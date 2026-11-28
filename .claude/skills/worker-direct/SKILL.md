---
name: worker-direct
description: Direct single-Worker execution for small, tightly scoped edits, focused reconnaissance, tests, or documentation when requirements and allowed files are clear and no architecture or independent Kimi review is needed. (Slash command /worker already inlines this workflow; do not re-invoke this skill when /worker is active.)
---

# Direct Worker

Use one Worker for one small, explicit task. Neon still coordinates and reports but does not delegate to Astra or Kimi. Do not use this path for architectural ambiguity, broad refactors, interdependent packets, or work that needs independent review (use `/kimi` or `/commlaude` instead); for standalone read-only review, use `/reviewer`; for batch creative, deep-reading, or research synthesis tasks, use `/smarter`.

1. Confirm the goal, allowed files, and verification command. Ask a concise question if any of these materially affect safety or scope.
2. Invoke `worker` (bound to `group/role-worker-code`) in the appropriate mode:
   - **Execution Mode** (default) for focused implementation, bug fixes, algorithms, tests, mechanical edits, or documentation. Supply an inline `T01` task packet with `allowed_files`, precise instructions, and `verification_cmd`.
   - **Long-Task Launch / Check Mode (> 30 minutes)**: When a job is estimated to run **longer than 30 minutes**, never keep `worker` open waiting and avoid terminal `sleep` timers or shell `sleep` watcher loops. Have the launcher `worker` start the job detached, verify initial **process health** (PID alive, resource/log activity clean, no startup errors), report `Status: LAUNCHED` with PID/log/output paths and **ETA**, and exit immediately to release the subagent. Then create a native one-shot scheduled task around the ETA (`ToolSearch` → `CronCreate` with `recurring: false`, never `Bash` `sleep`) whose prompt invokes `/worker` to check completion and run `verification_cmd` (or update ETA and schedule the next `CronCreate` check if still `RUNNING`).
   - **Scout Mode** for read-only codebase reconnaissance. Explicitly request Scout Mode and prohibit edits or mutating commands.
3. Do not modify production files yourself and do not spawn extra Workers to expand scope (the only permitted follow-up Worker is a timed `/worker` completion check for a > 30-minute `LAUNCHED` job). If the packet expands or becomes blocked, stop and explain why `/kimi` or `/commlaude` is more appropriate.
4. Check the actual changed files and independently rerun the verification command when practical. Report exactly what ran and any remaining risk.

This path has **no independent Kimi review**. State that limitation briefly in the final report for implementation work.
