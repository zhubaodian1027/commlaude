# PLAN.md — Multi-Model Role-Based Orchestration System (`model-orchestra`) on Claude Code + Magpie

> **Current implementation note:** The isolated implementation in this directory uses `/astra` for Astra consultation, `/kimi` for supervised delegation, `/worker` for direct single-Worker tasks, and `/commlaude` for the full workflow. L4 execution and read-only scouting are consolidated into a single `worker` subagent bound to `group/role-worker-code` (`role-worker-long` was removed), leaving five Magpie role groups including Auto Mode (`group/role-auto-mode`, DeepSeek Flash with GLM 5.3 Flash fallback by default). See `README.md` for current commands and paths. The remainder of this file is the original design plan.

> **Target Executor**: AI Coding Agent (Claude Code / Codex / Pi) operating in macOS with local Claude Code CLI (`2.1.311+`) and Magpie (`0.1.4473+`).
> **Goal**: Build a production-ready, low-friction, multi-model collaboration system in Claude Code backed by Magpie routing groups:
>
> `User ↔ [L1 Neon: Communicator & Hub] ↔ [L2 Astra: Architect & Innovator] → [L3 Kimi 3.1 Pro: Supervisor & Reviewer] → [L4 DeepSeek Flash / Gemini 4 Hydrogen: Workers]`

---

## 0. Ground-Truth Environment Inventory (Verified)

Do **not** guess paths or model IDs. The following were verified on this machine:

| Component | Verified Value |
| :--- | :--- |
| Claude Code CLI | `/opt/homebrew/bin/claude` (`2.1.311`) |
| Claude Code Config | `~/.claude/settings.json`, `~/.claude/agents/`, `~/.claude/skills/` |
| Magpie Binary | `/Applications/Magpie.app/Contents/MacOS/magpie` (`0.1.4473`) |
| Magpie Gateway | `http://127.0.0.1:3425` (`~/.config/magpie/gateway.json`) |
| Magpie Usage Log | `~/.config/magpie/usage.jsonl` (JSONL with `agent`, `model`, `requested`, `served`, `tokens`, `ms`, `status`, `cost`) |
| Current Main Model | `agy-cli/gemini-4-neon[1m]` |
| Current Subagent Env Override | `CLAUDE_CODE_SUBAGENT_MODEL="agy-cli/gemini-4-hydrogen[1m]"` (**HAZARD — see Phase 0**) |

### Verified Available Model IDs (from `~/.claude/settings.json` `modelPicker.options`)

| Role | Primary Model ID | Fallback Model ID(s) |
| :--- | :--- | :--- |
| **L1 Communicator / Hub** | `agy-cli/gemini-4-neon[1m]` | `agy-cli/claude-sonnet-5-5[1m]` |
| **L2 Architect / Innovator** | `codex/gpt-6.2-astra` | `codex/gpt-6.2-sol`, `agy-cli/claude-opus-5-5[1m]` |
| **L3 Supervisor / Reviewer** | `kimi/k3.1-pro[1m]` | `agy-cli/gemini-4-neon[1m]`, `agy-cli/claude-opus-5-5[1m]` |
| **L4a Worker (Code / Logic)** | `deepseek/deepseek-flash[1m]` | `agy-cli/gemini-4-hydrogen[1m]` |
| **L4b Worker (Long Context / Scout / Docs)** | `agy-cli/gemini-4-hydrogen[1m]` | `deepseek/deepseek-flash[1m]` |

> **Security Rule**: Never read, print, log, or copy API keys/tokens from `~/.claude/settings.json` or `~/.config/magpie/*.json`.

---

## 1. Architectural Invariants (DO NOT VIOLATE)

1. **Flat Hub-and-Spoke Delegation (Claude Code Constraint)**:
   - Claude Code subagents **cannot** recursively invoke the `Agent` tool to spawn sub-subagents.
   - Therefore, **L1 Neon (the main interactive Claude Code session)** is the **sole state-machine orchestrator**. All delegation (`Neon → Astra`, `Neon → Kimi`, `Neon → Workers`) happens at depth 1, coordinated via files in `.orchestra/<run-id>/`.
2. **Voice Isolation ("Astra Thinks, Neon Speaks")**:
   - `astra-architect` must NEVER produce user-facing prose, apologies, or hedging disclaimers.
   - `astra-architect` is strictly **read-only** (`Read, Grep, Glob, WebSearch, WebFetch`) and outputs a structured technical blueprint with explicit **Bold/First-Principles** vs **Pragmatic** options.
   - L1 Neon persists Astra's raw output to `.orchestra/<run-id>/01-blueprint.md`, then **rewrites/translates** it into crisp, natural, empathetic human language for the user.
3. **Decoupled Routing via Magpie Groups**:
   - Create semantic Magpie routing groups (`group/role-*`) with `routing=order` and `stays=session` so quota exhaustion or upstream outages fail over automatically without modifying any agent or skill files.
4. **Bounded Loops & Strict Escalation**:
   - Worker ↔ Kimi Supervisor review loop is capped at **max 2 revision rounds** per task packet.
   - If a task still fails after 2 rounds OR reveals a fundamental design flaw, Kimi emits `ESCALATE_TO_ASTRA` and Neon invokes `astra-architect` (max 1 re-plan per run without explicit user approval).
5. **Three-Speed Entry Points (Avoid Ceremony on Simple Tasks)**:
   - `/council` (`astra-council`): `User ↔ Neon ↔ Astra` (fast high-IQ brainstorming, architecture debate, debugging hard problems — zero worker/supervisor overhead).
   - `/delegate` (`fast-delegate`): `User ↔ Neon → Kimi → Workers → Kimi Review → Neon` (routine engineering when design is already clear — skips Astra).
   - `/orchestra` (`model-orchestra`): Full 4-tier pipeline for complex features, refactors, and research-to-code tasks.

---

## 2. Deliverable File Tree

```text
~/.claude/
├── agents/
│   ├── astra-architect.md          # L2: Read-only high-IQ planner & innovation engine
│   ├── kimi-supervisor.md          # L3: Read+Bash decomposer & strict code reviewer
│   ├── worker-deepseek.md          # L4a: Fast code & logic implementer
│   └── worker-hydrogen.md          # L4b: Long-context scout, multi-file refactor & docs worker
└── skills/
    ├── model-orchestra/
    │   ├── SKILL.md                # Full 4-tier orchestrator (/orchestra)
    │   ├── references/
    │   │   └── schemas.md          # Artifact schemas for .orchestra/<run-id>/*
    │   └── scripts/
    │       └── audit_run.py        # Verifies actual upstream models & cost via magpie usage.jsonl
    ├── astra-council/
    │   └── SKILL.md                # 2-model fast path (/council: Neon ↔ Astra)
    └── fast-delegate/
        └── SKILL.md                # 3-model fast path (/delegate: Neon → Kimi ↔ Workers)
```

Runtime workspace artifacts (per project, gitignored):
```text
<project>/.orchestra/<YYYYMMDD-HHMMSS>-<slug>/
├── 00-brief.md                     # Problem statement, constraints, acceptance criteria (written by Neon)
├── 01-blueprint.md                 # Raw Astra blueprint (persisted verbatim by Neon)
├── 02-tasks.json                   # Atomic work orders + worker assignments (generated by Kimi)
├── 03-reports/
│   └── T01.md, T02.md, ...         # Worker execution & test evidence reports
└── 04-review.md                    # Kimi review verdicts (PASS / REVISE / ESCALATE_TO_ASTRA)
```

---

## 3. Phased Execution Plan

### Phase 0: Backup & Empirical Routing Verification Gate (MANDATORY FIRST STEP)

**Why**: `~/.claude/settings.json` currently sets `CLAUDE_CODE_SUBAGENT_MODEL="agy-cli/gemini-4-hydrogen[1m]"`. In several Claude Code 2.1.x builds, `CLAUDE_CODE_SUBAGENT_MODEL` acts as a hard override that ignores per-agent frontmatter `model:`. Additionally, we must verify whether subagent frontmatter accepts direct Magpie group IDs (`group/role-architect`) or requires Claude Code tier aliases (`opus`, `sonnet`, `haiku`, `fable`).

#### Tasks
1. **Create Backups**:
   ```bash
   MAGPIE="/Applications/Magpie.app/Contents/MacOS/magpie"
   "$MAGPIE" save before-orchestra
   cp ~/.claude/settings.json ~/.claude/settings.json.bak.before-orchestra
   ```
2. **Test A — Check `CLAUDE_CODE_SUBAGENT_MODEL` Override Behavior**:
   - Create a temporary agent `~/.claude/agents/_probe-opus.md` with `model: opus` (or `model: codex/gpt-6.2-astra`) and minimal prompt: `Reply with the single word OK.`
   - Run a one-shot Claude Code invocation in `/tmp` that invokes `_probe-opus` via the Agent tool, recording timestamps before and after.
   - Inspect the last lines of `~/.config/magpie/usage.jsonl` after the start timestamp:
     ```bash
     tail -n 20 ~/.config/magpie/usage.jsonl | python3 -c '
     import sys, json
     for line in sys.stdin:
         r = json.loads(line)
         print(r.get("time"), r.get("agent"), "req=", r.get("requested"), "served=", r.get("served"), "status=", r.get("status"))
     '
     ```
   - **Branch Decision**:
     - If `served` shows `agy-cli/gemini-4-hydrogen[1m]` instead of the probe's `model:`, then `CLAUDE_CODE_SUBAGENT_MODEL` IS overriding frontmatter. Clear it immediately:
       ```bash
       "$MAGPIE" claude subagent default
       ```
       Re-run Test A to confirm override is lifted.
3. **Test B — Direct Group ID vs Tier Alias in Frontmatter `model:`**:
   - Temporarily test `_probe-direct.md` with `model: group/role-architect` (after creating `role-architect` in Phase 1) vs `model: opus`.
   - Record which mode routes cleanly through Magpie:
     - **Preferred Mode (Direct Group IDs)**: If `model: group/role-*` works directly in frontmatter, bind each of the 4 subagents directly to its dedicated `group/role-*` (enables 5+ independent role pools: Communicator, Architect, Supervisor, Worker-Code, Worker-Long).
     - **Fallback Mode (Tier Aliases)**: If Claude Code restricts frontmatter `model:` to built-in aliases, map the 4 Claude Code tiers via Magpie:
       - `opus` → `group/role-architect` (`astra-architect.md` uses `model: opus`)
       - `sonnet` → `group/role-supervisor` (`kimi-supervisor.md` uses `model: sonnet`)
       - `haiku` → `group/role-worker-code` (`worker-deepseek.md` uses `model: haiku`)
       - `fable` → `group/role-worker-long` (`worker-hydrogen.md` uses `model: fable`)
4. **Cleanup**: Delete `_probe-*.md` after verification.

#### Phase 0 Acceptance Gate
- [ ] Backup profile `before-orchestra` exists in `magpie profiles` and `~/.claude/settings.json.bak.before-orchestra` exists.
- [ ] Empirical log from `~/.config/magpie/usage.jsonl` proves per-subagent model routing works without being hijacked by `CLAUDE_CODE_SUBAGENT_MODEL`.
- [ ] Routing mode (Direct Group ID vs Tier Alias) is confirmed and documented.

---

### Phase 1: Provision Magpie Role Routing Groups & Claude Code Tier Bindings

Run the following commands using `MAGPIE="/Applications/Magpie.app/Contents/MacOS/magpie"`:

```bash
MAGPIE="/Applications/Magpie.app/Contents/MacOS/magpie"

# L1: Communicator / Main Session (Neon primary, Sonnet 5.5 fallback)
"$MAGPIE" group add role-communicator \
  models="agy-cli/gemini-4-neon[1m],agy-cli/claude-sonnet-5-5[1m]" \
  routing=order stays=session

# L2: Architect / High-IQ Innovation (Astra primary, Sol & Opus 5.5 fallback)
# Note: verify whether codex/gpt-6.2-astra accepts :high or :xhigh via `magpie models claude` first;
# if supported, append :high or :xhigh to codex/gpt-6.2-astra.
"$MAGPIE" group add role-architect \
  models="codex/gpt-6.2-astra,codex/gpt-6.2-sol,agy-cli/claude-opus-5-5[1m]" \
  routing=order stays=session

# L3: Supervisor / Reviewer (Kimi 3.1 Pro primary, Neon fallback)
"$MAGPIE" group add role-supervisor \
  models="kimi/k3.1-pro[1m],agy-cli/gemini-4-neon[1m],agy-cli/claude-opus-5-5[1m]" \
  routing=order stays=session

# L4a: Worker - Code & Logic (DeepSeek Flash primary, Hydrogen fallback)
"$MAGPIE" group add role-worker-code \
  models="deepseek/deepseek-flash[1m],agy-cli/gemini-4-hydrogen[1m]" \
  routing=order stays=auto

# L4b: Worker - Long Context, Exploration & Docs (Hydrogen primary, DeepSeek Flash fallback)
"$MAGPIE" group add role-worker-long \
  models="agy-cli/gemini-4-hydrogen[1m],deepseek/deepseek-flash[1m]" \
  routing=order stays=auto
```

Next, wire Claude Code's main model and 4 tier aliases to the role groups (so BOTH Direct Group ID mode and Tier Alias mode work seamlessly):

```bash
"$MAGPIE" claude group/role-communicator
"$MAGPIE" claude opus group/role-architect
"$MAGPIE" claude sonnet group/role-supervisor
"$MAGPIE" claude haiku group/role-worker-code
"$MAGPIE" claude fable group/role-worker-long
"$MAGPIE" claude subagent default

# Optional reasoning effort calibration (verify accepted values with `magpie claude opus_effort`)
"$MAGPIE" claude opus_effort high
"$MAGPIE" claude sonnet_effort medium
"$MAGPIE" claude haiku_effort low
```

#### Phase 1 Acceptance Gate
- [ ] `"$MAGPIE" groups` lists all 5 `group/role-*` groups with ready members (no `not served` warnings).
- [ ] `"$MAGPIE" claude` shows `group/role-communicator` as main model, the 4 tiers mapped to their respective groups, and `subagents` cleared (`default`).
- [ ] Save a clean snapshot: `"$MAGPIE" save orchestra-ready`.

---

### Phase 2: Author the 4 Specialized Subagents (`~/.claude/agents/`)

> **Model Field Rule**: Based on Phase 0 Test B, set `model:` to either `group/role-*` (Preferred) or the matching tier alias (`opus` / `sonnet` / `haiku` / `fable`).

#### 2.1 `~/.claude/agents/astra-architect.md` (L2 Architect / Innovator)

- **Frontmatter**:
  - `name: astra-architect`
  - `description: Principal Architect and Innovation Strategist powered by GPT-6.2-Astra. Invoke for hard technical design, first-principles breakthroughs, deep root-cause diagnosis, algorithm/architecture trade-offs, and escalations when workers or reviewers get stuck. Read-only; never talks directly to the end user.`
  - `model: group/role-architect` *(or `opus` per Phase 0)*
  - `tools: Read, Grep, Glob, WebSearch, WebFetch`
- **System Prompt Requirements (CRITICAL — Anti-Conservatism & Voice Isolation)**:
  - Role: You are an internal Principal Architect & First-Principles Strategist. Your output is read by an orchestration editor (Neon), **never directly by the human user**.
  - **Anti-Conservatism Rules**:
    - Do NOT pad answers with safety disclaimers, vague caveats ("it depends", "consider carefully"), or generic boilerplate.
    - For every non-trivial design problem, you MUST present **at least two distinct options**:
      1. **Option A — Bold / First-Principles**: High-leverage, non-obvious, cleanest long-term architecture even if it requires rethinking assumptions.
      2. **Option B — Pragmatic / Incremental**: Lowest-risk, fastest-to-ship path.
    - Explicitly commit to ONE recommendation with sharp engineering justification and falsifiable trade-offs.
  - **Strict Output Schema** (so Neon can persist verbatim and translate cleanly):
    1. `## Core Diagnosis & Hidden Invariants` (what naive approaches miss)
    2. `## Architectural Options` (Option A Bold vs Option B Pragmatic + Recommendation)
    3. `## Target Design & Module Contracts` (exact files, interfaces, data flow, state invariants)
    4. `## Failure Modes & Edge Cases` (concrete traps + mitigations)
    5. `## Verification & Acceptance Criteria` (exact commands/assertions that prove correctness)
  - Never modify repository files. Inspect only the files strictly necessary to ground your design.

#### 2.2 `~/.claude/agents/kimi-supervisor.md` (L3 Supervisor / Decomposer / Reviewer)

- **Frontmatter**:
  - `name: kimi-supervisor`
  - `description: Technical Project Manager and Independent Code Reviewer powered by Kimi 3.1 Pro. Supports two explicit modes specified in the prompt: (1) DECOMPOSE — convert an approved blueprint into atomic worker task packets; (2) REVIEW — audit worker diffs, run tests, and issue PASS, REVISE, or ESCALATE_TO_ASTRA verdicts.`
  - `model: group/role-supervisor` *(or `sonnet` per Phase 0)*
  - `tools: Read, Grep, Glob, Bash`
- **System Prompt Requirements**:
  - Strictly check the caller's requested mode: `MODE: DECOMPOSE` or `MODE: REVIEW`. Never edit production source files yourself (read-only + read/test `Bash` commands only).
  - **In `MODE: DECOMPOSE`**:
    - Read `.orchestra/<run-id>/00-brief.md` and `01-blueprint.md`.
    - Emit a valid JSON task graph (to be saved as `02-tasks.json`) containing atomic, testable packets (`T01`, `T02`, ...).
    - Each packet MUST declare: `id`, `title`, `assignee` (`worker-deepseek` for focused code/algorithms/tests OR `worker-hydrogen` for large-context reads/multi-file mechanical refactors/docs), `depends_on`, `allowed_files` (disjoint for parallel packets!), `instructions`, `verification_cmd`.
    - Minimize dependencies so independent packets can run in parallel.
  - **In `MODE: REVIEW`**:
    - Read `01-blueprint.md`, `02-tasks.json`, worker report(s) in `03-reports/`, inspect `git status` and `git diff`, and **independently run** the verification/test commands via `Bash`.
    - Check: (1) Blueprint compliance, (2) Scope discipline (no unrequested edits), (3) Edge cases & error handling, (4) Real test execution evidence.
    - Output a structured verdict block starting with exactly one of:
      - `VERDICT: PASS`
      - `VERDICT: REVISE` (followed by numbered, file:line-specific fix instructions per task ID)
      - `VERDICT: ESCALATE_TO_ASTRA` (only when a deep architectural contradiction or unsolvable bug blocks progress; include minimal repro and exact question for Astra)

#### 2.3 `~/.claude/agents/worker-deepseek.md` (L4a Code & Logic Worker)

- **Frontmatter**:
  - `name: worker-deepseek`
  - `description: Fast, cost-efficient coding worker powered by DeepSeek V4.1 Flash. Execute one scoped task packet (coding, bug fixes, unit tests, scripts) strictly within its allowed_files and return a concise verification report.`
  - `model: group/role-worker-code` *(or `haiku` per Phase 0)*
  - `tools: Read, Edit, Write, MultiEdit, Bash, Grep, Glob`
- **System Prompt Requirements**:
  - Execute ONLY the assigned task packet (`Txx`) and modify ONLY files listed in `allowed_files` (if another file is required, stop and report `BLOCKED` instead of expanding scope silently).
  - Run the packet's `verification_cmd` after implementing.
  - Return a compact structured report (for `03-reports/<task-id>.md`):
    - `Status`: `DONE` | `BLOCKED`
    - `Files Changed`: list with 1-line summary each
    - `Verification`: exact command + exit code + key output snippet
    - `Notes / Risks`: any assumptions or issues discovered

#### 2.4 `~/.claude/agents/worker-hydrogen.md` (L4b Long-Context / Scout / Docs Worker)

- **Frontmatter**:
  - `name: worker-hydrogen`
  - `description: High-speed long-context worker powered by Gemini 4 Hydrogen (1M context). Use for codebase reconnaissance/mapping, multi-file mechanical edits, log/paper/spec synthesis, and documentation updates.`
  - `model: group/role-worker-long` *(or `fable` per Phase 0)*
  - `tools: Read, Edit, Write, MultiEdit, Bash, Grep, Glob`
- **System Prompt Requirements**:
  - Dual capability:
    1. **Scout Mode** (read-only reconnaissance): Quickly scan large directories, extract file maps, symbol inventories, and dependency graphs into a concise brief so Astra and Neon don't waste expensive tokens reading raw boilerplate.
    2. **Execution Mode**: Execute assigned task packet (`Txx`) strictly within `allowed_files`, run `verification_cmd`, and return the same structured report format as `worker-deepseek`.

#### Phase 2 Acceptance Gate
- [ ] All 4 files exist in `~/.claude/agents/` with valid YAML frontmatter.
- [ ] `astra-architect.md` and `kimi-supervisor.md` have **no** `Edit`/`Write`/`MultiEdit` tools.
- [ ] No hardcoded API keys or legacy proxy model strings (`ccs-claude-myantigravity...`) appear in any new agent.

---

### Phase 3: Author the Orchestration Skills, Schemas & Audit Script (`~/.claude/skills/`)

#### 3.1 `~/.claude/skills/model-orchestra/references/schemas.md`
Define exact templates for:
- `00-brief.md` (Goal, Repo Context, Constraints, Non-Goals, Done Criteria)
- `01-blueprint.md` (Astra's 5-section schema)
- `02-tasks.json` (JSON schema with `run_id`, `tasks[]`: `id`, `title`, `assignee`, `depends_on`, `allowed_files`, `instructions`, `verification_cmd`)
- `03-reports/<Txx>.md` (Worker completion report)
- `04-review.md` (Kimi review log with round number, diff summary, test results, verdict)

#### 3.2 `~/.claude/skills/model-orchestra/SKILL.md` (Full Pipeline — `/orchestra`)
- **Frontmatter**:
  - `name: model-orchestra`
  - `description: Full 4-tier multi-model orchestration workflow (Neon Hub ↔ Astra Architect → Kimi Supervisor → DeepSeek/Hydrogen Workers). Use when the user asks to run /orchestra, build a complex feature, perform a major refactor, or wants multi-model planning, execution, and independent review.`
- **State Machine Instructions for L1 Neon (Main Session)**:
  1. **Phase 1 — Frame & Scout**:
     - Clarify ambiguous requirements with the user in plain, concise language.
     - Create `.orchestra/<YYYYMMDD-HHMMSS>-<slug>/00-brief.md`.
     - If the codebase is large/unfamiliar, dispatch `worker-hydrogen` in Scout Mode to map relevant files and attach the summary to `00-brief.md`.
  2. **Phase 2 — Innovate & Architect (`astra-architect`)**:
     - Invoke `astra-architect` with `00-brief.md` path and specific technical questions.
     - Save Astra's raw response verbatim to `01-blueprint.md`.
  3. **Phase 3 — Human Translation & Approval Gate 1 (CRITICAL)**:
     - **Translate Astra's blueprint into natural, high-clarity Chinese/English ("讲人话")**:
       - Summarize the core insight in 3 bullets.
       - Present **激进创新方案 (Option A)** vs **稳健务实方案 (Option B)** in a clean comparison table with pros/cons and Astra's recommendation + Neon's own editorial critique (flag if Astra was still too conservative or over-engineered!).
       - Ask the user to pick an option or adjust constraints before any code is written.
     - Wait for user confirmation. (Record decision at top of `01-blueprint.md`.)
  4. **Phase 4 — Task Breakdown (`kimi-supervisor`, `MODE: DECOMPOSE`)**:
     - Invoke `kimi-supervisor` to produce `02-tasks.json`. Persist it to `.orchestra/<run-id>/02-tasks.json`.
     - Sanity-check that parallel tasks have disjoint `allowed_files`.
  5. **Phase 5 — Parallel Execution (`worker-deepseek` / `worker-hydrogen`)**:
     - Execute waves in topological order of `depends_on`.
     - Dispatch independent tasks in the same wave in **parallel** Agent tool calls (use `isolation: "worktree"` if two tasks might touch overlapping build artifacts, otherwise disjoint `allowed_files`).
     - Save each worker's response to `03-reports/<Txx>.md`.
  6. **Phase 6 — Independent Review Loop (`kimi-supervisor`, `MODE: REVIEW`)**:
     - Invoke `kimi-supervisor` (`MODE: REVIEW`). Append result to `04-review.md`.
     - If `VERDICT: PASS` → go to Phase 7.
     - If `VERDICT: REVISE` and `round < 2` → dispatch only the affected worker(s) with Kimi's exact `file:line` feedback, then re-review.
     - If `VERDICT: ESCALATE_TO_ASTRA` (or `round == 2` still failing) → invoke `astra-architect` with `04-review.md` + failure trace for a targeted fix plan (max 1 escalation without asking user), then resume or pause for user input.
  7. **Phase 7 — Executive Debrief**:
     - Run `python3 ~/.claude/skills/model-orchestra/scripts/audit_run.py --since <run_start_iso>` (optional summary of models actually invoked).
     - Present a concise, human-friendly delivery report to the user: what changed, how it was verified, what Kimi caught & fixed, and per-role model attribution.

#### 3.3 `~/.claude/skills/astra-council/SKILL.md` (2-Model Fast Path — `/council`)
- **Frontmatter**:
  - `name: astra-council`
  - `description: Fast 2-model thinking workflow (User ↔ Neon ↔ Astra). Use when the user asks to /council, brainstorm, solve a hard math/research/architecture problem, or wants GPT-6.2-Astra's maximum intelligence translated into clear human prose by Gemini 4 Neon without spawning workers.`
- **Workflow**:
  1. Neon distills the user's question + minimal relevant file paths into a sharp prompt for `astra-architect` (explicitly demanding bold first-principles ideas + anti-conservatism).
  2. Invoke `astra-architect`.
  3. Neon reads Astra's raw response and delivers a human-friendly synthesis:
     - **核心结论（说人话版）**
     - **Astra 的高价值洞见 / 突破点**
     - **Neon 补充视角**（指出 Astra 过于保守、晦涩或忽略工程体验的地方）
     - **下一步建议**（是否值得升级为 `/orchestra` 落地实现）
  4. Only show raw Astra excerpts if the user asks or for exact formulas/code snippets.

#### 3.4 `~/.claude/skills/fast-delegate/SKILL.md` (3-Model Fast Path — `/delegate`)
- **Frontmatter**:
  - `name: fast-delegate`
  - `description: Fast 3-tier coding workflow (Neon → Kimi Supervisor ↔ DeepSeek/Hydrogen Workers) that skips Astra planning. Use for well-defined engineering tasks, bug fixes, refactors, or batch edits where architecture is already clear.`
- **Workflow**:
  - Same as `/orchestra` Phases 1, 4, 5, 6, 7 — skips Phases 2–3 (`astra-architect`) unless Kimi explicitly emits `ESCALATE_TO_ASTRA`.

#### 3.5 `~/.claude/skills/model-orchestra/scripts/audit_run.py`
Write a clean, stdlib-only Python 3 script that:
- Accepts `--since <ISO-8601 timestamp>` (default: last 30 minutes) and `--log ~/.config/magpie/usage.jsonl`.
- Filters records where `agent` contains `claude` (or all records if `--all`).
- Aggregates by `(requested, served)`: call count, input/output tokens, avg latency (`ms`), error count, total `cost`.
- Prints a clean Markdown table to stdout so Neon (and the user) can **provably verify** that Neon, Astra, Kimi, DeepSeek, and Hydrogen each actually served their intended calls!
- Never prints prompts, keys, or secrets (Magpie's `usage.jsonl` only stores metadata anyway).

#### Phase 3 Acceptance Gate
- [ ] All 3 `SKILL.md` files, `references/schemas.md`, and `scripts/audit_run.py` exist.
- [ ] `python3 ~/.claude/skills/model-orchestra/scripts/audit_run.py --since "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)"` runs cleanly with exit code 0.

---

### Phase 4: End-to-End Smoke Tests & Empirical Attribution Audit

Run all 3 smoke tests inside an isolated scratch repo `/tmp/orchestra-smoke` (`git init`):

1. **Test 1 — `/council` (Neon ↔ Astra Voice Isolation)**:
   - Prompt: Ask `/council` to design an adaptive rate-limiter algorithm with non-obvious trade-offs.
   - Verify:
     - `audit_run.py` shows BOTH `agy-cli/gemini-4-neon[1m]` AND `codex/gpt-6.2-astra` in `served`.
     - User-facing response is natural, structured, includes Bold vs Pragmatic options, and contains zero raw Astra hedging fluff.
2. **Test 2 — `/orchestra` (Full 4-Tier Pipeline + Review Loop)**:
   - Prompt: Build a tiny Python CLI tool (e.g., JSONL log stats analyzer with unit tests + README) in `/tmp/orchestra-smoke` via `/orchestra`.
   - Verify:
     - `.orchestra/<run-id>/` contains `00-brief.md`, `01-blueprint.md`, `02-tasks.json`, `03-reports/*.md`, `04-review.md`.
     - Gate 1 pauses for user approval before writing code.
     - `worker-deepseek` writes the Python code + tests; `worker-hydrogen` writes the README/docs in parallel.
     - `kimi-supervisor` independently executes `pytest` / `unittest` and issues `VERDICT: PASS`.
     - `audit_run.py` confirms all 4 tiers (`gemini-4-neon`, `gpt-6.2-astra`, `kimi/k3.1-pro`, and `deepseek-flash` / `gemini-4-hydrogen`) actually executed!
3. **Test 3 — Failover Verification**:
   - Inspect `magpie group role-architect` and `magpie group role-worker-code` to confirm ordered fallbacks are valid and ready.

#### Phase 4 Acceptance Gate
- [ ] Test 1 & Test 2 pass with real `audit_run.py` proof showing distinct upstream models per role.
- [ ] Clean up `/tmp/orchestra-smoke`.

---

### Phase 5: Optional Hardening (Implement Only After Phase 4 Passes)

1. **Global `.gitignore`**: Add `.orchestra/` to user's global gitignore (`~/.gitignore_global` if configured) so orchestration scratch directories are never accidentally committed.
2. **Deterministic `SubagentStop` Hook (Optional)**: Add a lightweight hook in `~/.claude/settings.json` that checks if a worker exited with `STATUS: DONE` without test output, reminding Neon to request verification before passing to Kimi.
3. **Magpie Library Sync (Optional)**: If the user also wants `/council` or `/orchestra` in Codex/Pi/Cursor later, register the skills via `magpie library skill` (keep Claude Code as primary first).

---

## 4. Rollback Plan

If anything breaks Claude Code or Magpie routing at any step:

```bash
MAGPIE="/Applications/Magpie.app/Contents/MacOS/magpie"
"$MAGPIE" use before-orchestra
cp ~/.claude/settings.json.bak.before-orchestra ~/.claude/settings.json
rm -f ~/.claude/agents/astra-architect.md \
      ~/.claude/agents/kimi-supervisor.md \
      ~/.claude/agents/worker-deepseek.md \
      ~/.claude/agents/worker-hydrogen.md
rm -rf ~/.claude/skills/model-orchestra \
       ~/.claude/skills/astra-council \
       ~/.claude/skills/fast-delegate
```

*(Note: Magpie `group/role-*` groups are harmless if unused, or can be removed via `magpie group rm <id>`.)*
