---
name: worker-direct
description: Direct single-Worker execution for small, tightly scoped edits, focused reconnaissance, tests, or documentation. Use for /worker when requirements and allowed files are clear and no architecture or independent Kimi review is needed.
---

# Direct Worker

Use one Worker for one small, explicit task. Neon still coordinates and reports but does not delegate to Astra or Kimi. Do not use this path for architectural ambiguity, broad refactors, interdependent packets, or work that needs independent review; use `/kimi` or `/commlaude` instead.

1. Confirm the goal, allowed files, and verification command. Ask a concise question if any of these materially affect safety or scope.
2. Choose exactly one Worker:
   - `worker-deepseek` for focused implementation, bug fixes, algorithms, and tests.
   - `worker-hydrogen` for long-context reconnaissance, mechanical multi-file edits, or documentation.
3. Supply an inline `T01` task packet with `allowed_files`, precise instructions, and `verification_cmd`. For read-only reconnaissance, explicitly request Scout Mode and prohibit edits.
4. Do not modify production files yourself and do not spawn a second Worker. If the packet expands or becomes blocked, stop and explain why `/kimi` or `/commlaude` is more appropriate.
5. Check the actual changed files and independently rerun the verification command when practical. Report exactly what ran and any remaining risk.

This path has **no independent Kimi review**. State that limitation briefly in the final report for implementation work.
