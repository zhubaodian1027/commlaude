---
name: reviewer-direct
description: Direct standalone read-only review via kimi-supervisor (group/role-supervisor) in MODE: REVIEW without task decomposition, .orchestra scaffolding, or worker/smart-worker dispatch. (Slash command /reviewer already inlines this workflow; do not re-invoke this skill when /reviewer is active.)
---

# Direct Reviewer

Use this path when the user wants an independent, strictly read-only review of existing code, diffs, commits, tests, scripts, or documents without decomposing tasks or making edits. Neon stays the sole coordinator at depth 1 and invokes `kimi-supervisor` (`group/role-supervisor`) directly in `MODE: REVIEW`.

- **Never** call `kimi-supervisor` with `MODE: DECOMPOSE`.
- **Never** dispatch `worker`, `smart-worker`, or `astra-architect`.
- **Never** modify production files or create new `.orchestra/` run scaffolding unless explicitly reviewing an existing run.

1. **Confirm Scope**: Identify the exact review target (file paths, `git diff` / commit range, test suite, or rubric) and focus areas. Ask a concise question only when scope or criteria are materially ambiguous.
2. **Invoke `kimi-supervisor` Directly (`MODE: REVIEW`)**: Call `kimi-supervisor` once with explicit `MODE: REVIEW` (standalone review), target paths/diff scope, review criteria, and any safe verification commands to run independently.
3. **Verify & Debrief**: Spot-check cited locations or test results as needed and report the verdict (`PASS`, `REVISE`, or `ESCALATE_TO_ASTRA`), independent checks executed, prioritized findings with `file:line` or section references, and the best next step (`/worker`, `/kimi`, `/astra`, or none). Optionally audit routing with `"$ORCHESTRA_ROOT/bin/orchestra-audit" --since <run_start_iso>`.
