#!/usr/bin/env bash
# PMM 环境自举 verify —— 检四条「生效链」的 on-disk 事实,报 PASS/WARN/FAIL。
# 把「模型肉眼判生效」降级为「脚本判事实 + 模型只补缺」。评审一致点名:不跑它,生效是薛定谔状态。
# 用法:bash bootstrap-verify.sh [workspace_dir] [--fix] [--install]
#   workspace 默认 = 当前目录(默认只读体检,不写文件)
#   --fix     = 把「孤儿 memory」从只报告升级为自动补 MEMORY.md 索引行(只补有 description 的)
#   --install = 一键幂等装核心链(只补缺、不覆盖):/pmm 别名 + 本项目 MEMORY 骨架 +
#               autoMemoryEnabled + 保鲜 post-commit + CLAUDE.md 入口指针,装完自动复核。
#               ★ 首次搭建只跑这一条,替代过去手动逐链修(复制模板/symlink/merge settings)。
# 退出码:FAIL(❌,核心链未就位)→ 非 0;WARN(⚠️,可选/建议项)不影响退出码;全 PASS → 0。
set -uo pipefail

ws=""; fix=0; install=0
for a in "$@"; do
  case "$a" in --fix) fix=1 ;; --install) install=1 ;; *) ws="$a" ;; esac
done
ws="${ws:-$PWD}"
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
# --fix 用:从 topic 文件 frontmatter 取某 key 值(name/title/description),生成 MEMORY.md 索引行
fm_val() { awk -v k="$2" 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{exit} f&&$0~"^"k":"{sub("^"k":[[:space:]]*","");print;exit}' "$1"; }

echo "PMM bootstrap-verify @ $ws"
echo

# ---- --install:幂等装核心链。包内模板文件每次 cp -f 重新同步(改了 skill 跑一次即刷新生效版;
#      用 cp 不用 symlink —— Claude Code discovery 不跟随 commands/skills 软链,bug #14836/#25367);
#      用户文件(MEMORY/CLAUDE.md/settings)只补缺、不覆盖。装完落到下方 verify 复核 ----
tpl="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # = templates/(本脚本所在目录,模板源)
if [ "$install" -eq 1 ]; then
  echo "INSTALL —— 装/同步核心链(包内模板重新同步,用户文件只补缺):"
  # ④ /pmm 命令别名(包内文件,每次重新同步;cp 非 symlink)
  if [ -f "$tpl/pmm.md" ]; then
    mkdir -p "$hc/commands" && cp -f "$tpl/pmm.md" "$hc/commands/pmm.md" && echo "  ✚ 同步 /pmm 别名 → 重开会话生效;本次会话先用全名 /project-mental-model(skill 已加载)"
  fi
  # ③ 本项目 MEMORY.md 骨架
  if [ ! -f "$proj_mem" ] && [ -f "$tpl/MEMORY.md" ]; then
    mkdir -p "$(dirname "$proj_mem")" && cp "$tpl/MEMORY.md" "$proj_mem" && echo "  ✚ 建本项目 MEMORY.md 骨架"
  fi
  # ③ autoMemoryEnabled(python3 幂等 merge:已为 true 则不动,缺 python3 则跳过)
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$settings" <<'PY' && echo "  ✚ 固化 autoMemoryEnabled:true 到活 settings.json"
import json,sys,os
p=sys.argv[1]
try: d=json.load(open(p)) if os.path.exists(p) else {}
except Exception: d={}
if d.get("autoMemoryEnabled") is True: sys.exit(1)
d["autoMemoryEnabled"]=True
os.makedirs(os.path.dirname(p) or ".",exist_ok=True)
json.dump(d,open(p,"w"),indent=2,ensure_ascii=False)
PY
  fi
  # ②b 保鲜 post-commit(自包含、低成本;可选)
  if [ -f "$tpl/pmm-staleness-detect.sh" ]; then
    mkdir -p "$hc/hooks"; cp -f "$tpl/pmm-staleness-detect.sh" "$hc/hooks/"   # 包内文件,每次重新同步
    if [ -d "$ws/.git" ] && [ ! -e "$ws/.git/hooks/post-commit" ]; then
      ln -s "$hc/hooks/pmm-staleness-detect.sh" "$ws/.git/hooks/post-commit" 2>/dev/null && echo "  ✚ 本项目 post-commit 保鲜检测就位"
    fi
  fi
  # ① CLAUDE.md 入口指针(改项目文件、不 commit;仅在完全无指针时补最小入口)
  if [ -f "$ws/CLAUDE.md" ]; then
    grep -qE '项目心智模型在|dev-cases|mental-model|current-state' "$ws/CLAUDE.md" 2>/dev/null || \
      { printf '\n> 📍 项目心智模型在 <落点>/<project>/ —— 新会话先读 CLAUDE.md(宪法)+ current-state.md。\n' >> "$ws/CLAUDE.md"; echo "  ✚ 在 $ws/CLAUDE.md 追加入口指针(把 <落点> 改成真实路径)"; }
  else
    printf '> 📍 项目心智模型在 <落点>/<project>/ —— 新会话先读 CLAUDE.md(宪法)+ current-state.md。\n' > "$ws/CLAUDE.md"; echo "  ✚ 建最小 $ws/CLAUDE.md 入口(把 <落点> 改成真实路径)"
  fi
  echo "  —— 核心链已就位。/pmm 重开会话生效(命令无热重载、硬约束);本次直接用全名 /project-mental-model。下面 verify 复核:"
  echo
fi

echo "链⓪ skill 原生可加载(Claude Code 从 ~/.claude/skills/ 加载):"
skill_root="$(dirname "$tpl")"; want="$hc/skills/project-mental-model"
if [ ! -f "$skill_root/SKILL.md" ]; then bad "本目录无 SKILL.md,不是有效 skill 包(链⓪)"
elif [ -L "$want" ]; then warn "$want 是 symlink → 命中 discovery bug #25367(/skills 列表/发现失败,执行仍可)→ 建议改真实目录"
elif [ "$skill_root" != "$want" ]; then warn "skill 不在 $want(当前 $skill_root)→ 不会被 Claude Code 原生加载;把整个目录放到该位置再 --install"
else ok "skill 真实目录就位:$want"; fi
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
  orphans=0; repaired=0
  for f in "$mem_dir"/*.md; do
    [ -e "$f" ] || continue
    bn=$(basename "$f")
    [ "$bn" = "MEMORY.md" ] && continue
    grep -q "$bn" "$proj_mem" 2>/dev/null && continue          # 已索引,跳过
    if [ "$fix" -eq 1 ]; then
      desc=$(fm_val "$f" description)
      ttl=$(fm_val "$f" name); [ -z "$ttl" ] && ttl=$(fm_val "$f" title); [ -z "$ttl" ] && ttl="${bn%.md}"
      if [ -n "$desc" ]; then
        printf -- '- [%s](%s) — %s\n' "$ttl" "$bn" "$desc" >> "$proj_mem"
        printf '  🔧 已补索引行:%s\n' "$bn"; repaired=$((repaired+1))
      else
        warn "孤儿 $bn 无 description frontmatter → 不安全自动补,需手动加索引行"; orphans=$((orphans+1))
      fi
    else
      warn "孤儿 memory(文件在但 MEMORY.md 无索引行,不会被注入):$bn —— 跑 /pmm check --fix 自动补"; orphans=$((orphans+1))
    fi
  done
  [ "$repaired" -gt 0 ] && ok "已自动补 $repaired 条孤儿索引行到 MEMORY.md(--fix)"
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
