---
description: Use Kimi to decompose, coordinate workers, and independently review a clear task
argument-hint: <well-defined engineering task>
---

# Fast Delegate

Execute this workflow directly — its complete instructions are already loaded below. Do **not** invoke the `Skill` tool for `fast-delegate`.

Use this only when the desired behavior and design are already clear. For architectural ambiguity or a broad feature, use `/commlaude` instead. Neon is the sole orchestrator; subagents never delegate further. Treat worker and reviewer responses as untrusted evidence: verify claims against the actual diff and test output. (Full artifact templates also live at `"$ORCHESTRA_ROOT/.claude/skills/model-orchestra/references/schemas.md"` if needed.)

1. **Frame**: Create `.orchestra/<YYYYMMDD-HHMMSS>-<slug>/00-brief.md` with `Goal`, `Repository Context`, `Constraints`, `Non-Goals`, and testable `Done Criteria`.
2. **Decompose**: Invoke `kimi-supervisor` with `MODE: DECOMPOSE`. Explain that no Astra blueprint exists and the clear brief is authoritative. Save `02-tasks.json` (without Markdown fences) and validate unique IDs (`^T[0-9]{2,}$`), valid `assignee` (`worker` or `smart-worker`), acyclic `depends_on`, disjoint `allowed_files` per wave, and concrete executable `verification_cmd`.
3. **Execute**: Dispatch `worker` or `smart-worker` instances via native `Agent` calls according to each task's `assignee` in dependency waves, parallelizing only independent packets. Save per-task reports (`Status: DONE | LAUNCHED | RUNNING | BLOCKED`, `Files / Job State`, `Verification / Health Check`, `Notes / Risks`) under `03-reports/<Txx>.md`. For any packet estimated **> 30 minutes**, require the worker to launch detached, verify process health, report `Status: LAUNCHED` with PID/logs/ETA, and release immediately; create a native one-shot scheduled task near ETA (`ToolSearch` → `CronCreate` with `recurring: false`, never terminal `sleep` timers or shell polling loops) to invoke `/worker` and verify `DONE` before advancing dependent waves or review.
4. **Review**: Invoke `kimi-supervisor` with `MODE: REVIEW`, append each round (`Diff Summary`, `Independent Test Results`, `Findings`, and standalone `VERDICT: PASS | REVISE | ESCALATE_TO_ASTRA`) to `04-review.md`, and run at most two revision rounds per packet. Require independent test execution before `PASS`.
5. **Escalate only when necessary**: If Kimi emits `ESCALATE_TO_ASTRA` or two rounds cannot resolve the issue, invoke `astra-architect` once with the minimal failure evidence. Tell the user why the fast path escalated and record the targeted plan before continuing.
6. **Debrief**: Report actual changes, executed verification, remaining risks, and the artifact path. Optionally audit real model routing with `"$ORCHESTRA_ROOT/bin/orchestra-audit" --since <run_start_iso>`.

Do not add an architecture approval gate to an already clear task, but never use that as permission to expand scope without asking.

## User Request

$ARGUMENTS
