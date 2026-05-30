---
name: project-mental-model
description: 为项目维护"开局即接续"的心智:① CLAUDE.md 宪法 ② 不可推导认知进 auto-memory ③ current-state 易失态;结构交给读代码/codegraph、不手写。`/pmm` 建·`log` 沉淀·`check` 体检;首次 `bootstrap-verify.sh --install` 一键搭建。
---

# Project Mental Model skill

> 新会话第一秒接续项目心智、不重踩坑:**只采集读代码做不到的不可推导知识**。
> 检查项目 CLAUDE.md 入口是否含落点指针:没有就创建,有就更新对应心智文件;把本次对话按判据沉淀,并更新入口指针。
> 写完跑检查工具确认产物生效。

## 三产物
- **① 宪法** 项目 `CLAUDE.md`(常驻 ≤150 行,顶 `triggers:` frontmatter 否则不注入):范式/跨端约束 + 业务主线一句 + 踩坑指针 + [AI 标准动作](templates/ai-actions.md)。
- **② 认知** auto-memory(`projects/*/memory/`):harness 每会话原生注入;写文件必同步加 MEMORY.md 索引行,否则不注入(判据见「认知存入规则」)。
- **③ 易失** [`current-state.md`](templates/current-state.md):在途阶段/临时方案/坑/债/阻塞,消除即删、无硬上限;已沉淀进 ② 的坑只留 link。

## 落点 · 入口闸
- 落点 `dev-cases/` > `docs/mental-model/` > `.mental-model/`(`--project`/`--where` 覆盖)。
- **入口闸**:CLAUDE.md 无落点指针 → `bash …/templates/bootstrap-verify.sh --install`(一键装核心链;唯一跨机器必需 = 项目 CLAUDE.md 指针;详 [bootstrap.md](bootstrap.md))。

## 认知存入规则
auto-memory 是**末位**(40 条实测仅 3 过闸)。**两道闸,全过才存:**
- **① 会复发**:根因是稳定不变量(设备/协议/架构/SDK)才会;一次性的即便被纠正也不存。
- **② 冷测试**:只读 repo 的新 AI 能从「代码+注释+全局 rule+模型常识」推对的不存。
  - 用户纠正只是触发,不是充分条件:「我不知道」→ 存;「知道没执行好」→ 不存。

**过闸后,往最耐久处写:**
- 能进出错点代码注释/类型 → 写注释(最耐久);写不进、又推不出 → memory(末位)。
- 教训一旦落进更耐久处,对应 memory 即 **supersede**(避免重复)。

拿不准不存,例见 [memory-bar-examples.md](memory-bar-examples.md)。

## 流程
- **A 新建/刷新**(`/pmm`、`--rebuild`、"整理/重做/全量"):并行 Explore 扫源码注释找坑 + 粗读结构理解业务主线 → 写/刷新 ①③ + 顶层 INDEX 指针,标 `Last verified`;刷新 = 增量。不手写会腐烂的结构地图,大库要结构才用 codegraph(命令见铁律 2)。
- **B 会话沉淀**(`log`,或 build 成功 + 改 ≥5 文件 / feature 闭合;≤30 秒只回顾本会话):按「认知存入规则」存入 auto-memory;收尾自检 MEMORY 索引行 + `triggers:`。
- **check**(`bootstrap-verify.sh`,默认只读):四链 PASS/WARN/FAIL + 孤儿对账(`--fix` 补)+ 覆盖自检 + `.pmm-pending` 提示;`--install` 装核心链。

## 铁律
1. CLAUDE.md ≤150 行常驻,只放不可从 代码/lockfile/git 推导的;引用代码用 **file+符号锚点**、不写易漂行号。
2. **不维护可推导的结构地图(模块/调用图/文件树)** —— 读代码/grep,大库才用 codegraph(skill 内 vendored 零安装 `python3 tools/codegraph/cli.py map|where|callers|deps|impact`;外部 `pipx install "git+https://github.com/PsChina/project-mental-model.git#subdirectory=tools/codegraph"`)。
3. 增量 > 全量,recency-wins,不写 session log/文件清单;**永不自动 commit/push**。
4. **自包含可移植**:复制目录 + 跑一次 `--install` 即在新机生效,包内零硬编码路径;全局索引注入(session-start.js)是可选 Tier3。
