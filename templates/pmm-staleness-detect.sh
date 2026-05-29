#!/usr/bin/env bash
# PMM staleness detector — 装为项目的 git post-commit hook。
# 仅在本次 commit 含「结构性变化」时写 staleness flag，供下次会话 SessionStart 提示更新项目心智模型。
# bugfix / 重构 / 格式 commit 不触发（避免噪音）。post-commit 不影响已完成的 commit，任何失败都静默退出。
#
# 【版本化源】本文件是 pmm 保鲜脚本的唯一版本化源（随 skill 目录走）。bootstrap 自举时：
#   cp templates/pmm-staleness-detect.sh ~/.claude/hooks/pmm-staleness-detect.sh
#   ln -s ~/.claude/hooks/pmm-staleness-detect.sh <repo>/.git/hooks/post-commit
# 要改保鲜逻辑改本模板，再复制下去。无硬编码本机路径（全靠 $HOME / git rev-parse 推导），可跨机器移植。
set -uo pipefail

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
reponame=$(basename "$repo_root")
hash=$(git rev-parse --short HEAD 2>/dev/null) || exit 0
# --root 让首个(root)commit 也输出文件列表(否则 root commit 无父 → diff-tree 空 → 漏触发;对非 root commit 行为不变）
namestatus=$(git diff-tree --no-commit-id --name-status -r --root HEAD 2>/dev/null) || exit 0
[ -z "$namestatus" ] && exit 0

reasons=""
add_reason() { reasons="${reasons:+$reasons; }$1"; }

# 信号1：依赖 / SDK 版本文件变更（最强的"心智需更新"信号）
if printf '%s\n' "$namestatus" | grep -qiE '(Package\.(swift|resolved)|\.gradle(\.kts)?|libs\.versions\.toml|Podfile(\.lock)?|requirements\.txt|pyproject\.toml|package\.json|go\.mod|Cargo\.toml)$'; then
  add_reason "依赖/SDK 版本文件变更"
fi

# 信号2：新增 / 删除源文件（目录结构 / 模块切分变化）
ad_count=$(printf '%s\n' "$namestatus" | grep -cE '^[AD]	' || true)
if [ "${ad_count:-0}" -ge 1 ]; then
  add_reason "新增/删除 ${ad_count} 个文件"
fi

# 信号3：新增配置 / 权限 / 环境变量 / 端点（diff 里的 + 行）
if git show HEAD --no-color 2>/dev/null | grep -qE '^\+.*(buildConfigField|<uses-permission|<queries>|\.entitlements|environment\(|process\.env|@(GET|POST|PUT|DELETE|PATCH)\(|@Headers)'; then
  add_reason "配置/权限/环境/端点变更"
fi

# 无结构性信号 → 静默退出
[ -z "$reasons" ] && exit 0

pending_dir="$HOME/.claude/.pmm-pending"
mkdir -p "$pending_dir" 2>/dev/null || exit 0
ts=$(date +%Y-%m-%dT%H:%M:%S)
# 覆盖式：每个 repo 一个 flag，只记最新一次未沉淀的结构性改动（不堆叠）
printf '{"timestamp":"%s","repo":"%s","path":"%s","hash":"%s","reason":"%s"}\n' \
  "$ts" "$reponame" "$repo_root" "$hash" "$reasons" > "$pending_dir/$reponame.flag" 2>/dev/null || true
exit 0
