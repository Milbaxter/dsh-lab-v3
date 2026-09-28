# The improvement loop

## One iteration

```
1. Read champion config + dev failure tags from last sweep
2. Proposer picks ONE target failure mode and ONE bounded change
3. Build candidate DSH profile (fresh, disposable)
4. Smoke tier (~10 dev tasks × 1 run): reject crashes, broken schemas, loops
5. Dev tier (40 × 5): paired comparison vs. champion
6. If dev improves → held-out (40 × 5) + transfer (20 × 5, both models)
7. Matched-budget control: champion + same extra inference (best-of-n)
8. Promotion gate (all conditions in PLAN.md)
9. Write experiment record; commit; promote or reject
```

Early exits at steps 4 and 5 keep most iterations cheap.

## Mutation types (what the proposer may change)

| Type | Examples |
|---|---|
| Add plugin | New system-prompt section, new tool, verification hook, fault-recovery logic |
| Edit plugin | Rewrite, shorten or restructure an existing plugin |
| Remove plugin | Drop an addition whose gain doesn't justify its token cost |
| Tool descriptions | Clarify, deduplicate or narrow tool descriptions and schemas |
| Configuration | Compaction thresholds, step budgets, tool subset, memory provider on/off |
| Adopt candidate | Try a researched external plugin or memory provider (e.g. from the optimal-deepseek-harness-setup candidate ledger) |

One change per iteration so gains can be attributed. Bundles only after their parts are individually tested.

## Proposer rules
- Input: champion config, dev tasks, dev traces with failure tags, history of past experiment records.
- Must state: target failure mode, hypothesis, expected mechanism, what result would disprove it.
- Never receives held-out or transfer tasks, graders, or per-task held-out outcomes.
- Plugin text is checked for leakage (overlap with dev task text, file names, expected answers) before running.
- Author and reviewer passes are separate, following the Astra rubric in optimal-deepseek-harness-setup (`docs/JUDGING.md`).

## Experiment record (one file per iteration)

Based on the harness-intelligence-improvements template:

```
Name / date / iteration number
Target failure and baseline evidence (dev failure tags)
Hypothesis and disconfirmation criterion
Champion config (commit) / candidate config (commit)
Model, provider, sampling settings, vLLM version
Tasks: split sizes, task-bank commit
Budgets and repetitions (k)
Dev: pass rate, paired diff, CI
Held-out: pass rate, paired diff, CI
Transfer (both models): pass rate, paired diff, CI
Matched-budget control result
Tokens per solved task; plugin prompt overhead
Failure-tag shift (did the targeted failure actually decrease?)
Newly solved tasks / regressions (dev only listed by ID)
Decision: promote / reject / revise / insufficient evidence
Limitations
Trace locations
```

## Meta-review (every ~10 iterations)
- Which mutation types win or lose, and on which failure modes.
- Dev vs. held-out gap trend (overfitting alarm).
- Whether champion gains transfer to the second model and to DeepSeek spot checks.
- Direction for the next proposer passes.

## Scheduling
Reuse the existing 12-hour Astra cycle rather than creating a new scheduler. GPU servers are created at the start of a sweep and deleted at the end.
