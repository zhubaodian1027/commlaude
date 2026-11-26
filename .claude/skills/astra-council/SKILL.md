---
name: astra-council
description: Fast two-model thinking workflow (User, Neon, Astra) for natural-language brainstorming, difficult math/research/architecture questions, and deep diagnosis when no workers or independent implementation review are needed. (Slash command /astra already inlines this workflow; do not re-invoke this skill when /astra is active.)
---

# Astra Council

1. Distill the user's question and only the relevant context into a focused prompt for `astra-architect`. Explicitly request bold first-principles ideas and a pragmatic alternative.
2. Invoke `astra-architect` once. If a material requirement is missing, ask Neon to clarify with the user rather than making a second speculative call.
3. Translate the response into natural prose with these sections:
   - **核心结论（说人话版）**
   - **Astra 的高价值洞见 / 突破点**
   - **Neon 补充视角** — identify excessive conservatism, abstraction, or ignored engineering experience.
   - **下一步建议** — state whether a small task fits `/worker`, a clear implementation needs `/kimi`, the design justifies `/commlaude`, or no further workflow is needed.
4. Preserve exact formulas, proofs, and code when precision matters. Show longer raw Astra excerpts only when the user asks.

Do not create worker tasks or modify production files in this workflow.
