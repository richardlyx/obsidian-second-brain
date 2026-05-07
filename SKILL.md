---
name: obsidian-second-brain
description: Universal framework for deploying Obsidian as any AI Agent's local "Second Brain". Features PARA+AI architecture, conflict-free navigation, token-saving rules, automated agent detection, and bidirectional workflows.
---

# 🧠 Obsidian 第二大脑通用部署指南

> 核心理念：基于 **Serena心心加州** 的方法论，将 Obsidian 打造为 AI Agent 的本地持久记忆与知识引擎。
> **设计目标**：兼容任何具备文件读写能力的 Agent（Hermes, Claude Code, OpenClaw, Codex 等），零配置冲突，即装即用。

## 🛡️ 1. 兼容性与安全设计

### 1.1 文件命名规范（防冲突）

| 文件类型 | 命名 | 用途 | 为什么安全 |
|---------|------|------|-----------|
| 全局地图 | `VAULT-MAP.md` | 所有 Agent 共享的 Vault 总入口 | 不会与 `CLAUDE.md` / `AGENTS.md` 冲突 |
| Agent 专属 | `agent-<name>.md` | 当前 Agent 的个性化配置 | `agent-` 前缀在 macOS 上不会与任何原生配置冲突（如 `claude.md` = `CLAUDE.md`） |

### 1.2 安全红线
- **绝不在 Vault 根目录创建** `CLAUDE.md`、`AGENTS.md`、`AGENT.md` 等可能冲突的文件名
- **幂等部署**：所有文件/目录仅在不存在时创建，已存在则跳过
- **macOS APFS 兼容**：所有文件名在大小写不敏感文件系统下均安全

### 1.3 Agent 初始化指令
任何安装此 Skill 的 Agent，必须在会话启动时执行：
1. 读取 `$OBSIDIAN_VAULT_PATH/VAULT-MAP.md`（获取全局架构与规则）
2. 读取 `$OBSIDIAN_VAULT_PATH/agent-*.md`（获取当前 Agent 的专属配置）
3. 进入目标文件夹前，必读该目录下的 `instructions.md`
4. **严禁全库扫描**，仅按需读取（渐进式披露）

## 📦 2. 自动化部署脚本

**快速部署**: 运行 `scripts/deploy-second-brain.sh`（可执行脚本，已通过全面验证）。
**Vault 路径**: 通过参数 `$1` 或环境变量 `OBSIDIAN_VAULT_PATH` 指定，默认 `~/Documents/Obsidian Vault`。

运行以下脚本完成初始化。脚本包含 **Agent 身份自动检测**、**冲突防护** 与 **目录创建**：

```bash
#!/bin/bash
# deploy-second-brain.sh — 安全幂等部署
set -euo pipefail

VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

echo "🚀 正在部署 Obsidian 第二大脑到: $VAULT"
mkdir -p "$VAULT"

# ════════════════════════════════════════════════════════════
# 0. Agent 身份检测（轻量级，零依赖，3层优先级）
# ════════════════════════════════════════════════════════════
detect_agent() {
    # L1: 环境变量
    [ -n "${ANTHROPIC_API_KEY:-}" ]  && { echo "claude";  return; }
    [ -n "${HERMES_CONFIG:-}" ]      && { echo "hermes";  return; }
    [ -n "${HERMES_HOME:-}" ]        && { echo "hermes";  return; }
    [ -n "${OPENCLAW_CONFIG:-}" ]    && { echo "openclaw"; return; }
    [ -n "${CODEX:-}" ]              && { echo "codex";   return; }

    # L2: CLI 命令
    command -v claude  &>/dev/null && { echo "claude";  return; }
    command -v hermes  &>/dev/null && { echo "hermes";  return; }
    command -v openclaw &>/dev/null && { echo "openclaw"; return; }
    command -v codex   &>/dev/null && { echo "codex";   return; }

    # L3: 特征目录
    [ -d "$HOME/.claude" ]  && { echo "claude";  return; }
    [ -d "$HOME/.hermes" ]  && { echo "hermes";  return; }

    # 兜底
    echo "agent"
}

AGENT_NAME=$(detect_agent)
echo "🔍 检测到 Agent: $AGENT_NAME"

# 创建 Agent 专属配置文件（使用 agent- 前缀，macOS 安全）
AGENT_FILE="$VAULT/agent-${AGENT_NAME}.md"
if [ ! -f "$AGENT_FILE" ]; then
    echo "✅ 创建: agent-${AGENT_NAME}.md"
    # 首字母大写（兼容 bash 3.2，macOS 默认版本）
    AGENT_TITLE="$(echo "$AGENT_NAME" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
    cat > "$AGENT_FILE" << AEOF
# ${AGENT_TITLE} Agent — 第二大脑配置

> 本文件由 \`obsidian-second-brain\` skill 自动检测并创建。
> Agent 类型：\`${AGENT_NAME}\`
> 部署时间：$(date +"%Y-%m-%d %H:%M:%S %Z")

## 🧭 使用指南
1. 每次会话启动时读取 \`VAULT-MAP.md\`（全局规则）
2. 严禁全库扫描，仅按需读取目标目录的 \`instructions.md\`
3. 所有任务输出保存至 \`80-Outputs/\`
4. 定期将重要记忆归档至 \`70-Agent-Memory/\`
5. 轮询 \`00-Inbox/for-agent/\` 执行反向驱动任务

## 🔧 环境信息
- **Agent**: ${AGENT_NAME}
- **Vault**: ${VAULT}
- **系统**: $(uname -s) $(uname -m)
- **时间**: $(date +"%Y-%m-%d %H:%M:%S %Z")
AEOF
else
    echo "⚠️ agent-${AGENT_NAME}.md 已存在，跳过"
fi

# ════════════════════════════════════════════════════════════
# 1. 创建全局地图（VAULT-MAP.md）— 仅当不存在时
# ════════════════════════════════════════════════════════════
VAULT_MAP="$VAULT/VAULT-MAP.md"
if [ -f "$VAULT_MAP" ]; then
    echo "⚠️ VAULT-MAP.md 已存在，跳过"
else
    echo "✅ 创建: VAULT-MAP.md"
    cat > "$VAULT_MAP" << 'VEOF'
# 🧠 第二大脑总地图 (VAULT-MAP.md)

## ⚡ Agent 读取铁律
1. **启动必读**: 每次会话开始，必须先读取本文件
2. **局部指南**: 进入任何文件夹前，必读该目录下的 `instructions.md`
3. **禁止全扫**: 绝不允许扫描整个 Vault，按需读取当前任务相关文件
4. **安全红线**: 禁止读取/修改 .env, secrets, passwords 等敏感文件
5. **Agent 配置**: 读取 `agent-*.md` 获取当前 Agent 的专属设置

## 🗺️ 文件夹架构 (PARA + AI)
| 目录 | 用途 | Agent 何时读取 |
|------|------|----------------|
| `00-Inbox/` | 闪念收集、临时输入 | 需要处理新笔记或 `for-agent/` 有指令时 |
| `10-Projects/` | 进行中的项目 | 处理特定项目任务时 |
| `20-Areas/` | 持续关注的领域 | 需要领域背景知识时 |
| `30-Resources/` | 可复用知识资产 | 查找模板、SOP、方案框架时 |
| `40-Archives/` | 已完成项目归档 | 需要历史参考时 |
| `50-Daily/` | 每日记录 | 需要了解近期动态或写日报时 |
| `60-Templates/` | 模板库 | 需要创建标准化文档时 |
| `70-Agent-Memory/` | Agent 共享记忆 | 需要回忆历史偏好、环境配置时 |
| `80-Outputs/` | 生成成品/响应 | 保存任务产出物时 |
| `99-Attachments/` | 附件存储 | 存放非文本文件时 |

## 🔄 自动化工作流
- **每日归档**: 03:30 执行记忆归档（A/B/C 分类）
- **反向驱动**: 每 2 分钟轮询 `00-Inbox/for-agent/`
- **定期清理**: 每月清理 `00-Inbox/processed/`（保留 30 天）
VEOF
fi

# ════════════════════════════════════════════════════════════
# 2. 创建目录结构（幂等，不影响已存在内容）
# ════════════════════════════════════════════════════════════
DIRS=(
    "00-Inbox/for-agent"
    "00-Inbox/processed"
    "10-Projects"
    "20-Areas"
    "30-Resources"
    "40-Archives"
    "50-Daily"
    "60-Templates"
    "70-Agent-Memory/inbox"
    "70-Agent-Memory/reviews"
    "70-Agent-Memory/processed"
    "70-Agent-Memory/backups"
    "80-Outputs/agent-response"
    "80-Outputs/hermes-response"
    "99-Attachments"
)

for d in "${DIRS[@]}"; do
    mkdir -p "$VAULT/$d"
done

# 3. 为主目录生成 instructions.md（仅当不存在时）
# 注意：使用兼容 bash 3.2 的写法（macOS 默认版本）
for info in \
    "00-Inbox|用途: 闪念收集、Agent 指令入口|何时读取: 有新笔记或收到 for-agent/ 任务时|操作: 处理后将文件移至 processed/" \
    "10-Projects|用途: 进行中的项目|何时读取: 处理特定项目任务时|操作: 按项目名创建子文件夹" \
    "20-Areas|用途: 持续关注的领域|何时读取: 需要领域背景知识时|操作: 按领域名组织文件" \
    "30-Resources|用途: 可复用知识资产|何时读取: 查找模板、SOP、方案框架时|操作: 分类存放通用知识" \
    "40-Archives|用途: 已完成项目归档|何时读取: 需要历史参考时|操作: 项目结束后移入" \
    "50-Daily|用途: 每日记录|何时读取: 需要了解近期动态时|操作: 按 YYYY-MM-DD.md 命名" \
    "60-Templates|用途: 模板库|何时读取: 需要创建标准化文档时|操作: 存放各类 .md 模板" \
    "70-Agent-Memory|用途: Agent 共享记忆|何时读取: 需要回忆历史偏好时|操作: A类记忆存入 inbox/" \
    "80-Outputs|用途: 生成成品与响应|何时读取: 需要查看历史产出时|操作: 按任务类型分子目录" \
    "99-Attachments|用途: 附件存储|何时读取: 需要非文本文件时|操作: 存放图片、PDF 等"; do
    dir="${info%%|*}"
    rest="${info#*|}"
    INST_FILE="$VAULT/$dir/instructions.md"
    if [ ! -f "$INST_FILE" ]; then
        printf "# %s 操作指南\n\n## 用途\n%s\n" "$dir" "$rest" > "$INST_FILE"
    fi
done

echo ""
echo "✅ 部署完成！"
echo "   Vault: $VAULT"
echo "   Agent: $AGENT_NAME"
echo "   文件: agent-${AGENT_NAME}.md + VAULT-MAP.md"
```

## 🤖 3. 核心工作流配置

### 3.1 Token 节省机制（双层导航）
- **第一层 (VAULT-MAP.md)**：Agent 仅通过此文件了解目录用途，不加载具体内容
- **第二层 (instructions.md)**：仅当 Agent 需要操作某目录时，才加载该目录的 `instructions.md`
- **效果**：将 Context Window 占用从"全库扫描"降低到"单文件读取"，节省 90%+ Token

### 3.2 自动化归档（每日凌晨）

> ⚠️ **重要：此 skill 仅定义归档规范和目录结构，不会自动创建 cron 任务。**
> 完整的 cron 任务配置参考见 `references/cron-config-reference.md`，包含：
> - 每日 03:30 记忆归档任务的完整创建命令和 prompt
> - 每 2 分钟反向驱动监听任务的完整创建命令
> - B 类资源分类目录清单
> - 常见陷阱和注意事项

安装此 skill 后，你需要在对应 Agent 平台手动创建定时任务：

**Hermes 用户**：运行 `references/cron-config-reference.md` 中的 `hermes cron create` 命令
**OpenClaw 用户**：在 heartbeat 配置中添加相应的归档脚本

归档任务应调用 Agent 的文件读写工具，按以下规则执行：
- **A类 (记忆)**: 写入 `70-Agent-Memory/inbox/<Agent>.md`
- **B类 (资源)**: 写入 `30-Resources/` (需具备跨场景复用价值)
- **C类 (进展)**: 追加至 `50-Daily/YYYY-MM-DD.md`

### 3.3 Obsidian 反向驱动
Agent 定时轮询 `00-Inbox/for-agent/`：
1. 发现 `.md` 文件 → 读取指令
2. 执行任务 → 结果写入 `80-Outputs/agent-response/`
3. 原文件移至 `00-Inbox/processed/`
4. 通知用户

## 🧪 4. 部署验证清单

安装后请逐项验证：
- [ ] **Agent 检测**: 运行脚本后输出了正确的 Agent 名称
- [ ] **Agent 文件**: 创建了 `agent-<name>.md`（非原生名，安全）
- [ ] **结构完整**: 所有 PARA+AI 目录存在
- [ ] **零覆盖**: 未覆盖任何现有文件（特别是 `CLAUDE.md`/`AGENTS.md`）
- [ ] **导航可用**: `VAULT-MAP.md` 存在且含"读取铁律"
- [ ] **指令文件**: 各主目录下有 `instructions.md`
- [ ] **幂等安全**: 二次运行脚本无报错、无重复创建

## ⚠️ 6. 已知陷阱（Pitfalls）

本节记录开发过程中踩过的坑，后续修改脚本时必须遵守。

### 6.1 bash 3.2 兼容性（macOS 默认版本）
macOS 默认 bash 为 3.2.57，**不支持 bash 4.0+ 语法**：
- ❌ `${VAR^}`（首字母大写）→ "bad substitution" → ✅ 改用 `awk '{print toupper(substr($0,1,1)) substr($0,2)}'`
- ❌ `declare -A`（关联数组）→ "bad substitution" → ✅ 改用 `"key|value"` 字符串 + `${var%%|*}` 解析
- ❌ 管道内 `set -u` 可能误判 → ✅ 将脚本写入 `.sh` 文件后执行，不要 `echo | bash`

### 6.2 macOS 文件名冲突（APFS 大小写不敏感）
- ❌ 创建 `claude.md` 在 macOS 上等同于 `CLAUDE.md` / `Claude.md` → **直接覆盖用户配置**
- ✅ 统一使用 `agent-` 前缀（`agent-claude.md`），彻底隔离
- ✅ 也绝不在 Vault 根目录创建 `AGENT.md`、`AGENTS.md` 等可能冲突的文件名

### 6.3 幂等性
- 所有文件/目录创建前必须 `if [ ! -f ... ]` 或 `if [ ! -d ... ]` 检查
- 二次运行不能覆盖用户自定义内容
- 用户手动修改过 `agent-*.md` 后再次部署，文件内容必须保持不变

## 🏗️ 7. 多实例 Skill 安装指南

当需要将此 skill 安装到多个 Agent 实例时，按以下路径分发。

### 7.1 安装目标清单

| 实例类型 | 技能安装路径 | 说明 |
|---------|------------|------|
| Hermes 主实例 | `~/.hermes/skills/productivity/obsidian-second-brain/` | 已有 SKILL.md + scripts/ |
| Hermes Bot3 | `~/.hermes-3/skills/productivity/obsidian-second-brain/` | 独立实例，需复制 |
| Hermes 新媒体 | `~/.hermes-newmedia/skills/productivity/obsidian-second-brain/` | 独立实例，需复制 |
| OpenClaw 全局 | `~/.openclaw/plugin-skills/obsidian-second-brain/` | 所有 OpenClaw Bot 共享 |
| OpenClaw workspace 级 | `~/.openclaw/workspace*/skills/obsidian-second-brain/` | 仅对有 skills 目录的 workspace |

### 7.2 一键安装命令

```bash
# 以主实例为源，分发到所有 Hermes 实例
for home in ~/.hermes ~/.hermes-3 ~/.hermes-newmedia; do
  if [ -d "$home" ]; then
    mkdir -p "$home/skills/productivity/obsidian-second-brain/scripts"
    cp ~/.hermes/skills/productivity/obsidian-second-brain/SKILL.md \
       "$home/skills/productivity/obsidian-second-brain/"
    cp ~/.hermes/skills/productivity/obsidian-second-brain/scripts/deploy-second-brain.sh \
       "$home/skills/productivity/obsidian-second-brain/scripts/"
    echo "✅ $home"
  fi
done

# OpenClaw 全局 plugin-skills
mkdir -p ~/.openclaw/plugin-skills/obsidian-second-brain/scripts
cp ~/.hermes/skills/productivity/obsidian-second-brain/SKILL.md \
   ~/.openclaw/plugin-skills/obsidian-second-brain/
cp ~/.hermes/skills/productivity/obsidian-second-brain/scripts/deploy-second-brain.sh \
   ~/.openclaw/plugin-skills/obsidian-second-brain/scripts/
echo "✅ OpenClaw global"

# OpenClaw workspace-level（仅当 workspace 有 skills 目录时）
for ws in ~/.openclaw/workspace*/; do
  skills_dir="${ws}skills"
  if [ -d "$skills_dir" ] && [ ! -d "$skills_dir/obsidian-second-brain" ]; then
    mkdir -p "$skills_dir/obsidian-second-brain/scripts"
    cp ~/.hermes/skills/productivity/obsidian-second-brain/SKILL.md "$skills_dir/obsidian-second-brain/"
    cp ~/.hermes/skills/productivity/obsidian-second-brain/scripts/deploy-second-brain.sh "$skills_dir/obsidian-second-brain/scripts/"
    echo "✅ $(basename $ws)"
  fi
done
```

### 7.3 OpenClaw 技能加载机制

- **plugin-skills**：全局共享，所有 OpenClaw Bot 自动加载，无需额外配置
- **workspace-level skills**：部分 workspace 有独立 `skills/` 目录（如 workspace-bot1、workspace），这些 workspace 的 Bot 优先加载 workspace 级副本
- 没有独立 skills 目录的 workspace（workspace-bot2/3/4）依赖全局 plugin-skils

### 7.4 验证方法

```bash
# 检查 Hermes 实例
for home in ~/.hermes ~/.hermes-3 ~/.hermes-newmedia; do
  [ -f "$home/skills/productivity/obsidian-second-brain/SKILL.md" ] && echo "✅ $home" || echo "❌ $home"
done

# 检查 OpenClaw
[ -f ~/.openclaw/plugin-skills/obsidian-second-brain/SKILL.md" ] && echo "✅ OpenClaw global" || echo "❌ OpenClaw global"
```

## 🛠️ 8. 维护与迭代
- **每周**: Review `70-Agent-Memory/inbox/`，将高价值记忆合并
- **每月**: 优化 `VAULT-MAP.md`，根据 Agent 读取热点调整导航
- **定期**: 清理 `00-Inbox/processed/` (保留最近 30 天)

## 📋 9. Cron 任务参考配置

实际运行的归档 cron 任务配置见 `references/cron-config-reference.md`，包含：
- 每日 03:30 记忆归档任务的完整流程
- 每 2 分钟反向驱动监听任务
- B 类资源分类目录清单
- 常见陷阱和注意事项
