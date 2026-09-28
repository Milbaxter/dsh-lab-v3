"""Harbor agent: run DSH (`headless` profile) inside a Terminal-Bench 2.0 task container.

The linux-amd64 Node + `@deepseek-ai/dsh` closure is mounted read-only at
/opt/dsh and this repo's `harness/` at /opt/lab/harness (see lab/tb.sh), so the
container needs no network install. Model calls go to the host pinning proxy
via host.docker.internal; the container never sees the OpenRouter key.

    harbor run ... --agent-import-path lab.harbor_dsh:DSHAgent --ak arm=standard --ak rep=1
"""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

ROOT = Path(__file__).resolve().parent.parent
PROXY = os.environ.get("LAB_PROXY_CONTAINER", "http://host.docker.internal:18080")
MODELS = {"flash": {"LAB_MODEL_ID": "deepseek-v4-flash", "LAB_CONTEXT_WINDOW": "1000000", "LAB_MAX_TOKENS": "65536"}}


def arm_patches(arm: str) -> list[str]:
    """Container paths of the arm's patches (same arm registry as the local runner)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from lab import arms as armreg
    harness = (ROOT / "harness").resolve()
    out = []
    for p in armreg.resolve(arm).all_patches():
        rel = Path(p).resolve().relative_to(harness)
        out.append(f"/opt/lab/harness/{rel.as_posix()}")
    return out


class DSHAgent(BaseAgent):
    def __init__(self, *args, arm: str = "standard", rep: int | str = 1, sweep: str = "tb",
                 max_calls: int | str = 80, model: str = "flash", **kwargs):
        super().__init__(*args, **kwargs)
        self.arm, self.rep, self.sweep = arm, int(rep), sweep
        self.max_calls, self.model = int(max_calls), model

    @staticmethod
    def name() -> str:
        return "dsh-lab"

    def version(self) -> str:
        return "0.1.7-rc.2"

    async def setup(self, environment: BaseEnvironment) -> None:
        r = await environment.exec("test -x /opt/dsh/node && /opt/dsh/node --version", timeout_sec=60)
        if r.return_code:
            raise RuntimeError("DSH closure not mounted at /opt/dsh: " + (r.stderr or r.stdout or "")[-500:])

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        task = Path(str(self.logs_dir)).parent.name.split("__")[0]
        rid = f"{self.sweep}.{self.arm.replace('/', '-')}.{task}.r{self.rep}"
        faults = ROOT / "runs" / "faults"
        faults.mkdir(parents=True, exist_ok=True)
        (faults / f"{rid}.json").write_text(json.dumps({"max_calls": self.max_calls, "model": self.model}))

        patches = " ".join(f"--patch {shlex.quote(p)}" for p in arm_patches(self.arm))
        env = {"LAB_BASE_URL": f"{PROXY}/r/{rid}/v1", "LAB_API_KEY": "lab-dummy", "DSH_HOME": "/tmp/dsh-lab-home",
               "DSH_PERMISSION_MODE": "danger-full-access", "DSH_TELEMETRY_MODE": "DISABLED", **MODELS[self.model]}
        logs = Path(self.logs_dir).resolve()
        (logs / "instruction.md").write_text(instruction)
        cmd = (f"mkdir -p /tmp/dsh-lab-home && /opt/dsh/node /opt/dsh/app/node_modules/@deepseek-ai/dsh/lib/bin.js "
               f"--profile headless {patches} --json - < /tmp/dsh-lab-instruction.md "
               f"> /tmp/dsh-lab-events.jsonl 2> /tmp/dsh-lab-stderr.log; echo exit=$? >> /tmp/dsh-lab-stderr.log")
        await environment.upload_file(logs / "instruction.md", "/tmp/dsh-lab-instruction.md")
        res = await environment.exec(cmd, env=env, timeout_sec=None)
        for name in ("dsh-lab-events.jsonl", "dsh-lab-stderr.log"):
            try:
                await environment.download_file(f"/tmp/{name}", logs / name)
            except Exception:
                pass
        try:
            await environment.download_dir("/tmp/dsh-lab-home/sessions", logs / "sessions")
        except Exception:
            pass
        context.metadata = {"arm": self.arm, "rep": self.rep, "run_id": rid, "exit_code": res.return_code}
