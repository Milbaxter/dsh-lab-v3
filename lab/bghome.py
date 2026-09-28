"""Build a background DSH home: earlier sessions from *other* projects.

A real user's ~/.dsh holds many sessions across many projects. Each lab run
copies this snapshot into its fake ~/.dsh before starting, so an agent that
digs through DSH's session store faces realistic noise instead of finding only
the current task's sessions.

    python -m lab.bghome            # builds ../bghome/.dsh (about 40 sessions, a few cents)
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from . import arms as armreg
from .sweep import PROXY, MODELS, DSH_BIN, ROOT, base_env, sandboxed, PY

PROJECTS = {
    "blog-site": [
        "Create index.html with a simple header 'My Blog' and an empty article list.",
        "I prefer 2-space indentation in HTML and CSS. Add style.css with a centered 700px column.",
        "Add a first article 'Hello world' to index.html.",
        "Write a tiny Python script build.py that copies index.html and style.css into public/.",
        "Add a footer with the current year to index.html.",
    ],
    "cli-todo": [
        "Start a CLI todo app: todo.py with add and list commands storing items in todo.json.",
        "Add a 'done <n>' command that marks item n as done.",
        "We use argparse, not click, in this project. Make sure todo.py follows that.",
        "Add a --json flag to 'list' that prints the raw JSON.",
        "Write a short README.md with usage examples.",
    ],
    "data-pipeline": [
        "Write extract.py that reads raw.csv (columns id,value) and writes clean.csv without rows where value is empty.",
        "Our timestamps in this pipeline are always UTC ISO-8601. Add a 'processed_at' column to clean.csv.",
        "Add a unit test test_extract.py for the empty-value filtering using pytest.",
        "Create a Makefile target 'pipeline' that runs extract.py.",
        "Summarise what the pipeline does in PIPELINE.md.",
    ],
    "infra-scripts": [
        "Write backup.sh that tars the ./data directory into backups/data-<date>.tar.gz.",
        "Our servers run Ubuntu 22.04 and we deploy with Ansible. Create inventory.ini with hosts web1 and web2 under [web].",
        "Add a cleanup step to backup.sh that keeps only the 7 newest backups.",
        "Write healthcheck.sh that curls http://localhost:3000/health and exits 1 on failure.",
        "Add comments explaining each step of backup.sh.",
    ],
    "ml-notebook": [
        "Create train.py that fits a linear regression on data.csv (x,y) with numpy only and prints the slope.",
        "We always seed randomness with 1234 in this repo. Add a train/test split to train.py.",
        "Print the test MSE at the end of train.py.",
        "Save the fitted parameters to model.json.",
        "Write a short EXPERIMENTS.md noting the current MSE placeholder.",
    ],
    "mobile-api": [
        "Create app.py with a Flask app exposing GET /ping returning {'ok': true}.",
        "API responses in this service use camelCase keys. Add GET /userProfile returning a dummy profile.",
        "Add a requirements.txt for the service.",
        "Add basic request logging to app.py.",
        "Write api.md documenting both endpoints.",
    ],
    "docs-site": [
        "Create docs/index.md with a welcome page for our product 'Beacon'.",
        "Our docs use sentence case for headings, never Title Case. Add docs/install.md.",
        "Add docs/faq.md with three placeholder questions.",
        "Create mkdocs.yml listing the three pages.",
        "Fix any heading that is not in sentence case.",
    ],
    "game-jam": [
        "Create game.py: a text guessing game where the player guesses a number 1-100.",
        "Keep this project dependency-free: standard library only. Add a replay option.",
        "Track the best score in best.txt.",
        "Add a --easy flag that limits the range to 1-20.",
        "Write CREDITS.md listing 'Team Pixel'.",
    ],
}


def main() -> None:
    out = ROOT.parent / "bghome"
    shutil.rmtree(out, ignore_errors=True)
    fakehome = out / "fakehome"
    home = fakehome / ".dsh"
    tmp = out / "tmp"
    for d in (home, tmp):
        d.mkdir(parents=True)
    arm = armreg.resolve("standard")
    results = (ROOT / "runs" / "_results").resolve()
    results.mkdir(parents=True, exist_ok=True)
    faults = ROOT / "runs" / "faults"
    for pi, (proj, prompts) in enumerate(PROJECTS.items()):
        ws = fakehome / "projects" / proj
        ws.mkdir(parents=True)
        rid = f"bghome.{proj}"
        (faults / f"{rid}.json").write_text(json.dumps({"max_calls": 25 * len(prompts), "model": "flash"}))
        env = base_env(tmp.resolve(), fakehome.resolve())
        env.update(LAB_BASE_URL=f"{PROXY}/r/{rid}/v1", LAB_API_KEY="lab-dummy", LAB_DSH_BIN=DSH_BIN, **MODELS["flash"])
        # Session ids like a real install (unique, never s1/s2/s3 used by tasks).
        sids = [f"bg{pi:02d}{i:02d}-{os.urandom(4).hex()}" for i in range(len(prompts))]
        spec = {"prompts": prompts, "session_ids": sids, "home": str(home.resolve()), "ws": str(ws.resolve()),
                "profile": arm.profile, "patches": arm.all_patches(), "session_timeout": 300,
                "result": str(results / f"{rid}.json")}
        rc, killed, log = sandboxed([PY, str(ROOT / "lab" / "worker.py"), json.dumps(spec)], out.resolve(),
                                    tmp.resolve(), env, 300 * len(prompts) + 60)
        print(proj, "rc", rc, "killed", killed, flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    n = len(list(home.glob("sessions/*/*/session.v*.jsonl*")))
    print(f"background home: {n} sessions in {home}")


if __name__ == "__main__":
    main()
