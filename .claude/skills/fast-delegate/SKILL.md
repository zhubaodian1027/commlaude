---
name: fast-delegate
description: Fast three-tier coding workflow (Neon, Kimi Supervisor, Worker) for well-defined implementation, bug fixes, scoped refactors, and batch edits where architecture is already clear. Skips Astra unless explicitly escalated. (Slash command /kimi already inlines this workflow; do not re-invoke this skill when /kimi is active.)
---

# Fast Delegate

Use this only when the desired behavior and design are already clear and edits/execution are needed. If the user only asks for a read-only review or audit without edits, skip Frame/Decompose/Execute and invoke `kimi-supervisor` directly in `MODE: REVIEW` (same as `/reviewer`) without dispatching `worker` or `smart-worker`. For architectural ambiguity or a broad feature, use `/commlaude` instead. Neon is the sole orchestrator; subagents never delegate further.

1. **Frame**: Create `.orchestra/<run-id>/00-brief.md` with scope, constraints, and acceptance criteria. Read `../model-orchestra/references/schemas.md` for artifact formats.
2. **Decompose**: Invoke `kimi-supervisor` with `MODE: DECOMPOSE`. Explain that no Astra blueprint exists and the clear brief is authoritative. Save `02-tasks.json` and validate task scope, dependencies, and verification commands.
3. **Execute**: Dispatch `worker` or `smart-worker` instances according to each task's `assignee` in dependency waves, parallelizing only independent packets. Save reports under `03-reports/`. For any packet estimated **> 30 minutes**, release the launcher worker right after detached startup and process health check (`Status: LAUNCHED` + ETA), then create a native scheduled task near ETA (`ToolSearch` → `CronCreate` with `recurring: false`, avoiding terminal `sleep`) to run `/worker` before advancing dependent waves or review.
4. **Review**: Invoke Kimi with `MODE: REVIEW`, append results to `04-review.md`, and run at most two revision rounds per packet. Require independent test execution before `PASS`.
5. **Escalate only when necessary**: If Kimi emits `ESCALATE_TO_ASTRA` or two rounds cannot resolve the issue, invoke `astra-architect` once with the minimal failure evidence. Tell the user why the fast path escalated and record the targeted plan before continuing.
6. **Debrief**: Report actual changes, executed verification, remaining risks, and the artifact path. Optionally audit real model routing with `"$ORCHESTRA_ROOT/bin/orchestra-audit" --since <run_start_iso>`.

Do not add an architecture approval gate to an already clear task, but never use that as permission to expand scope without asking.
