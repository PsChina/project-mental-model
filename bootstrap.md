# 环境自举(install / 自完善)— project-mental-model

> 首次建模、新机器 / 新 workspace、或别人把整个 `project-mental-model/` 目录复制过来后执行。目的:让产物**真能被新会话加载、命令唤得起、跨机器可复现**。
> **有 bash:一条命令搞定** —— `bash templates/bootstrap-verify.sh --install`(幂等装齐核心链、只补缺不覆盖,装完自动复核 PASS/WARN/FAIL,替代手动逐链修)。日常体检跑无参版(只读);`--fix` 补孤儿索引。**生成优先复制 `templates/` 成熟模板,均不自动 commit**,settings 改动可走 `update-config`。

## 接收方启动指南(复制整个目录后)= 两步
0. 目录放进 `~/.claude/skills/project-mental-model/`(skill 靠此被原生加载)。
1. `bash ~/.claude/skills/project-mental-model/templates/bootstrap-verify.sh --install` → 然后**重开一次会话**(命令别名在会话启动时加载,`/pmm` 才生效)。

> `--install` 已解开"要 `/pmm` 才能建 `/pmm`"的死循环(它直接装别名,不靠敲 `/pmm`)。纯 Windows 无 git-bash → 按下表各链手动核。

## 四条核心链(`--install` 自动补;无 bash 时按此手动核)

| 链 | 是什么 | 缺则怎么补 | 移植性 |
|---|---|---|---|
| ① CLAUDE.md 入口指针 | **唯一跨机器**:落点(dev-cases/.mental-model)不随项目 git 走,靠本机 hook 注入;所以在 cwd 向上**原生加载的** CLAUDE.md(项目 repo 根;双端每个 repo 根)留一行 marker | 补一行 `> 📍 项目心智模型在 <落点>/<project>/ —— 新会话先读 CLAUDE.md + current-state.md`;改项目文件、不自动 commit | ✅ 随项目自身 git,任何机器拉到都见 |
| ② 注入 hook | (a) dev-cases 注入器(仅有 dev-cases 的 workspace);(b) 保鲜 post-commit;(c) 全局索引 session-start(**可选 Tier3**,pmm 核心不依赖) | (a) 复制 `templates/inject.js` + merge `settings.snippet.json` 的 `_workspace`;(b) 复制 `templates/pmm-staleness-detect.sh`→`~/.claude/hooks/` + `ln -s` 到 `<repo>/.git/hooks/post-commit`;(c) merge `_global` | ✅ 模板源在包内 |
| ③ auto-memory | `autoMemoryEnabled:true`(harness 原生载体)+ 本项目 `MEMORY.md` 索引 | merge `settings.snippet.json` 的 `_global`;复制 `templates/MEMORY.md` 到 `projects/<cwd-hash>/memory/`(`<cwd-hash>` = cwd 把 `/` 换 `-`) | ✅ |
| ④ `/pmm` 别名 | `/pmm` 由 `~/.claude/commands/pmm.md` 提供(skill 本名 `/project-mental-model`),缺则敲 `/pmm` 无反应 | 复制 `templates/pmm.md` → `~/.claude/commands/pmm.md`,**重开会话**生效 | ✅ 源在包内 |

## 注入生效前提(写产物时务必满足,否则白写)
- project `CLAUDE.md` 顶部写 `triggers:` frontmatter(常用措辞关键词)—— 否则 UserPromptSubmit 不按输入注入(cwd 落在该子目录时 SessionStart 仍全文注入)。
- dev-cases topic 在 `INDEX.md` 配"触发:"行 —— 否则不被命中注入。
- 写 auto-memory 认知:**写文件 + 同步加 MEMORY.md 一行索引** —— 否则不注入(verify 做孤儿对账,`--fix` 兜底)。
