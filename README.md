# 🧠 Obsidian Second Brain — AI Agent 通用部署框架

> 将 Obsidian 打造为 AI Agent 的本地持久记忆与知识引擎。零配置冲突，即装即用。

## ✨ 特性

- **🤖 兼容任何 Agent** — Hermes、Claude Code、OpenClaw、Codex 等，具备文件读写能力即可
- **🛡️ 零配置冲突** — `VAULT-MAP.md` + `agent-<name>.md` 命名体系，绝不覆盖 `CLAUDE.md` / `AGENTS.md`
- **💰 Token 节省 90%+** — 双层导航 + 本地监听 gate，告别全库扫描和空轮询烧 token
- **🔄 双向工作流** — 正向归档（A/B/C 分类）+ 反向驱动（轮询 Inbox 执行任务）
- **✅ 幂等部署** — 二次运行无报错、无覆盖，用户自定义内容始终安全
- **🍎 macOS 完全兼容** — 适配 bash 3.2、APFS 大小写不敏感

## 📦 快速安装

### 方式一：Hermes 安装

```bash
hermes skills install richardlyx/obsidian-second-brain
```

安装后执行部署脚本：

```bash
bash ~/.hermes/skills/productivity/obsidian-second-brain/scripts/deploy-second-brain.sh ~/Documents/AI-Knowledge-Base
```

### 方式二：OpenClaw 安装

如果该 skill 已发布到 ClawHub：

```bash
openclaw skills install obsidian-second-brain
```

本地安装可直接复制到当前 OpenClaw workspace：

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R obsidian-second-brain ~/.openclaw/workspace/skills/
~/.openclaw/workspace/skills/obsidian-second-brain/scripts/deploy-second-brain.sh ~/Documents/AI-Knowledge-Base
```

### 方式三：手动部署

```bash
git clone https://github.com/richardlyx/obsidian-second-brain.git
cd obsidian-second-brain
bash scripts/deploy-second-brain.sh /path/to/your/vault
```

### 方式四：一行命令

```bash
curl -fsSL https://raw.githubusercontent.com/richardlyx/obsidian-second-brain/main/scripts/deploy-second-brain.sh | bash -s /path/to/your/vault
```

## 🗺️ 目录结构（PARA + AI 扩展）

```
Vault/
├── VAULT-MAP.md              # 总地图（所有 Agent 共享）
├── agent-<name>.md           # 当前 Agent 专属配置
├── 00-Inbox/                 # 闪念收集、Agent 指令入口
│   ├── for-agent/            # 反向驱动：用户放置任务指令
│   └── processed/            # 已处理任务归档
├── 10-Projects/              # 进行中的项目
├── 20-Areas/                 # 持续关注的领域
├── 30-Resources/             # 可复用知识资产（模板、SOP、方案框架）
├── 40-Archives/              # 已完成项目归档
├── 50-Daily/                 # 每日记录
├── 60-Templates/             # 模板库
├── 70-Agent-Memory/          # Agent 共享记忆
│   ├── inbox/                # A类记忆待审核
│   ├── reviews/              # 已审核记忆
│   ├── processed/            # 已归档
│   └── backups/              # 备份
├── 80-Outputs/               # 生成成品与响应
│   └── <agent-name>-response/ # 当前 Agent 任务产出（可含 _index.md）
└── 99-Attachments/           # 附件存储
```

## 🔄 核心工作流

### 正向归档（每日凌晨 03:30）

Agent 自动将对话中的重要信息分类归档：

| 类别 | 写入位置 | 说明 |
|------|----------|------|
| A类（记忆） | `70-Agent-Memory/inbox/<agent-name>.md` | 用户偏好、环境配置、工具经验 |
| B类（资源） | `30-Resources/` | 提示词模板、SOP、方案框架等可复用知识 |
| C类（进展） | `50-Daily/YYYY-MM-DD.md` | 当日工作日志、待跟进事项 |

### 反向驱动（轮询 Inbox）

用户在 `00-Inbox/for-agent/` 放置任务文件 → 本地 gate 判断是否需要唤醒模型 → 普通任务走 cheap tier，强任务走 strong tier → 结果写入 `80-Outputs/<agent-name>-response/` → 通知用户。

推荐任务模板：

```yaml
---
type: summarize
model: cheap
---
请总结这篇笔记。
```

需要强模型时显式标记：

```yaml
---
type: research
model: strong
---
请做深度分析，必要时跨多篇笔记综合。
```

### 双层导航（Token 节省）

1. **第一层** — Agent 启动时读取 `VAULT-MAP.md`，了解目录架构与铁律
2. **第二层** — 进入目标文件夹前读取 `instructions.md`，获取局部操作指南
3. **监听 gate** — Cron 先跑本地脚本；空 Inbox 输出 `{"wakeAgent": false}`，调度器跳过 LLM
4. **挂载预检** — gate 可通过 `OBSIDIAN_SMB_URL` 自动尝试挂载远程 Vault，避免 NAS/SMB 未挂载导致误判为空
5. **分层模型** — 普通任务默认 cheap tier，只有 `model: strong` / `model: deep` 或“深度分析、复杂推理、跨多篇”等任务进入 strong tier
6. **状态索引** — 处理成功后追加 `_index.md`，记录时间、源文件、输出文件、模型层级和状态
7. **效果** — 无需加载全库内容，按需读取，空轮询 0 token

## 🛡️ 安全设计

| 设计 | 说明 |
|------|------|
| `agent-` 前缀 | macOS APFS 大小写不敏感，`claude.md` 等同于 `CLAUDE.md`，`agent-claude.md` 彻底隔离 |
| 幂等创建 | 所有文件/目录仅在不存在时创建，已存在则跳过 |
| 不扫描全库 | Agent 严格按需读取，不遍历整个 Vault |
| 不修改现有文件 | 用户的 `CLAUDE.md`、`AGENTS.md` 等文件始终安全 |

## ⚠️ 已知陷阱

### bash 3.2 兼容性（macOS 默认版本）

macOS 默认 bash 为 3.2.57，**不支持 bash 4.0+ 语法**：

| 不可用 | 替代方案 |
|--------|----------|
| `${VAR^}`（首字母大写） | `awk '{print toupper(substr($0,1,1)) substr($0,2)}'` |
| `declare -A`（关联数组） | `"key|value"` 字符串 + `${var%%|*}` 解析 |
| 管道内 `set -u` | 写入 `.sh` 文件后执行 |

### macOS 文件名冲突

- ❌ 创建 `claude.md` 在 macOS 上等同于 `CLAUDE.md` → **直接覆盖用户配置**
- ✅ 统一使用 `agent-` 前缀，彻底隔离

## 🧪 部署验证清单

安装后请逐项验证：

- [ ] Agent 检测：运行脚本后输出了正确的 Agent 名称
- [ ] Agent 文件：创建了 `agent-<name>.md`
- [ ] 结构完整：所有 PARA+AI 目录存在
- [ ] 零覆盖：未覆盖任何现有文件
- [ ] 导航可用：`VAULT-MAP.md` 存在
- [ ] 指令文件：各主目录下有 `instructions.md`
- [ ] 幂等安全：二次运行无报错

## 📁 仓库结构

```
obsidian-second-brain/
├── README.md                    # 本文件
├── SKILL.md                     # Skill 完整定义
├── references/
│   └── cron-config-reference.md # Cron 任务配置参考（含完整创建命令和 prompt）
└── scripts/
    ├── deploy-second-brain.sh          # 自动化部署脚本
    ├── hermes-obsidian-gate.py         # cheap tier 本地唤醒 gate
    └── hermes-obsidian-strong-gate.py  # strong tier 本地唤醒 gate
```

## ⏰ 定时任务配置

Skill 安装后需要创建 cron 任务来实现自动化归档和反向驱动。完整的配置参考见 `references/cron-config-reference.md`：

| 任务 | 调度 | 说明 |
|------|------|------|
| 记忆归档 | `30 3 * * *`（每日 03:30） | A/B/C 三类归档到 Obsidian |
| 反向驱动监听（普通） | `*/5 * * * *`（每 5 分钟） | 本地 gate 先判断，有普通任务才唤醒 cheap tier |
| 反向驱动监听（强模型） | `*/10 * * * *`（每 10 分钟） | 仅处理显式强模型/深度任务 |

**Hermes 用户**：复制参考文件中的 `hermes cron create` 命令直接创建
**OpenClaw 用户**：在 heartbeat 配置中添加相应的归档脚本

## 🤝 贡献

欢迎提交 Issue 和 PR。修改部署脚本时请务必遵守：

1. 保持 bash 3.2 兼容性
2. 所有操作幂等
3. 不创建可能冲突的文件名
4. 反向驱动必须保留本地 gate，不能恢复为高频直接唤醒 Agent

## 📄 License

MIT

---

**核心理念**：基于 Serena心心加州 的方法论，将 Obsidian 打造为 AI Agent 的本地持久记忆与知识引擎。
