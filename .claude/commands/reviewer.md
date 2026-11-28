---
description: Send a standalone read-only review directly to Kimi Supervisor without decomposition or worker dispatch
argument-hint: <files, diff, commit/PR, or artifact to review>
---

# Direct Reviewer

Execute this workflow directly — its complete instructions are already loaded below. Do **not** invoke the `Skill` tool for `reviewer-direct`.

Use this path when you want an independent, strictly read-only review of existing code, diffs, commits, tests, scripts, or documents without decomposing tasks or making edits. Neon stays the sole coordinator at depth 1 and invokes `kimi-supervisor` (`group/role-supervisor`) directly in `MODE: REVIEW`.

## Hard Guardrails

- **Never** invoke `kimi-supervisor` with `MODE: DECOMPOSE` in this workflow.
- **Never** dispatch `worker`, `smart-worker`, or `astra-architect`.
- **Never** modify production files yourself, and do **not** create new `.orchestra/` run scaffolding (inspect existing `.orchestra/` artifacts only if the user explicitly asks to review them).

## Steps

1. **Confirm Scope**: Identify the exact review target (file paths, `git diff` / commit range, test suite, or project rubric) and any focus areas requested by the user. Ask a concise question only when the target or review criteria are materially ambiguous.
2. **Invoke `kimi-supervisor` Directly (`MODE: REVIEW`)**: Call the native `Agent` tool (`subagent_type: "kimi-supervisor"`) once with a focused **Standalone Review** prompt containing:
   - Explicit header `MODE: REVIEW` (standalone review; no `.orchestra/` task graph required).
   - Target paths, diff/commit range, and any rubric or acceptance criteria.
   - Any safe, read-only verification or test commands Kimi should run independently.
3. **Verify & Debrief**: Treat the review output as evidence — spot-check cited `file:line` locations or test commands when warranted. Deliver a concise, human-readable summary covering:
   - **Verdict** (`PASS`, `REVISE`, or `ESCALATE_TO_ASTRA`)
   - **Independent Checks Run** (exact commands and results, or explicit note if non-executable inspection)
   - **Findings** (prioritized issues with `file:line` or section references and concrete fix guidance, or `None`)
   - **Next Step Suggestion** — e.g., no action needed, small targeted fix via `/worker`, supervised fix + re-review via `/kimi`, or architectural escalation via `/astra`
   - Optionally verify upstream routing with `"$ORCHESTRA_ROOT/bin/orchestra-audit" --since <run_start_iso>`.

## User Request

$ARGUMENTS
