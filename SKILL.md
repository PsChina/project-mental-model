---
name: project-mental-model
description: 为任意项目维护"开局即接续"的心智。三产物:① CLAUDE.md 常驻宪法(≤150 行,只放不可推导的铁律/约定/指针);② 不可推导认知进 auto-memory;③ current-state 易失状态。结构交给读代码/codegraph,不手写骨架。`/pmm` 建·`log` 沉淀·`check` 体检;首次 `bootstrap-verify.sh --install` 一键搭建。
---

# Project Mental Model skill

> 让新会话 AI 第一秒接续项目心智、不重踩坑。**只做读代码做不到的事 —— 采集注入不可推导知识**;模块图/调用关系/文件树都可推导 → 读代码/codegraph,本 skill 不维护这类**结构地图**(手写只会腐化);坑/认知的**定位**是它的属性、不算地图。

## 入口闸(先于一切)
cwd 向上的 CLAUDE.md 有指向心智落点的指针?**有** → 继续;**没有** → `bash ~/.claude/skills/project-mental-model/templates/bootstrap-verify.sh --install`(一键幂等装齐核心链 + 复核;唯一跨机器必需的是项目 CLAUDE.md 指针。细节 [bootstrap.md](bootstrap.md))。

## 三个产物(只装"不可推导"的)
| 产物 | 文件 | 加载 | 装什么 |
|---|---|---|---|
| ① 宪法 | 项目 `CLAUDE.md` | 常驻 ≤150 行 | 铁律/约定(范式、跨端约束)+ 业务主线一句话 + 最易踩坑指针;顶部 `triggers:` frontmatter 否则不注入 |
| ② 认知 | auto-memory `~/.claude/projects/*/memory/` | MEMORY.md 索引开局注入 | 仅不可推导的不变量(见下方闸);一事一条 + Why,可 supersede |
| ③ 易失状态 | `current-state.md`([模板](templates/current-state.md)) | 按需 Read | 阶段/临时方案/已知坑/债/阻塞;消除即删、无硬上限 |

> **落点**:有 `dev-cases/`→`dev-cases/<project>/`;有 `docs/`→`docs/mental-model/<project>/`;否则 `.mental-model/<project>/`(`--project`/`--where` 覆盖)。宪法装得下就只出 ①,大了才加 ③。
> ②的存储/注入是 **harness 原生**(AI 直接 Write、开局自动注入),pmm 不实现 —— 增量只是下方写入判据 +「写文件必同步加 MEMORY.md 索引行」纪律。

## 该不该存进 ② memory(核心判据,模式 A/B 共用)
auto-memory 每会话注入,是**末位**落点、不是默认(40 条实测审计:仅 3 条过闸)。写前过两闸:
① **会复发** —— 根因是稳定不变量(设备/协议/架构/SDK)→ 会;一次性情境 → 否(**只发生一次的即便被纠正也不存**)。
② **推不出来(冷测试)** —— 设想一个**只读得到 repo、读不到这条**的新 AI:它会照样做错吗?**会做错才存**;能从 代码+注释+全局 rule+模型常识 推对的不存。(用户纠正 = 触发判断、**非充分**:分清「我不知道」[存] vs「我知道、那次没执行好」[不存]。)对照 [memory-bar-examples.md](memory-bar-examples.md);拿不准不存。

**先路由再写(按耐久度,auto-memory 垫底)**:出错点代码注释/类型 → 写代码 · LLM 行为纠正 → 全局 `~/.claude/rules/` · 个人偏好 → `~/.claude/local/CLAUDE.md` · 项目约定/决策 → 项目 CLAUDE.md · UI/平台 idiom → dev-cases · **连代码+注释都推不出的硬件/SDK/协议不变量 → auto-memory**(一事一条+Why,坑用 symptom→cause→fix;写文件必加 MEMORY.md 索引行,`/pmm check --fix` 兜底;永不自动 commit) · 易失 → current-state(已沉淀进 memory 的坑这里只留一行 link、不重抄) · 文件改动 → 不记。
**生命周期**:教训一旦落进代码注释/CLAUDE.md/rule,**memory 退休**(supersede)—— 它把不可推导教训推进 durable 处,不是永久仓库。

## 两模式(默认 B;不因 Last scanned 超期自动全量)
- **A 建/刷新**(`/pmm`、`--rebuild`、"整理/重做/全量"):并行 Explore 扫源码注释找坑(TODO/FIXME/临时/坑,中英)+ 粗读结构理解业务主线 → 写/刷新 ① 宪法(含 [AI 标准动作模板](templates/ai-actions.md) + 业务主线 + 踩坑指针)+ ③ current-state + 顶层 INDEX 指针,各标 `Last verified`。刷新 = 增量(消除的删、新坑追加、可复用坑按上方判据提议进 memory)。
- **B 沉淀**(`/pmm log`,或 build 成功 + 改 ≥5 文件 / feature 闭合,AI 自觉、≤30 秒只回顾本会话):按上方判据写对应落点。**收尾自检**:写了 auto-memory → 每条都加 MEMORY.md 索引行;改了 project CLAUDE.md → 顶部有 `triggers:`。

## 命令 · check
`/pmm` 建/刷新 · `log` 沉淀 · `--rebuild` 重做 · `check` 体检 · `--project`/`--where` 覆盖。
`check` 跑 `bootstrap-verify.sh`(默认只读)报四链 PASS/WARN/FAIL + 孤儿对账(`--fix` 自动补有 description 的孤儿索引)+ 覆盖自检(对照 memory-bar 逐类问"有无已知未沉淀的",只捞已暴露漏存)+ 读 `.pmm-pending` flag 提示;`--install` 一键装核心链。

## 铁律
1. CLAUDE.md ≤150 行常驻,只放不可从 代码/lockfile/linter/git 推导的。
2. 认知按耐久度路由(代码注释 > rules/CLAUDE.md > dev-cases > auto-memory 末位),过冷测试才进 memory + 加索引;current-state 只放易失状态、无硬上限。
3. **不维护可推导的结构地图(模块图/调用图/文件树)** —— 交给读代码/grep(大库才用 codegraph:skill 内 vendored 零安装 `python3 cli.py …`,外部 `pipx install "git+https://github.com/PsChina/project-mental-model.git#subdirectory=tools/codegraph"`)。坑/认知的定位用**稳定锚点(file+符号名,不写易漂行号)**,是路标不是地图。
4. 增量 > 全量,recency-wins,不写 session log/文件改动清单。
5. 永不自动 commit/push。**自包含可移植**:复制整个目录 + 跑一次 `--install` 即在新机生效,包内零硬编码本机路径;核心链自包含,全局索引注入(session-start.js)是可选 Tier3。
