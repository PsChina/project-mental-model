# 环境自举 — project-mental-model

> 首次建模 / 新机器 / 复制整个目录后:让产物能被新会话加载、命令唤得起、跨机器可复现。
> **一条命令**:`bash templates/bootstrap-verify.sh --install`(幂等:**包内模板每次重新同步**[改了 skill 跑一次即刷新生效版]、**用户文件[MEMORY/CLAUDE.md]只补缺**,装完自动复核;日常体检跑无参版,`--fix` 补孤儿索引)→ 然后**重开一次会话**(命令无热重载、`/pmm` 才注册;**本次先用全名 `/project-mental-model`**,skill 已加载,这也解了"要 /pmm 才能建 /pmm"死循环)。**均不自动 commit。** 纯 Windows 无 bash → 按下面手动核。
> 注:生效位一律用 **cp 不用 symlink** —— Claude Code 发现阶段不跟随 commands/skills 软链(bug #14836/#25367),软链会让 `/pmm`、`/skills` 在发现期失效。

## 四条核心链(`--install` 自动补;无 bash 时手动核)
- **① CLAUDE.md 入口指针(唯一跨机器)**:cwd 向上原生加载的 CLAUDE.md(项目 repo 根,双端各一)留一行 `> 📍 项目心智模型在 <落点>/<project>/`,随项目 git 走、任何机器都见。
- **② 注入 hook**:(a) dev-cases 注入器 `templates/inject.js` + merge `settings.snippet.json#_workspace`;(b) 保鲜 post-commit = `templates/pmm-staleness-detect.sh` symlink 到 `<repo>/.git/hooks/`;(c) 全局索引 session-start = merge `#_global`(**可选 Tier3**,核心不依赖)。
- **③ auto-memory**:`autoMemoryEnabled:true`(merge `#_global`)+ `templates/MEMORY.md` 拷到 `projects/<cwd 把 / 换 ->/memory/`。
- **④ `/pmm` 别名**:`templates/pmm.md` 拷到 `~/.claude/commands/`,重开会话生效。

## 注入生效前提(否则白写)
项目 CLAUDE.md 顶 `triggers:` frontmatter(否则不按措辞注入)· dev-cases topic 在 INDEX 配"触发:"行 · auto-memory 写文件**必加 MEMORY.md 索引行**(否则不注入,`--fix` 兜底)。
