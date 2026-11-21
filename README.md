# commlaude — Communication-First 的多模型 Claude Code

这是一个运行在 Claude Code 之上、**目录完全隔离**的多模型角色协作环境。

它不是简单的“多接几个模型”，而是围绕两个核心工程理念构建：

1. **Communication 能力为中枢（Communication-First Hub）**
   在复杂软件工程中，真正的瓶颈往往不是单次推理的上限，而是**意图对齐、上下文策展（Context Curation）、方案翻译与批判性把关、以及多步骤状态编排**。因此本架构将**沟通、理解与协调能力最强**的模型放在 L1 主会话中枢，统一面向人协作，并对内以扁平单层（Flat Hub-and-Spoke）方式调度专职角色。
2. **角色抽象与模型解耦（Role-First, Model-Agnostic）**
   所有子代理、技能、斜杠命令与启动脚本**只绑定语义角色组（`group/role-*`）**，不耦合任何具体厂商或具体模型。每个角色组由**能力画像**定义；背后实际接入哪些模型、故障如何回退、何时调整优先级，全部在路由层（如 Magpie）动态配置，编排层零改动。

> 本环境的所有配置、代理、技能、会话数据与运行产物都归当前目录管理，**不会修改全局 `~/.claude/` 配置或原有 Magpie 的主模型 / tier / subagent 绑定**。

---

## 核心设计理念

### 1. 单中枢扁平编排（Flat Hub-and-Spoke）

Claude Code 子代理不能递归派生子代理，这也恰好避免了失控的多层代理套娃。L1 Communicator 是唯一的全局状态机编排者：

- 负责与人澄清需求、提炼精简的 `00-brief.md`；
- 必要时先派长上下文侦察角色绘制代码地图，**不把未经筛选的大段仓库直接倾倒给深度推理角色**；
- 按拓扑依赖分波次派发任务，并控制审批闸门、修订轮次与升级边界。

### 2. 声音隔离（Voice Isolation：“Thinker Thinks, Communicator Speaks”）

不同角色的能力优势并不重合：深度推理/架构模型擅长第一性原理与极端边界分析，但直接输出往往冗长、保守或充满免责声明。

- **L2 架构师**保持严格只读，只产出高密度结构化蓝图，并强制提供**激进第一性原理方案**与**稳健务实方案**对比；
- **L1 沟通中枢**负责落盘原始蓝图，将其转译为清晰、自然、直指本质的人话，并补充独立的工程视角（指出过度设计、隐性迁移成本或过度保守），在**得到人明确批准后**才进入实现。

### 3. 写审分离与有界循环

- **架构师只读**：可检索与分析，不能改代码；
- **Worker 限定作用域**：每个原子任务包明确指定 `allowed_files` 与 `verification_cmd`；
- **审查者写审分离**：拥有读取与命令执行权限，可独立运行测试并给出 `PASS` / `REVISE` / `ESCALATE_TO_ASTRA` 结论，但没有直接编辑文件的工具权限；
- **有界收敛**：单任务最多 2 轮修订，架构升级默认最多 1 次，防止无限返工。

### 4. 泛化优先，路由与编排彻底解耦

模型生态迭代极快。只要在路由层维护 6 个语义角色组（`group/role-*`），你随时可以：

- 替换任意角色的底层模型或供应商，而不改一行提示词；
- 为每个角色配置有序回退链（`routing=order`），配额耗尽或上游异常时自动切换；
- 依据不同时间段、成本策略或额度状态，动态调整组内模型顺序；
- 通过审计脚本核对每次调用的 `Requested`（角色组）与 `Served`（实际服务模型），保证归因真实可查。

---

## 架构总览

```text
                         ┌─────────────────────────────────────┐
                         │                User                 │
                         └──────────────────┬──────────────────┘
                                            │ 自然语言对齐 / 架构审批
                                            ▼
                         ┌─────────────────────────────────────┐
                         │  L1 Communicator & Hub (主会话)      │
                         │  group/role-communicator            │
                         │  意图对齐 · 上下文策展 · 翻译 · 状态机 │
                         └────┬──────────┬──────────┬──────────┘
                              │          │          │
              ┌───────────────┘          │          └───────────────┐
              ▼                          ▼                          ▼
┌───────────────────────────┐ ┌───────────────────────┐ ┌───────────────────────────┐
│ L2 Architect (只读规划)    │ │ L3 Supervisor (写审分离)│ │ L4 Workers (限定范围执行)   │
│ group/role-architect      │ │ group/role-supervisor │ │ group/role-worker-code    │
│ 第一性原理 · 双方案蓝图     │ │ 任务拆解 · 独立测审    │ │ group/role-worker-long    │
└───────────────────────────┘ └───────────────────────┘ └───────────────────────────┘

独立权限分类旁路：Auto Mode ──► group/role-auto-mode（不跟随主会话模型漂移）
```

---

## 语义角色组与能力画像

编排层只认以下 6 个语义路由组，不预设任何特定模型。你可以根据自己可用的模型池，按能力画像自由填入首选与回退链：

| 角色层 | 语义路由组 | 权限边界 | 推荐能力画像（Model-Agnostic） | 默认路由策略 |
|---|---|---|---|---|
| **L1 沟通中枢** | `group/role-communicator` | 主会话编排 | 沟通自然、上下文理解强、擅长总结转译与多步协作 | `routing=order` `stays=session` |
| **L2 架构师** | `group/role-architect` | 只读（检索/调研） | 高深度推理、第一性原理建模、复杂架构与难题诊断 | `routing=order` `stays=session` |
| **L3 拆解与审查** | `group/role-supervisor` | 只读 + Bash 测试 | 任务分解严谨、边界条件敏感、擅长严格代码审查 | `routing=order` `stays=session` |
| **L4a 编码 Worker** | `group/role-worker-code` | 读写 + 测试 | 高性价比、响应快、逻辑与代码实现准确 | `routing=order` `stays=auto` |
| **L4b 长上下文 Worker** | `group/role-worker-long` | 读写 + 侦察/文档 | 长上下文稳定、适合代码库侦察、多文件机械修改与文档 | `routing=order` `stays=auto` |
| **Auto Mode 分类器** | `group/role-auto-mode` | 权限安全分类 | 极低延迟、低成本、适合高频无状态权限判定 | `routing=order` `stays=off` |

> **关于命名说明**：目录中的命令名（`/astra`、`/kimi`、`/worker`、`/commlaude`）与子代理文件名（`.claude/agents/*.md`）是参考实现沿用的语义槽位标识；实际路由完全由 `group/role-*` 决定，不限定任何具体模型。

---

## 四种按需提速入口

按任务复杂度选择合适档位，避免小事走重流程，也避免大事缺少设计把关：

| 入口 | 协作路径 | 适用场景 | 关键约束 |
|---|---|---|---|
| `/astra <问题>` | `User ↔ L1 ↔ L2` | 架构讨论、难题诊断、第一性原理头脑风暴 | 只读，不改代码 |
| `/worker <小型明确任务>` | `User ↔ L1 → 单 L4` | 边界清晰的小改动、代码侦察、补测试、改文档 | 单 Worker 直通，**无独立审查** |
| `/kimi <明确任务>` | `User ↔ L1 → L3 → L4 → L3` | 设计已经清楚的功能实现、缺陷修复、范围重构 | 跳过架构阶段，保留独立测试与审查 |
| `/commlaude <复杂任务>` | `User ↔ L1 ↔ L2 → [人工审批] → L3 ↔ L4` | 复杂特性、大型重构、方案不确定的研发任务 | **架构经人明确批准后才写代码**，最多 2 轮修订 |

每次多步编排都会在当前项目目录沉淀可追踪产物：

```text
<project>/.orchestra/<YYYYMMDD-HHMMSS>-<slug>/
├── 00-brief.md          # L1 提炼的问题定义、约束与验收标准
├── 01-blueprint.md      # L2 原始技术蓝图 + 人类审批结论
├── 02-tasks.json        # L3 拆解的原子任务图（含依赖与 allowed_files）
├── 03-reports/          # L4 各任务执行与验证证据
└── 04-review.md         # L3 独立测试与逐轮审查结论
```

---

## 快速开始

### 前置条件

- macOS / 类 Unix 环境，已安装 Claude Code CLI（默认探测 `/opt/homebrew/bin/claude`，可通过 `CLAUDE_BIN` 指定）。
- 已安装并运行本地 Magpie 网关（默认监听 `http://127.0.0.1:3425`，或任意支持分组路由的 Anthropic 兼容本地网关）。
- Python 3（仅使用标准库，无第三方依赖）。

### 1. 创建六个语义角色组

`setup-magpie.sh` 内置了一组参考映射，你可以直接通过环境变量传入自己手头的模型列表（逗号分隔，按优先级排序），无需改动脚本本身：

```bash
ROLE_COMMUNICATOR_MODELS="<primary>,<fallback>" \
ROLE_ARCHITECT_MODELS="<primary>,<fallback>" \
ROLE_SUPERVISOR_MODELS="<primary>,<fallback>" \
ROLE_WORKER_CODE_MODELS="<primary>,<fallback>" \
ROLE_WORKER_LONG_MODELS="<primary>,<fallback>" \
ROLE_AUTO_MODE_MODELS="<primary>,<fallback>" \
./setup-magpie.sh
```

或者直接编辑 `setup-magpie.sh` 中的默认模型列表后执行 `./setup-magpie.sh`（也可在已有 Claude Code 会话中使用 `! ./setup-magpie.sh`）。

脚本会自动完成以下安全措施：

1. 首次运行时自动保存带时间戳的 Magpie 回滚快照，快照名仅记录在本目录被 git 忽略的 `.magpie-setup-state`。
2. 仅创建六个 `group/role-*` 路由组；若发现同名组已存在且非本安装创建，会拒绝覆盖并退出。
3. **不会修改**现有的 Magpie 主模型、四个 tier 或全局 subagent 绑定。

### 2. 启动隔离环境

在任意项目目录下运行本仓库中的启动器：

```bash
/path/to/commlaude/bin/claude-orchestra
```

如果希望在任意目录通过短命令启动，可在 `~/.zshrc`（或对应 shell 配置）中添加带标记的 alias（卸载脚本可自动识别并仅移除该标记块）：

```zsh
# >>> commlaude isolated launcher >>>
alias commlaude='/path/to/commlaude/bin/claude-orchestra'
# <<< commlaude isolated launcher <<<
```

随后 `source ~/.zshrc`，即可在任意项目目录运行：

```bash
commlaude
commlaude --resume
commlaude --version
```

启动器会自动完成：

- 将 `CLAUDE_CONFIG_DIR` 固定指向本仓库的 `.claude/`；
- 直连本机网关 `http://127.0.0.1:3425`（使用非机密本地占位令牌 `magpie-local`）；
- 清除继承的 `CLAUDE_CODE_SUBAGENT_MODEL`、`ANTHROPIC_MODEL` 等全局路由覆盖，避免原有全局配置干扰子代理路由；
- 将 Auto Mode 权限分类器固定到 `group/role-auto-mode`（`CLAUDE_CODE_AUTO_MODE_SERVER=0`），防止权限判断漂移到主会话模型。

可选启动环境变量：

- `ORCHESTRA_MAIN_MODEL`：默认 `group/role-communicator`。
- `ORCHESTRA_EFFORT`：默认 `high`。
- `MAGPIE_BASE_URL`：默认 `http://127.0.0.1:3425`。
- `CLAUDE_BIN`：默认 `/opt/homebrew/bin/claude`。

### 3. 动态调整任意角色组的模型顺序

由于路由与编排完全解耦，想根据成本、额度或时段切换某角色的优先级（例如调整 Auto Mode 分类器或 Worker 首选模型），只需在 Magpie 中更新对应组的模型顺序：

```bash
magpie group set role-auto-mode models=<model-a>,<model-b>
```

`role-auto-mode` 默认使用 `routing=order` 与 `stays=off`，因此无需重启或修改启动器，等待数秒让网关加载新配置后，新的权限分类请求就会按新顺序路由。

---

## 验证与模型归因审计

### 静态检查与单元测试（不调用模型）

```bash
./bin/orchestra-verify
python3 -I -m unittest discover -s ./tests -p 'test_*.py'
```

### 真实路由冒烟测试（会通过网关发起模型调用）

```bash
./scripts/routing_smoke_test.sh
```

测试产物写入本目录被忽略的 `.smoke/`，并验证主会话与四个子代理角色组是否都真实发出请求。

### 模型归因审计

读取本地 Magpie `usage.jsonl` 的元数据（仅统计角色、模型、耗时、状态与 token/费用字段，不读取提示词或密钥）：

```bash
# 查看最近 30 分钟
./bin/orchestra-audit

# 查看指定 UTC 时间之后
./bin/orchestra-audit --since '2026-11-20T00:00:00Z'
```

输出表格会同时展示 `Requested`（请求的语义角色组）与 `Served`（实际服务的上游模型），发生故障回退时一目了然，不会把回退模型误算为首选模型。

---

## 目录隔离边界

本环境只在以下位置写入运行数据（均已在 `.gitignore` 中排除）：

- `.claude/` 下的运行时文件（会话、设置、缓存、历史等；`.gitignore` 采用白名单机制，仅追踪 `.claude/agents/`、`.claude/commands/`、`.claude/skills/`）；
- 目标项目的 `.orchestra/`：多步编排的工作流产物；
- 本目录的 `.smoke/`、`logs/`、`backups/`、`.magpie-setup-state`：本地测试、日志与回滚记录。

不会改动全局 `~/.claude/`。如需临时回到原生 Claude Code，直接运行普通的 `claude` 命令即可。

---

## 撤回 / 卸载

先预览会被删除的范围，不修改任何内容：

```bash
./uninstall.sh --dry-run
```

卸载本目录内的隔离环境与运行产物（若 `~/.zshrc` 中存在标记的 `commlaude` alias 也会一并移除），保留 Magpie 路由组：

```bash
./uninstall.sh --yes
```

同时删除六个由本安装创建的 `group/role-*` 路由组：

```bash
./uninstall.sh --yes --magpie
```

> 卸载默认不会自动恢复整个 Magpie 快照，以避免覆盖你之后做的无关调整。若希望完全回到安装前的 Magpie 状态，可查看本地 `.magpie-setup-state` 中的快照名并手动执行 `magpie use '<snapshot-name>'`。

---

## 常见问题

- **启动时报网关连接失败**：确认本地 Magpie 正在运行，可执行 `magpie healthcheck`。
- **提示自定义模型名未识别（`context assumed to be 200k tokens`）**：这是 Claude Code 对自定义 `group/role-*` 名称的本地提示，不影响路由与正常调用。
- **某个角色实际走了回退模型**：用 `magpie group role-<角色>` 检查组内成员可用性，再用 `./bin/orchestra-audit` 核对 `Requested` 与 `Served`。
- **如何无痛切回原生环境**：直接运行 `claude`，全局配置从未被改动。
