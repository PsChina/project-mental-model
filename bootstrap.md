# 环境自举(install / 自完善)— project-mental-model

> 首次建模、或在**新机器 / 新 workspace**、或**别人把整个 `project-mental-model/` 目录复制过来**时执行。目的:让 skill 产物**真能被新会话加载、命令唤得起、跨机器可复现**。四条链缺一,产物即孤儿、跨机器不可见、或命令无反应。
> 通则:**首次搭建只跑一条 `bash templates/bootstrap-verify.sh --install`** —— 幂等装齐核心链(只补缺、不覆盖),装完自动复核 PASS/WARN/FAIL,替代过去手动逐链修。日常体检跑无参版(只读);`--fix` 补孤儿索引。(依赖 bash;纯 Windows 无 git-bash 时跳过脚本,改按下方"接收方启动指南"逐链手动核)· **生成 = 优先复制 `templates/` 下成熟模板(忠实可复现),不凭契约现写** · **均不自动 commit** · 改完一句话告知用户 · settings.json 改动可走 `update-config`。

## 接收方启动指南(别人复制整个 `project-mental-model/` 目录后)

复制单位 = 整个 `~/.claude/skills/project-mental-model/` 目录(自包含,包内零硬编码本机路径,可跨机器)。让它在新机 / 新项目生效 = **两步**:

0. **放对位置**:目录放进 `~/.claude/skills/project-mental-model/`(skill 靠此被原生加载)。
1. **一条命令装齐**:
   ```sh
   bash ~/.claude/skills/project-mental-model/templates/bootstrap-verify.sh --install
   ```
   幂等装核心链(`/pmm` 别名 + 本项目 MEMORY 骨架 + `autoMemoryEnabled` + 保鲜 post-commit + CLAUDE.md 入口指针),只补缺、不覆盖,装完自动复核报 PASS/WARN/FAIL。然后**重开一次会话**(命令别名在会话启动时加载,`/pmm` 才生效)。

> 没有 bash(纯 Windows 无 git-bash)→ 按下方各链手动核;有 bash 一律用 `--install`。
> `--install` 已解开"要 `/pmm` 才能建 `/pmm`"的死循环——它直接把别名装上,不靠敲 `/pmm`。

## 三层产物(决定"复制即生效"的边界)

| 层 | 内容 | 在哪 | 移植性 |
|---|---|---|---|
| **核心(必自包含)** | skill 本体(SKILL/bootstrap/memory-bar)+ `/pmm` 别名源(`templates/pmm.md`)+ MEMORY 骨架(`templates/MEMORY.md`)+ 四链体检(`templates/bootstrap-verify.sh`)+ 记忆判据 | 全在包内 | ✅ 复制目录即带走,自举即生效 |
| **保鲜写(自包含)** | `templates/pmm-staleness-detect.sh`(结构性 commit → 写 pending flag) | 包内(版本化源) | ✅ 复制就位;查过时走 `/pmm check`,**不依赖**公司 brain |
| **全局索引注入(可选 Tier3)** | `~/.claude/hooks/session-start.js`(开局注入**全局公司 brain 索引** + pmm-pending 主动提示) | 公司 brain 跨 skill 基础设施,**不在本 skill 包** | ⚠️ 接收方无公司 brain 时缺失;**pmm 核心不依赖它**,缺了只是少了开局自动提示,仍可 `/pmm check` 手动查 |

## 链 ① 原生 CLAUDE.md 入口(唯一跨机器 / 不依赖本地 hook)

Claude Code 只原生加载 cwd 逐级向上的 `CLAUDE.md`;而落点(dev-cases / .mental-model)**不在该路径、也不随项目 git 走**(靠本机 hook 注入)。所以必须在**原生加载的 CLAUDE.md**(项目 repo 根;双端则每个 repo 根)留一个入口指针——它随项目自身 git 走,任何机器拉到该 repo 都能看见。

- **检测**:repo 根有无 `CLAUDE.md`,且其中有无指向 `<落点>/<project>/` 的指针(verify 用宽松 grep 落点关键词机检,不再纯靠肉眼)。
- **缺则补一行**(无文件则在 repo 根建最小 CLAUDE.md),用固定 marker 前缀,便于 verify 机检:
  ```
  > 📍 项目心智模型在 <落点>/<project>/ —— 新会话先读 CLAUDE.md(宪法)+ current-state.md。
  ```
- 补入口 = 改项目 repo 文件,不自动 commit,告知用户。

## 链 ② 注入 hook(分三块,标清归属与移植性)

**(a) dev-cases 落点注入**(本机加速层,按 cwd / 关键词注入项目心智;仅有 dev-cases 的 workspace 需要):
- 检 `<workspace>/dev-cases/.hooks/inject.js` 存在,且 `<workspace>/.claude/settings.json` 注册了 SessionStart + UserPromptSubmit 指向它。
- 缺 → **复制模板 [`templates/inject.js`](templates/inject.js)** 到 `<workspace>/dev-cases/.hooks/inject.js`(逐字节,别现写),再把 [`templates/settings.snippet.json`](templates/settings.snippet.json) 的 `_workspace` 块 **merge** 进 `<workspace>/.claude/settings.json`(不整体覆盖)。
  > `templates/inject.js` 是这套注入 hook 的**唯一版本化源**——dev-cases 目录本身不入任何 git,`templates/` 在随 `~/.claude` 同步的位置,是它唯一能版本化、可复现的家。要改注入行为改模板,再复制下去。

**(b) 保鲜检测 post-commit**(pmm 专属,自包含):
- `~/.claude/hooks/pmm-staleness-detect.sh` 存在,且 symlink 为**本项目** `.git/hooks/post-commit`(结构性 commit → 写 pending flag)。
- 缺 → **复制模板 [`templates/pmm-staleness-detect.sh`](templates/pmm-staleness-detect.sh)** 到 `~/.claude/hooks/`,再 `ln -s ~/.claude/hooks/pmm-staleness-detect.sh <repo>/.git/hooks/post-commit`。
  > 历史上此脚本只在 `~/.claude/hooks/`(不随 skill 走),复制 skill 给别人就丢。现已纳入 `templates/` 作版本化源,复制目录即带走。

**(c) 全局索引注入**(可选 Tier3,公司 brain 跨 skill 基础设施,**非 pmm 独有**):
- `~/.claude/hooks/session-start.js` 是否在 `~/.claude/settings.json` 注册。它注入的是**全局公司 brain 索引**(`~/.claude/memory/MEMORY.md`)+ 读 pmm-pending flag 做开局提示。
- 缺 → merge [`templates/settings.snippet.json`](templates/settings.snippet.json) 的 `_global` 块(脚本本体随你的 `~/.claude` git 仓库同步,无该仓库时此层缺失)。
  > ⚠️ 这是**可选增强**:它喂的 `~/.claude/memory/MEMORY.md`(全局公司 brain)与 pmm 模式 B 写的 `~/.claude/projects/*/memory/MEMORY.md`(**项目** auto-memory)是**两个不同文件、两个池**。pmm 核心只依赖后者(harness 原生注入);缺了 session-start.js,只是少了开局自动提示"项目心智可能过时",接收方仍可用 `/pmm check` 手动查 pending。

## 链 ③ auto-memory

- `~/.claude/settings.json` 有 `autoMemoryEnabled: true`?缺 → merge [`templates/settings.snippet.json`](templates/settings.snippet.json) 的 `_global` 块(可走 `update-config`)。
  > 这是 pmm ②层(不可推导认知)的**载体与注入,本就是 harness 原生能力** —— pmm 不实现存储/注入,只在此层叠加"5 正 5 反写入判据 + 同步索引行纪律"。显式写 `autoMemoryEnabled:true` 是把隐式默认固化为可复现声明(换机/升级不静默漂移),merge 它幂等无害。
- `~/.claude/projects/<cwd-hash>/memory/MEMORY.md` 索引存在?(`<cwd-hash>` = cwd 路径把 `/` 换成 `-`,harness 约定)缺 → **复制骨架 [`templates/MEMORY.md`](templates/MEMORY.md)**;后续模式 B 沉淀写认知时往这加一行指针。

## 链 ④ 命令别名 `/pmm`

`/pmm` 不是 skill 自带的——它由 `~/.claude/commands/pmm.md` 命令文件提供别名(skill 本名是 `/project-mental-model`)。文件不在 → 敲 `/pmm` 无反应(本 skill 历史上就栽在这)。**这也是"复制 skill 目录"最易丢的链**:别名文件不在 skill 目录内,但其源在包内。

- **检测**:`~/.claude/commands/pmm.md` 是否存在。
- **缺则生成**:**复制模板 [`templates/pmm.md`](templates/pmm.md)** 到 `~/.claude/commands/pmm.md`(薄路由,把 `$ARGUMENTS` 路由到 skill:空=模式 A / `log`=模式 B / `check` / `--rebuild` / `--project`·`--where`;不复制 skill 逻辑)。
- 命令在会话启动时加载 → 新建后需重开会话才生效;告知用户。

## 注入生效前提(写产物时务必满足,否则白写)

- project `CLAUDE.md` 顶部写 `triggers:` frontmatter(用户常用措辞关键词)——否则 UserPromptSubmit 不按输入自动注入它(cwd 落在该子目录时 SessionStart 仍会全文注入,但跨目录按措辞注入会失效)。verify 对落点下每个 `<project>/CLAUDE.md` 机检 `^triggers:`。
- topic case 在 `dev-cases/INDEX.md` 配"触发:"行——否则不会被命中注入。
- 写 auto-memory 认知:**写文件 + 同步在 MEMORY.md 加一行索引**,否则不被注入。verify 做孤儿对账(有 topic 文件无索引行 → 报出)。
