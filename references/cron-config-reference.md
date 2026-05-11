# Cron 任务配置参考

本文档提供 obsidian-second-brain 归档所需的 cron 任务完整配置。

## 任务 1：每日会话记忆归档（03:30）

### 创建命令（Hermes）

```bash
hermes cron create \
  --name "每日会话记忆归档" \
  --schedule "30 3 * * *" \
  --prompt "你是 Hermes 的记忆管理员。现在是凌晨 03:30，请完成以下任务：

## 第一步：回顾今天的会话
调用 session_search 回顾最近 24 小时的对话记录，搜索关键词包括用户偏好、环境配置、工具使用、项目进展、SOP、提示词、方案框架、工作流等。

## 第二步：提取值得持久化的信息，并分类
提取时按内容性质分成三类：

### A 类：Agent 记忆（用户偏好、环境、经验教训）
- 用户新表达的偏好、习惯、沟通风格
- 环境/系统/工具的新发现（OS 版本、软件安装、路径、版本等）
- 工具使用中的经验教训、坑点、解决方案
- 项目约定、命名规范、工作流变更
- 用户纠正你的错误或要求记住的事项

### B 类：资源资产（可复用的知识资产）
**判断标准：具有跨场景复用价值，不是某次对话的专属内容**

自动分类到 30-Resources/ 的子目录：
- AI 提示词/ — 提示词模板、系统提示词、角色设定
- SOP 流程/ — 操作流程、手册、标准规范
- 方案框架/ — 方案框架、营销策略、活动策划模板
- 工作流设计/ — 工作流设计、决策框架、知识图谱
- 技术教程/ — 技术笔记、配置说明、踩坑指南
- 教学模板/ — 教学相关的模板和提示词

**B 类资源筛选规则：**
1. 优先保留：完整可复用的模板/框架/SOP
2. 保留：通用性强的技术方案（不依赖特定项目上下文）
3. 保留：用户明确要求记住或保存的内容
4. 跳过：特定项目的专属讨论、一次性操作记录
5. 跳过：未完成的草稿或还在迭代中的内容

### C 类：项目进展（阶段性成果）
- 项目里程碑完成
- 阶段性总结、复盘
- 待办事项、跟进计划

## 第三步：写入记忆

### A 类 → Agent Memory + Obsidian Agent Memory
1. 对每条 A 类信息，调用 memory(action='add', target='memory') 或 target='user'
2. 同时追加到 Obsidian 70-Agent-Memory/inbox/<agent-name>.md（Hermes 默认为 hermes.md，先读现有去重）
   格式：## YYYY-MM-DD\\n- 要点 1\\n- 要点 2

### B 类 → Obsidian 30-Resources/ 资源库
1. 先读取 30-Resources/ 目录结构，确认现有分类
2. 检查对应分类子目录是否存在，没有则创建
3. 为每条有价值的 B 类内容创建或更新对应的资源笔记
4. 使用 wikilink 建立知识图谱关联
5. 文件名格式：[分类]/[主题]-[关键词].md
6. 笔记结构：标题、概述、核心内容、使用场景、元数据（创建日期、关联任务、状态）

### C 类 → Obsidian 50-Daily/ 或 10-Projects/
1. 追加到当天的 50-Daily/YYYY-MM-DD.md 或对应项目文件

## 规则
- 不要保存临时任务状态、一次性操作结果
- 不要保存已存在的相同内容（先判断是否已有）
- 如果今天没有值得保存的新信息，直接结束，不要硬凑
- 敏感信息（密钥、token、联系方式）禁止写入 Obsidian
- B 类资源的写入标准：必须具有跨场景复用价值，不是某次对话的专属内容

完成后汇报：
- A 类：保存了多少条 MemOS 记忆，inbox 追加了多少条
- B 类：创建/更新了多少条资源笔记（列出文件名）
- C 类：记录了多少条项目进展" \
  --toolsets web,terminal,file
```

### 验证

```bash
hermes cron list | grep "记忆归档"
```

## 任务 2：反向驱动监听（本地 gate + 分层模型）

### 设计原则

不要让 cron 高频直接唤醒 Agent 扫描 Inbox。正确流程是：

1. cron 先运行本地 gate 脚本检查 Inbox
2. Vault 不存在时，gate 可用 `OBSIDIAN_SMB_URL` 尝试挂载；失败则输出 `vault_unavailable`
3. 空目录、无匹配 tier、近期 provider 欠费/鉴权错误 → 输出 `{"wakeAgent": false}`，调度器跳过 LLM
4. 普通任务 → cheap tier job 唤醒小模型
5. 显式强模型任务 → strong tier job 唤醒强模型
6. 处理成功后追加 `80-Outputs/<agent-name>-response/_index.md`

### 安装 gate 脚本

将 skill 自带脚本复制到 Hermes 可执行脚本目录：

```bash
mkdir -p ~/.hermes/scripts
cp scripts/hermes-obsidian-gate.py ~/.hermes/scripts/
cp scripts/hermes-obsidian-strong-gate.py ~/.hermes/scripts/
chmod 700 ~/.hermes/scripts/hermes-obsidian-gate.py \
          ~/.hermes/scripts/hermes-obsidian-strong-gate.py
```

如果你的 Vault 不在默认路径，给 cron 所在环境设置：

```bash
export OBSIDIAN_AGENT_NAME="hermes"
export OBSIDIAN_AGENT_INBOX="/path/to/vault/00-Inbox/for-agent"
```

也可以设置 `OBSIDIAN_VAULT_PATH="/path/to/vault"`，gate 会自动推导 `00-Inbox/for-agent`，并按 `OBSIDIAN_AGENT_NAME` 推导输出目录 `80-Outputs/<agent-name>-response/`。如果是远程 SMB Vault，可设置 `OBSIDIAN_SMB_URL="smb://host/share"` 让 gate 在 Vault 不存在时尝试挂载。

如果 Hermes 是 launchd 后台服务，普通 shell 里的 `export` 可能不会传给服务；这种情况下要么用 `launchctl setenv OBSIDIAN_VAULT_PATH "/path/to/vault"` 和 `launchctl setenv OBSIDIAN_SMB_URL "smb://host/share"` 后重启 Hermes gateway，要么使用一个小 wrapper 脚本设置环境变量。

### 普通任务监听（cheap tier，每 5 分钟）

```bash
hermes cron create \
  --name "Obsidian 反向驱动监听（普通省钱）" \
  --script hermes-obsidian-gate.py \
  "*/5 * * * *" \
  "你是 Hermes 的 Obsidian 低成本指令处理引擎。运行前本地脚本已经完成目录扫描、任务分层和熔断判断。

执行规则：
1. 只处理 Script Output 中 Selected file / target_file 指定的那个 .md 文件，不要重新选择其他文件。
2. 当前 job 是 cheap tier，只处理普通 Obsidian 指令；深度分析、复杂推理、跨多篇综合、明确 model: strong 的任务由强模型 job 处理。
3. 读取目标文件内容，根据其中指令完成任务。优先使用现有本地文件和 Obsidian 内容，不需要联网时不要联网。
4. 输出目录以 Script Output 中的 Output dir / output_dir 为准；写入文件名格式为 response_YYYYMMDD_HHMMSS.md。
5. 处理成功后，将原文件移动到 Script Output 中的 Processed dir / processed_dir。
6. 处理成功后，追加一行到 Script Output 中的 Index file / index_file，格式：- YYYY-MM-DD HH:MM | tier=cheap | source=<原文件名> | output=<输出文件名> | status=ok。
7. 最终回复只给用户一个简短结果：处理了哪个文件、输出写到哪里、是否已归档、索引是否已更新。

省钱规则：
- 不做用户没有要求的扩展分析。
- 不对整库做广泛扫描，除非目标文件明确要求。
- 敏感信息不要写入输出目录。"
```

### 强模型监听（strong tier，每 10 分钟）

```bash
hermes cron create \
  --name "Obsidian 反向驱动监听（深度强模型）" \
  --script hermes-obsidian-strong-gate.py \
  "*/10 * * * *" \
  "你是 Hermes 的 Obsidian 强模型指令处理引擎，只处理明确标记为强模型/深度任务的文件。运行前本地脚本已经完成目录扫描、任务分层和熔断判断。

执行规则：
1. 只处理 Script Output 中 Selected file / target_file 指定的那个 .md 文件，不要处理普通 cheap tier 文件。
2. 适用任务包括：frontmatter 写了 model: strong / model: deep，或正文明确要求深度分析、复杂推理、跨多篇综合。
3. 根据目标文件完成深度处理，但仍然保持范围克制；只读取任务所需文件。
4. 输出目录以 Script Output 中的 Output dir / output_dir 为准；写入文件名格式为 response_YYYYMMDD_HHMMSS.md。
5. 处理成功后，将原文件移动到 Script Output 中的 Processed dir / processed_dir。
6. 处理成功后，追加一行到 Script Output 中的 Index file / index_file，格式：- YYYY-MM-DD HH:MM | tier=strong | source=<原文件名> | output=<输出文件名> | status=ok。
7. 最终回复只给用户一个简短结果：处理了哪个文件、输出写到哪里、是否已归档、索引是否已更新。

成本规则：
- 只有明确强模型任务才运行本 job。
- 不要做任务外的额外研究或整库扫描。
- 敏感信息不要写入输出目录。"
```

> Hermes `cron create` 当前不暴露 per-job model/provider 参数。要固定模型，可使用全局 Hermes model 配置，或在 `~/.hermes/cron/jobs.json` 中给对应 job 增加 `model` / `provider` 字段。推荐：cheap tier 使用便宜小模型，strong tier 只在显式强任务时使用强模型。

### Obsidian 任务文件模板

普通任务：

```yaml
---
type: summarize
model: cheap
---
请总结这篇笔记。
```

强模型任务：

```yaml
---
type: research
model: strong
---
请做深度分析，必要时跨多篇笔记综合。
```

### 验证监听不烧 token

空 Inbox 时，cron output 应类似：

```text
Script gate returned `wakeAgent=false` — agent skipped.
```

并且 `~/.hermes/sessions/` 下不应出现对应时间的新 `request_dump_cron_<job_id>...json`。

## B 类资源分类目录清单

```
30-Resources/
├── AI 提示词/        # 提示词模板、角色设定
├── SOP 流程/         # 操作流程、标准规范
├── 方案框架/         # 策略、策划模板
├── 工作流设计/       # 决策框架、知识图谱
├── 技术教程/         # 技术笔记、踩坑指南
└── 教学模板/         # 教学相关模板
```

## 常见陷阱

1. **重复归档** — 每次写入前先读取现有文件，避免重复内容
2. **敏感信息泄露** — 密钥、token、联系方式禁止写入任何 Obsidian 文件
3. **过度归档** — 不要保存一次性对话、临时状态、未完成草稿
4. **分类错误** — B 类资源必须具有跨场景复用价值，项目专属内容应归入 C 类
5. **文件命名冲突** — 使用统一的命名格式，避免覆盖已有文件
6. **空轮询烧 token** — 不要恢复为“每 2 分钟直接唤醒 Agent 扫描目录”；必须保留本地 gate
7. **失败无限重试** — 遇到 `Arrearage`、`Invalid token`、`Access denied` 等 provider 错误时，gate 应熔断并跳过 LLM
