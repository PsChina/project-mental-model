---
name: project-mental-model
description: 为任意项目维护"开局即接续"的心智。三个产物:① CLAUDE.md 常驻宪法(≤150 行,只放不可推导的铁律/约定/指针);② 不可推导认知进 auto-memory;③ current-state 易失状态。结构/导航交给读代码 / codegraph,不手写骨架。`/pmm` 建/刷新、`/pmm log` 沉淀、`/pmm check` 体检;首次先过入口闸;不因 Last scanned 超期自动全量。
---

# Project Mental Model skill

> 让新会话 AI 第一秒接续项目心智、不重踩坑。**只做读代码 / codegraph 做不到的事 —— 采集并注入不可推导知识。** 模块图 / 文件位置 / 调用关系都可推导 → 交给读代码 / codegraph,本 skill 不维护任何骨架 / 流程 / 位置文档(手写只会腐化)。

## 入口闸(被调用先判一次,先于两模式)
cwd 逐级向上的 CLAUDE.md 有没有指向心智落点的指针?**有** → 直接继续。**没有** → 跑 `bash ~/.claude/skills/project-mental-model/templates/bootstrap-verify.sh` 看四链 PASS/FAIL,按 [bootstrap.md](bootstrap.md) 补,再继续。

## 三个产物(只装"不可推导"的)
| 产物 | 文件 | 加载 | 装什么 |
|---|---|---|---|
| ① 宪法 | `CLAUDE.md` | 常驻 ≤150 行 | 铁律/约定(范式、跨端约束)+ 业务主线一句话 + 最易踩坑指针 |
| ② 认知 | auto-memory `~/.claude/projects/*/memory/` | MEMORY.md 索引开局注入 | 坑 / 业务 / 约束 / 优势 / 高沟通成本;一事一条 + Why,可 supersede |
| ③ 易失状态 | `current-state.md` | 按需 Read | 阶段 / 临时方案 / 已知坑 / 债 / 阻塞;分类表有上限 |

> 共同准则:能 grep / 读代码 / lockfile / linter / git 得到的**不写**;always-load 越大越降效 → **宁可漏抓不可滥存**。
> ②层的存储与注入是 **harness 原生能力**(AI 直接 Write、开局自动注入),pmm 不实现它 —— pmm 的唯一增量 = `memory-bar-examples.md` 写入判据 +「写文件必同步加 MEMORY.md 索引行」纪律。

## 结构引擎 = codegraph
模块图 / 符号位置(`where`)/ 调用方(`callers`)/ 依赖(`deps`)读时即时生成、永不腐化。`tools/codegraph/`(见 [README](tools/codegraph/README.md)):T0 纯 Python 零依赖即用;T2(tree-sitter AST 精度)首次运行自动建 venv(`CODEGRAPH_NO_AUTOINSTALL=1` 可关);跨平台。**跨端不变量(如双端常量必须一致)写进 ② memory,不画 map。**

## 自适应
- **落点**:有 `dev-cases/`→`dev-cases/<project>/`;有 `docs/`→`docs/mental-model/<project>/`;否则 `.mental-model/<project>/`。`--project`/`--where` 覆盖。
- **规模**:宪法目测装得下 → 只出宪法;大了才加 current-state。

## 该不该存进 ② memory(模式 A / B 共用)
无论 A(建/刷新时筛出的坑)还是 B(沉淀),写 ② 认知前都过这道闸。

**两闸全过才存**:① **会复发** —— 第一次踩到就预判它属不属于「会再遇到的那一类」(根因 = 稳定的设备/协议/架构/流程不变量 → 会;一次性情境 → 否,**只发生一次的即便用户纠正也不存**);② **推不出来** —— grep/git/lockfile/读代码/模型常识 都拿不到的才算(用户纠正 = 触发判断、**非充分条件**:分清「我不知道」[存] vs 「我知道但那次没执行好」[不存])。对照 [memory-bar-examples.md](memory-bar-examples.md);拿不准不存。

**存哪(先路由再写)**:
- **仅本项目适用 → 项目 auto-memory**(`projects/<cwd>/memory/`):一事一条 + Why,坑用 symptom→cause→fix;**写文件 + 同步加该项目 MEMORY.md 索引行**(否则不注入,`/pmm check --fix` 兜底);超 ~40 条 archive;永不自动 commit。
- **跨项目通用 → 升全局**(项目 memory 本机私有、换项目即丢):个人通用 → `~/.claude/local/CLAUDE.md`;团队都该照做 → `~/.claude/rules/`(engineering-standards git,同事可见)。工具用法 / 设计规范 / LLM 行为纠正 多属此类。
- **易失状态 → current-state**;**文件改动 → 不记**(git log 已有)。

## 两模式(默认 B;不因 `Last scanned` 超期自动全量)
| 模式 | 触发 | 做 |
|---|---|---|
| A 建/刷新 | `/pmm`、`--rebuild`、"整理/重做/全量" | 扫源码注释找坑 + 读代码理解结构 → 写/刷新 ①宪法 + ③current-state |
| B 沉淀 | `/pmm log`,或 build 成功 + 改 ≥5 文件 / feature 闭合(AI 自觉) | 按共用判据沉淀(下方) |

### 模式 A(每步一句)
1. **Detect**:推断 `<project>` + 落点;已存在 → 只"刷新"。
2. **Scan**:并行 Explore agent 扫源码注释(TODO/FIXME/临时/坑/警告,中英)+ 粗读结构理解业务主线;只要事实 + 路径 + 行号。
3. **Write**:① `CLAUDE.md` 宪法(含下方 AI 标准动作 + 业务主线 + 踩坑指针;顶部 `triggers:` frontmatter,否则不被注入)② `current-state.md`(分类表)③ 顶层 INDEX 追加本项目指针。每份标 `Last verified`。
4. **刷新**:current-state 增量(消除的删、新坑追加、**可复用的坑按上方【该不该存】判据提议进 memory**);宪法有过时铁律才改。

### 模式 B · 沉淀(AI 自觉,≤30 秒,只回顾本会话不 grep)
按上方【该不该存】判据,把本会话值得沉淀的认知写进对应落点。**收尾自检**:写了 auto-memory → 核对每个新 topic 都加了 MEMORY.md 索引行;新建/改了 project CLAUDE.md → 核对顶部有 `triggers:`。`/pmm check` 机检兜底。

## current-state.md 模板
```markdown
# <project> · current-state ｜ Last scanned: YYYY-MM-DD ｜ 验证: grep <关键类名>
## 🚧 当前阶段(≤3)   ## 🩹 临时方案(≤6,附何时撤)   ## ⚠️ 已知坑(≤8,symptom→cause→fix)
## 🧹 优化债(≤8)     ## ⛔ 阻塞
```
溢出最旧 archive;已消除的删掉。安全/审计内容只放**指针到报告**,不列密钥位置。

## AI 标准动作模板(写进 project CLAUDE.md 顶部)
```markdown
## 🤖 AI 标准动作(新会话第一步)
0. memory/current-state 是写入时快照非实时 → file:line/路径引用先 grep 复核再用。
1. 命中 current-state/memory 条目 → 答前明示"注意:xxx"。
2. build 通过 + 改 ≥5 文件 / 闭合 feature → 走 /pmm log。
3. 需要结构 / 符号位置 / 调用关系 → 跑 codegraph(`python3 ~/.claude/skills/project-mental-model/tools/codegraph/cli.py map|where <sym>|callers <sym>|deps <file>`)或直接读代码;不维护骨架文档。
4. "整理/重做/全量" → 走 /pmm。
不要:Last scanned 超期自动全量 / 小修(<5 文件)沉淀 / 把认知塞 current-state / 写流水。
```

## 命令
`/pmm` 建/刷新 · `/pmm log` 沉淀 · `--rebuild` 重做 · `check` 体检 · `--project`/`--where` 覆盖。

## check 模式(默认只读;仅 `--fix` 写)
1. 跑 `bootstrap-verify.sh` 报四链 PASS/WARN/FAIL(含孤儿对账、triggers / 入口指针机检)。孤儿默认**只报告**;`/pmm check --fix` 对有 `description` frontmatter 的孤儿**自动补索引行**(取不到的仍只报),消除"写了 memory 忘加索引 → 静默不注入"。
2. **覆盖自检**:对照 memory-bar 五类目逐类问"本项目有无已知却未沉淀的",给"全"侧一个粗信号。**边界**:只捞已暴露的漏存,发现不了 unknown unknowns。
3. **pending 报告**:读 `~/.claude/.pmm-pending/<repo>.flag`,有则建议 /pmm log。

## 铁律
1. CLAUDE.md ≤150 行常驻,只放不可从 代码 / lockfile / linter / git 推导的。
2. 认知按适用面路由(仅本项目 → 项目 memory;跨项目 → local / rules),写前对照例子 + 加索引;current-state 只放易失状态。
3. **不维护骨架 / 流程 / 位置文档** —— 结构交给读代码 / codegraph。
4. 增量 > 全量,recency-wins,不写 session log / 文件改动清单。
5. 永不自动 commit/push。**自包含可移植**:复制整个 `project-mental-model/` 目录 + 跑一次自举即在新机生效,包内零硬编码本机路径;核心链自包含,全局索引注入(session-start.js)是可选 Tier3。
