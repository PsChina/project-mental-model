#!/usr/bin/env bash
# PMM 环境自举 verify —— 检四条「生效链」的 on-disk 事实,报 PASS/WARN/FAIL。
# 把「模型肉眼判生效」降级为「脚本判事实 + 模型只补缺」。评审一致点名:不跑它,生效是薛定谔状态。
# 用法:bash bootstrap-verify.sh [workspace_dir]   (workspace 默认 = 当前目录)
# 退出码:FAIL(❌,核心链未就位)→ 非 0;WARN(⚠️,可选/建议项)不影响退出码;全 PASS → 0。
set -uo pipefail

ws="${1:-$PWD}"
hc="$HOME/.claude"
settings="$hc/settings.json"
# 本项目 auto-memory 目录:cwd 路径把 / 换成 -(harness 约定)
proj_hash=$(printf '%s' "$PWD" | sed 's#/#-#g')
proj_mem="$hc/projects/$proj_hash/memory/MEMORY.md"

# 落点检测(triggers 检查用):dev-cases > docs/mental-model > .mental-model
if   [ -d "$ws/dev-cases" ];          then mm_root="$ws/dev-cases"
elif [ -d "$ws/docs/mental-model" ];  then mm_root="$ws/docs/mental-model"
elif [ -d "$ws/.mental-model" ];      then mm_root="$ws/.mental-model"
else mm_root=""; fi

fail=0
ok()   { printf '  ✅ %s\n' "$1"; }
warn() { printf '  ⚠️  %s\n' "$1"; }            # 可选/建议项,不置 fail
bad()  { printf '  ❌ %s\n' "$1"; fail=1; }

echo "PMM bootstrap-verify @ $ws"
echo

echo "链① 原生 CLAUDE.md 入口(唯一跨机器):"
if [ -f "$ws/CLAUDE.md" ]; then
  # 机检「有无指向落点的指针」——宽松匹配落点关键词,命中即 PASS(不再纯靠肉眼)
  if grep -qE '项目心智模型在|dev-cases|mental-model|current-state' "$ws/CLAUDE.md" 2>/dev/null; then
    ok "$ws/CLAUDE.md 存在且含指向心智落点的指针"
    grep -q '项目心智模型在' "$ws/CLAUDE.md" 2>/dev/null || \
      warn "建议入口用标准 marker「> 📍 项目心智模型在 <落点>/<project>/」(便于跨项目一致识别)"
  else
    bad "$ws/CLAUDE.md 存在但无任何指向心智落点的指针 → 新会话读不到心智(链①:补一行 marker 指针)"
  fi
else
  bad "$ws/CLAUDE.md 不存在 → 新会话无原生入口(bootstrap 链①:补一行指针)"
fi

echo "链② 注入 hook:"
# (a) dev-cases 注入
if [ -f "$ws/dev-cases/.hooks/inject.js" ]; then
  if grep -q 'inject.js' "$ws/.claude/settings.json" 2>/dev/null; then ok "dev-cases inject.js 存在且已注册"
  else bad "dev-cases inject.js 存在但 $ws/.claude/settings.json 未注册(链②a:merge _workspace)"; fi
else ok "本 workspace 无 dev-cases(跳过 dev-cases 注入检查)"; fi
# (b) 保鲜检测 post-commit(pmm 专属,自包含)
if [ -f "$hc/hooks/pmm-staleness-detect.sh" ]; then ok "pmm-staleness-detect.sh 已就位(~/.claude/hooks/)"
else warn "pmm-staleness-detect.sh 不在 ~/.claude/hooks/(链②b:复制 templates/pmm-staleness-detect.sh;保鲜检测可选,断了核心仍生效)"; fi
if [ -d "$ws/.git" ]; then
  pc="$ws/.git/hooks/post-commit"
  if [ -L "$pc" ] && readlink "$pc" 2>/dev/null | grep -q 'pmm-staleness-detect.sh'; then ok "本项目 post-commit 已 symlink 到 staleness 检测"
  else warn "本项目 .git/hooks/post-commit 未 symlink 到 staleness 检测(链②b:ln -s;可选,里程碑保鲜提示会缺)"; fi
fi
# (c) 全局索引注入(可选 Tier3,公司 brain 跨 skill 层)
if grep -q 'session-start.js' "$settings" 2>/dev/null; then ok "session-start.js 已注册(可选:注入全局公司 brain 索引 + pmm-pending 提示)"
else warn "session-start.js 未注册 → 缺开局自动提示(可选 Tier3;pmm 核心不依赖,可用 /pmm check 手动查 pending)"; fi

echo "链③ auto-memory:"
if grep -q '"autoMemoryEnabled"[[:space:]]*:[[:space:]]*true' "$settings" 2>/dev/null; then ok "autoMemoryEnabled:true 在活 settings.json"
else warn "autoMemoryEnabled 未显式声明 → 可能靠 harness 默认(换机/升级会静默漂移);建议 merge _global 固化(幂等无害)"; fi
if [ -f "$proj_mem" ]; then
  ok "本项目 MEMORY.md 索引存在:$proj_mem"
  # 孤儿对账:topic 文件写了却没加索引行 → 永不被注入(最高频静默失败)
  mem_dir=$(dirname "$proj_mem")
  orphans=0
  for f in "$mem_dir"/*.md; do
    [ -e "$f" ] || continue
    bn=$(basename "$f")
    [ "$bn" = "MEMORY.md" ] && continue
    grep -q "$bn" "$proj_mem" 2>/dev/null || { warn "孤儿 memory(文件在但 MEMORY.md 无索引行,不会被注入):$bn"; orphans=$((orphans+1)); }
  done
  [ "$orphans" -eq 0 ] && ok "MEMORY.md 索引与 topic 文件一致(无孤儿)"
else bad "本项目 MEMORY.md 不存在:$proj_mem(链③:复制 templates/MEMORY.md 骨架)"; fi

echo "链④ /pmm 命令别名:"
if [ -f "$hc/commands/pmm.md" ]; then ok "~/.claude/commands/pmm.md 存在"
else bad "~/.claude/commands/pmm.md 不存在 → 敲 /pmm 无反应(链④:复制 templates/pmm.md)"; fi

echo "落点项目 triggers frontmatter(按措辞自动注入前提):"
if [ -n "$mm_root" ]; then
  found=0
  for cm in "$mm_root"/*/CLAUDE.md; do
    [ -e "$cm" ] || continue
    found=1
    proj=$(basename "$(dirname "$cm")")
    if grep -qE '^triggers:' "$cm" 2>/dev/null; then ok "$proj/CLAUDE.md 有 triggers frontmatter"
    else warn "$proj/CLAUDE.md 缺 triggers frontmatter → 跨目录按措辞自动注入失效(cwd 落在该目录时 SessionStart 仍注入)"; fi
  done
  [ "$found" -eq 0 ] && ok "落点 $mm_root 下暂无 <project>/CLAUDE.md(跳过 triggers 检查)"
else ok "未检出落点目录(跳过 triggers 检查)"; fi

echo
if [ "$fail" -eq 0 ]; then echo "RESULT: PASS —— 核心四链就位,产物能生效(⚠️ 项为可选/建议,不阻塞)。"
else echo "RESULT: FAIL —— 上面 ❌ 的核心链未就位,该项产物会变孤儿;按括号里的链号补(bootstrap.md)。⚠️ 项可选。"; fi
exit "$fail"
