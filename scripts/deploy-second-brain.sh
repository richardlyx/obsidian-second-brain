#!/bin/bash
# deploy-second-brain.sh — 安全幂等部署脚本
# 兼容 macOS bash 3.2.57，经过全面验证
# 用法: bash deploy-second-brain.sh [VAULT_PATH]
#       默认 Vault: ~/Documents/Obsidian Vault
#       可通过 OBSDIDIAN_VAULT_PATH 环境变量覆盖

set -euo pipefail

VAULT="${OBSIDIAN_VAULT_PATH:-${1:-$HOME/Documents/Obsidian Vault}}"

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
