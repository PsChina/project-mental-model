# 环境自举 — project-mental-model

首次建模、换新机器、或复制整个目录之后,要做三件事:让产物能被新会话加载、让 `/pmm` 命令唤得起、让整套东西跨机器可复现。

## 一条命令搞定

```bash
bash templates/bootstrap-verify.sh --install
```

它是幂等的:**包内模板**(pmm.md、staleness 脚本等)每次都重新同步 —— 所以你改了 skill,跑一次就刷新到生效版;**用户文件**(MEMORY.md、CLAUDE.md、settings)只补缺、不覆盖。装完会自动复核一遍。日常体检跑无参版即可,`--fix` 补孤儿索引。**它不会自动 commit。**

装完要**重开一次会话**:命令没有热重载,`/pmm` 别名得新会话才注册。本次会话先用全名 `/project-mental-model`(skill 已经加载了)—— 这也顺带解开了"要先有 /pmm 才能建 /pmm"的死循环。

纯 Windows 没有 bash 的话,照下面四条链手动核对。

> **为什么生效位一律用 `cp` 而不是 symlink**:Claude Code 的发现阶段不跟随 commands / skills 的软链(bug #14836 / #25367),软链会让 `/pmm`、`/skills` 在发现期失效。

## 四条核心链(`--install` 自动补;无 bash 时手动核)

1. **CLAUDE.md 入口指针** —— 跨机器唯一真正必需的一环。
   从 cwd 向上、能被原生加载的那个 CLAUDE.md(通常是项目 repo 根,双端各一个),留一行 `> 📍 项目心智模型在 <落点>/<project>/`。它随项目 git 走,任何机器都看得到。

2. **注入 hook** —— 让心智按场景自动出现,四个子项:
   - (a) dev-cases 注入器:`templates/inject.js` + 把 `settings.snippet.json#_workspace` merge 进去;
   - (b) 保鲜 post-commit:把 `templates/pmm-staleness-detect.sh` symlink 到 `<repo>/.git/hooks/`;
   - (c) 全局索引 session-start:merge `#_global`(**可选,Tier3**,核心不依赖);
   - (d) 自主沉淀触发器:把 `templates/pmm-capture-detect.js` 拷到 `~/.claude/hooks/` + merge `#_global` 的 `UserPromptSubmit` —— 用户消息含决策/纠正/约束时自主触发流程 B(`--install` 自动装;断了仍可手动 `/pmm log`)。

3. **auto-memory** —— 设 `autoMemoryEnabled: true`(merge `#_global`),并把 `templates/MEMORY.md` 拷到 `projects/<把 cwd 路径里的 / 换成 ->/memory/`。

4. **`/pmm` 别名** —— 把 `templates/pmm.md` 拷到 `~/.claude/commands/`,重开会话生效。

## 注入要生效的前提(不满足就白写)

- 项目 CLAUDE.md 顶部有 `triggers:` frontmatter,否则不会按用户措辞跨目录注入;
- dev-cases 的 topic 在 INDEX 里配了"触发:"行;
- auto-memory 每写一个文件,**必须往 MEMORY.md 加一行索引**,否则永不被注入(`--fix` 兜底)。
