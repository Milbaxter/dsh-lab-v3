// Session recall: carry the user's own words across sessions in one workspace.
//
// Problem: each DSH session starts with an empty history, so standing
// instructions, preferences and facts the user gave in an earlier session
// ("from now on reports are in SEK", "never call v2") are simply absent. No
// model, however strong, can apply information it was never shown.
//
// Mechanism: when a top-level session's prompt is first assembled, read the
// persisted logs of earlier top-level sessions whose cwd is the same
// workspace, and add their user messages (verbatim, oldest first, capped) as a
// system-prompt section. The model sees what the user said before, including
// later corrections that override earlier ones. No extra model calls; the text
// is computed once per session so the prompt prefix stays cache-stable.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

export const name = 'lab-session-recall';
export const inject = ['systemPrompt'];

const HEADER = `## Earlier sessions in this workspace
The user worked with you in this workspace before. Below are the user's messages from those earlier sessions, oldest first. They may contain standing instructions, preferences, conventions or facts that still apply to the current request. A later message overrides an earlier one when they conflict, and an instruction the user explicitly scoped (to one file, package, task or occasion) applies only there. Do not redo earlier tasks unless asked; use this only as background for the current request.`;

// DSH appends one zstd frame per flush; zstdDecompressSync stops after the
// first frame, so split at frame magic and decode each frame (merging a chunk
// with the next if a magic sequence occurred inside compressed data).
const ZSTD_MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);
function zstdAllFrames(buf) {
  const starts = [];
  for (let i = buf.indexOf(ZSTD_MAGIC); i !== -1; i = buf.indexOf(ZSTD_MAGIC, i + 1)) starts.push(i);
  starts.push(buf.length);
  const out = [];
  let from = 0;
  for (let k = 1; k < starts.length; k++) {
    try {
      out.push(zlib.zstdDecompressSync(buf.subarray(starts[from], starts[k])));
      from = k;
    } catch { /* magic inside payload: extend this chunk to the next boundary */ }
  }
  return Buffer.concat(out);
}

function readLog(file) {
  try {
    let buf = fs.readFileSync(file);
    if (file.endsWith('.zst') || file.endsWith('.zstd')) buf = zstdAllFrames(buf);
    return buf.toString('utf8').split('\n').filter(Boolean).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
  } catch {
    return [];
  }
}

function listSessions(home) {
  const root = path.join(home, 'sessions');
  const out = [];
  let groups = [];
  try { groups = fs.readdirSync(root); } catch { return out; }
  for (const g of groups) {
    let ids = [];
    try { ids = fs.readdirSync(path.join(root, g)); } catch { continue; }
    for (const id of ids) {
      let files = [];
      try { files = fs.readdirSync(path.join(root, g, id)); } catch { continue; }
      const f = files.filter(n => /^session\.v\d+\.jsonl/.test(n)).sort().pop();
      if (f) out.push(path.join(root, g, id, f));
    }
  }
  return out;
}

function text(content) {
  return (content || []).filter(c => c && c.type === 'text').map(c => c.text).join('\n').trim();
}

// Matched control: same header and a comparable length, but neutral filler
// instead of the user's messages (tests "the information" vs "the nudge").
const FILLER = 'This workspace has a session history. Sessions are stored by the harness as event logs and are not reproduced here.';

export function recall({ home, cwd, sessionId, maxSessions = 20, maxChars = 12000, maxMessageChars = 2000, control = false }) {
  if (!home || !cwd) return '';
  const sessions = [];
  for (const file of listSessions(home)) {
    const events = readLog(file);
    const header = events.find(e => e.type === 'session');
    if (!header || header.id === sessionId || header.cwd !== cwd || (header.delegationDepth || 0) > 0) continue;
    const msgs = events
      .filter(e => e.type === 'user/message' && e.data && (e.data.source?.kind ?? 'user') === 'user')
      .map(e => text(e.data.content))
      .filter(Boolean);
    if (msgs.length) sessions.push({ at: header.createdAt || 0, msgs });
  }
  if (!sessions.length) return '';
  sessions.sort((a, b) => a.at - b.at);
  const recent = sessions.slice(-maxSessions);
  // Keep the newest material when over budget: drop whole oldest sessions first.
  const blocks = recent.map((s, i) => {
    const when = s.at ? new Date(s.at).toISOString().slice(0, 16).replace('T', ' ') + ' UTC' : 'unknown time';
    const body = s.msgs.map(m => '> ' + (m.length > maxMessageChars ? m.slice(0, maxMessageChars) + ' […]' : m).replace(/\n/g, '\n> ')).join('\n\n');
    return `### Session ${i + 1} (${when})\n${body}`;
  });
  while (blocks.length > 1 && blocks.join('\n\n').length > maxChars) blocks.shift();
  const body = blocks.join('\n\n');
  if (control) {
    const n = Math.max(1, Math.round(body.length / (FILLER.length + 1)));
    return `${HEADER}\n\n${Array(n).fill(FILLER).join(' ')}`;
  }
  return `${HEADER}\n\n${body}`;
}

function debug(obj) {
  if (!process.env.LAB_RECALL_DEBUG) return;
  try { fs.appendFileSync(process.env.LAB_RECALL_DEBUG, JSON.stringify(obj) + '\n'); } catch {}
}

export function apply(ctx, config = {}) {
  const home = config.home || process.env.DSH_HOME;
  debug({ at: 'apply', home, env: Object.keys(process.env).filter(k => k.startsWith('DSH')) });
  const cache = new Map(); // session id -> rendered text (stable for the session's lifetime)
  ctx.systemPrompt.variable('lab_session_recall', ({ agent }) => {
    const header = agent?.session?.header;
    debug({ at: 'variable', hasAgent: !!agent, keys: agent ? Object.keys(agent).slice(0, 30) : null, sessionKeys: agent?.session ? Object.keys(agent.session).slice(0, 30) : null, header });
    if (!header || (header.delegationDepth || 0) > 0) return '';
    const key = header.id ?? '';
    if (!cache.has(key)) {
      cache.set(key, recall({ home, cwd: header.cwd, sessionId: header.id, ...config }));
    }
    return cache.get(key);
  });
  ctx.systemPrompt.section({
    name: 'lab:session-recall',
    order: 10400,
    text: '{{lab_session_recall}}',
  });
}
