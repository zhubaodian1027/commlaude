---
name: smart-worker-direct
description: Direct high-reasoning single or parallel batch dispatch to smart-worker (group/role-smart-worker) for creative, judgment-heavy, or synthesis-intensive work such as deep paper reading, literature digests, nuanced research writing, and complex analysis without full architecture ceremony. (Slash command /smarter already inlines this workflow; do not re-invoke this skill when /smarter is active.)
---

# Smart Worker Direct

Use `smart-worker` (bound to `group/role-smart-worker`) for creative, judgment-heavy, or batch research and synthesis tasks — such as deep paper reading, literature reviews, structured technical writing, comparative analysis, or nuanced content generation — where higher reasoning quality matters more than lowest-cost mechanical execution.

Neon remains the sole coordinator at depth 1 and dispatches native `Agent` calls directly (so tasks appear and track cleanly as native subagents rather than background `claude -p` shell scripts). For mechanical code edits or quick read-only scouting, use `/worker`; for standalone read-only review, use `/reviewer`; for multi-file software engineering that requires independent code review or architecture approval, use `/kimi` or `/commlaude`.

1. **Frame & Scope**: Confirm the goal, per-item inputs, exact output paths (`allowed_files`), quality rubric or project standard (such as a project's `CLAUDE.md`), and any verification checks. Ask a concise question only when ambiguity materially affects structure, scope, or safety.
2. **Partition & Dispatch in Parallel Waves**:
   - For a single deliverable, invoke `smart-worker` with one inline `T01` packet containing inputs, rubric, `allowed_files`, and verification checks.
   - For a batch task (such as multiple papers, sections, or reports), partition into independent packets (`T01`, `T02`, ...) with strictly **disjoint `allowed_files`**.
   - Dispatch independent packets concurrently in bounded waves (typically 3–5 parallel native `Agent` calls with `subagent_type: "smart-worker"` per wave) to balance throughput with upstream rate limits and quality oversight.
   - Do not shell out to background `claude -p` scripts when native `Agent` calls can execute directly.
   - **Long-running jobs (> 30 minutes)**: If any packet launches a compute or pipeline job estimated > 30 minutes, require the subagent to start it detached, verify process health, report `Status: LAUNCHED` with PID/logs/ETA, and exit immediately so the subagent is released; create a native one-shot scheduled task near ETA (`ToolSearch` → `CronCreate` with `recurring: false`, avoiding terminal `sleep` timers or shell polling loops) to run `/worker` and check completion.
3. **Inspect & Aggregate**: Do not author the delegated deliverables yourself during execution. After each wave finishes, verify that every target file exists, is non-empty, and satisfies the required rubric before launching the next wave or updating any shared index/summary file.
4. **Debrief**: Report per-item status, written file paths, key findings or caveats, and optionally audit upstream routing with `"$ORCHESTRA_ROOT/bin/orchestra-audit" --since <run_start_iso>`. Note briefly that this path has **no independent Kimi review loop**.
