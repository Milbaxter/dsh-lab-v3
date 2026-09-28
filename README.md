# dsh-lab-v3

Attempt 3 of the DSH harness lab, following [dsh-small-model-lab-playbook](https://github.com/Milbaxter/dsh-small-model-lab-playbook).

**Goal:** find DeepSeek Harness plugins or config changes that make full DSH on its default model measurably better at real work.

- **Model:** `deepseek/deepseek-v4.1-flash` on OpenRouter.
  - Pinned to DeepInfra (fp8), with DSH's default reasoning effort (high) and no sampling overrides.
  - DeepSeek's own endpoint is excluded by the account's privacy setting, and DeepInfra is cheaper.
  - Prompt caching is verified: cached input costs about 10× less.
- **DSH:** `@deepseek-ai/dsh@0.1.7-rc.2` from npm, driven by `deepseek-harness-sdk 0.1.5rc1` through `dsh_bin`.
  - It uses the pi-ai `openai-completions` adapter, not DSH's native Messages adapter, because OpenRouter can't pass DeepSeek's Messages-specific features through.
  - Plugins built on hooks, prompts, tools or compaction don't depend on the adapter.
- **Budget:** about €50 (a $54 proxy hard cap).
- **Task bank:** private, in `dsh-lab-v3-tasks`.

Code is reused from [dsh-small-model-lab-opus-v2](https://github.com/Milbaxter/dsh-small-model-lab-opus-v2) (MIT).

## Known deviations
- The `minimal` arm (`sdk-minimal`) is dropped. Its persistent-PTY shell calls a setuid binary, which the macOS seatbelt sandbox always forbids. The `standard` arm's bash tool works inside the sandbox.
