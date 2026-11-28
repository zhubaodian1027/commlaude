---
description: Ask Astra for architecture, innovation, and deep technical diagnosis
argument-hint: <question or problem>
---

# Astra Council

Execute this workflow directly — its complete instructions are already loaded below. Do **not** invoke the `Skill` tool for `astra-council`.

1. Distill the user's question and only the relevant context into a focused prompt for `astra-architect`. Explicitly request bold first-principles ideas and a pragmatic alternative.
2. Invoke `astra-architect` once via the `Agent` tool (`subagent_type: "astra-architect"`). If a material requirement is missing, clarify with the user first rather than making a second speculative call.
3. Translate the response into natural prose with these sections:
   - **核心结论（说人话版）**
   - **Astra 的高价值洞见 / 突破点**
   - **Neon 补充视角** — identify excessive conservatism, abstraction, or ignored engineering experience.
   - **下一步建议** — state whether a small task fits `/worker`, standalone read-only verification fits `/reviewer`, a clear implementation needs `/kimi`, the design justifies `/commlaude`, or no further workflow is needed.
4. Preserve exact formulas, proofs, and code when precision matters. Show longer raw Astra excerpts only when the user asks.

Do not create worker tasks or modify production files in this workflow.

## User Request

$ARGUMENTS
