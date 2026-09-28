# Iteration 1: session-recall

Written 2026-09-28, before any candidate run on the bank.

## Target failure
Multi-session memory. DSH starts every session with an empty history, so standing instructions, preferences and facts from earlier sessions are missing. On the 74-task Opus bank (screen, k=1), 6 of V4.1-flash's 8 failures were memory tasks: a dropped signature rule, a currency rule ignored, a "never promise dates" rule broken, and a deprecated variable name used.

Plain DSH sometimes recovers by reading DSH's own session store under `~/.dsh`. This took 4–6 extra tool calls in the mechanics check, and it works much less reliably on a real machine, whose `~/.dsh` holds many projects.

## Hypothesis
Giving the model the user's own earlier messages from the same workspace, verbatim, oldest first and size-capped, raises the pass rate on memory tasks. It should also cut tool calls and cost per solved task, because the agent no longer has to dig through `~/.dsh`.

## Mechanism
The plugin `harness/candidates/session-recall/session-recall.js` adds a system-prompt section:
- It is computed once per top-level session, so the prompt prefix stays cache-stable.
- It reads the persisted logs of earlier top-level sessions whose `cwd` matches this workspace.
- It includes only the user's messages, not assistant or tool output.
- It is capped at 20 sessions and 12,000 characters, dropping the oldest sessions first.
- A fixed header says that later messages override earlier ones, and that scoped instructions apply only within their scope.

No extra model calls, no tools, and no task-specific text.

## Why it should help a strong model too (scale-generality)
The information is absent from the context, not merely hard to use. No model can apply a rule it was never shown. The mechanism supplies information and does no reasoning for the model, so a stronger model (V4-pro) should use it at least as well.

## Controls
- **Matched control (`session-recall-control`):** the same header plus neutral filler of the same length. This separates "delivering the user's words" from "telling the model there were earlier sessions", which by itself triggers `~/.dsh` digging.
- **Over-application controls in the bank:** tasks where the rule was revoked (`mm-revoked-header`, `mm-revoked-debug-prints`), tasks where a rule is scoped to another package (`mm-scoped-decimal`), and tasks where a later fact supersedes an earlier one (`mm-freeze-date`, `mm-port-moved`). A recall plugin that makes the model over-apply old instructions fails these.

## Disconfirmation
Any of the following rejects the candidate:
- The paired dev difference versus `standard` is ≤ 0.
- The held-out 95% CI lower bound is ≤ 0.
- It does not beat the header-only control on held-out.
- It regresses on the over-application controls.
- Transfer regresses.

A gain that is matched by the control would mean the effect is the nudge, not the information.

## Measurements
Dev k=5 (standard vs candidate, interleaved) → held-out k=5 (standard vs candidate vs control) → transfer k=5 → gate. Secondary metrics: tool calls, cost per solved task, and `~/.dsh` snoop count.

## Results
(to be filled in)
