---
name: project-mental-model
description: 为任意项目维护"开局即接续"的心智 —— 两层:① CLAUDE.md 常驻宪法(≤150 行,只放不可推导的铁律/约定/指针);② 不可推导知识(坑·业务·商业约束·优势·高沟通成本)进 auto-memory。结构/导航交给读代码 / codegraph,不手写维护骨架。两模式:`/pmm` 建/刷新宪法+current-state;`/pmm log` 或 build 成功+改≥5 文件时自觉沉淀(写前对照 demo 例子,像正例才写)。首次先过入口闸;无 session log;不因 Last scanned 超期自动全量。
---

# Project Mental Model skill

> 让新会话 AI 第一秒接续项目心智、不重踩坑。**只做 codegraph / 读代码做不到的事 —— 采集、结构化、注入不可推导知识。** 结构与导航交给读代码 / codegraph,本 skill 不维护骨架文档。

## 入口闸(被调用时先判断一次,先于两模式)
原生加载的 CLAUDE.md(cwd 逐级向上那个)有没有指向心智落点的指针?**没有** → 跑 `bash ~/.claude/skills/project-mental-model/templates/bootstrap-verify.sh` 看四链 PASS/FAIL → 按 [bootstrap.md](bootstrap.md) 补 → 继续。**有** → 直接继续,不读 bootstrap。

## 两层(其余交给读代码 / codegraph)
| 层 | 文件 | 加载 | 只装"不可推导"的 |
|---|---|---|---|
| ① 宪法 | `CLAUDE.md` | 常驻 ≤150 行 | 铁律/约定(范式、跨端约束)+ 业务主线一句话 + 最易踩坑指针。能 grep / 读代码 / lockfile / linter 得到的不写 |
| ② 不可推导知识 | auto-memory `~/.claude/projects/*/memory/` | MEMORY.md 索引开局注入 | 坑 / 业务模型 / 商业约束 / 优势 / 高沟通成本;一事一条 + Why,可 supersede |

外加 `current-state.md`(易失状态:当前阶段/临时方案/已知坑/债/阻塞;**按需 Read**,分类表有上限)。**注**:它是事实上的第三个产物文件,单列只因性质是"易失状态"而非"永久知识"——别被"两层"叙事误导成只有两个文件。

> **②层载体与注入 = harness 原生 auto-memory**(AI 直接 Write `projects/*/memory/`、开局自动注入)。pmm 不实现存储/注入,此层唯一增量 = `memory-bar-examples.md` 5 正 5 反**写入判据** + 「写文件必同步加 MEMORY.md 索引行」纪律。别把原生能力误记成 pmm 的功劳。

> **不再产 skeleton / flow / map**:模块图、序列图、文件位置都可推导(读代码 / codegraph 更新鲜),手写只会腐化。结构问题 = 读代码;跨端不变量(如双端常量必须一致)= 写进 ② memory,不画 map。
> always-load 越大越降效(ETH −3%,本 skill 产物也属此类,只靠"只装不可推导 + 严筛"压低)→ **宁可漏抓不可滥存**。
> **结构引擎 = codegraph**(`tools/codegraph/`,见其 [README](tools/codegraph/README.md)):读时即时生成 模块图 / 符号位置(`where`)/ 调用方(`callers`)/ 依赖(`deps`),永不腐化 —— 这就是"结构交给读代码 / codegraph"里 codegraph 的真身,补上结构那一半(认知半仍走 ② memory)。T0 纯 Python 零依赖即用;T2(tree-sitter,AST 精度)首次运行自动建 venv,`CODEGRAPH_NO_AUTOINSTALL=1` 可关。跨平台(mac/Linux/Win)。

## 自适应
- **落点**:有 `dev-cases/`→`dev-cases/<project>/`;有 `docs/`→`docs/mental-model/<project>/`;否则 `.mental-model/<project>/`。可 `--project`/`--where` 覆盖。
- **规模**:一个 CLAUDE.md 宪法目测装得下 → 只出宪法;大了才加 current-state。多端项目:跨端必须一致的不变量写进 ② memory(不画 map)。

## 两模式
| 模式 | 触发 | 做 |
|---|---|---|
| A 建/刷新 | `/pmm`、`--rebuild`、用户说"整理/重做/全量" | 扫源码注释找坑 + 读代码理解结构 → 写/刷新 CLAUDE.md 宪法 + current-state(**不产 skeleton/flow/map**) |
| B 沉淀 | `/pmm log`,或 build 成功 + 改 ≥5 文件 / feature 闭合(AI 自觉) | 只做心智沉淀(下方) |

铁律:默认走 B;不因 `Last scanned` 超期自动全量。

## 模式 A(建/刷新,每步一句)
1. **Detect**:推断 `<project>` + 落点;已存在 → 只走"刷新"。
2. **Scan**:并行 Explore agent 扫源码注释(TODO/FIXME/临时/坑/警告,中英)+ 粗读结构理解业务主线;只要事实 + 路径 + 行号。
3. **Write**:① `CLAUDE.md` 宪法(含下方 AI 标准动作 + 业务主线一句话 + 最易踩坑指针;顶部写 `triggers:` frontmatter,否则不被自动注入)② `current-state.md`(注释扫描结果,分类表)③ 顶层 INDEX 追加本项目指针(没有就建最小入口)。每份标 `Last verified`。
4. **刷新**(已存在):current-state 增量(消除的删、新坑追加、可复用坑提议进 memory);宪法有过时铁律才改。

## 模式 B · 心智沉淀(AI 自觉,≤30 秒,只回顾本会话不 grep)
**该不该存**:① 主信号 = 高沟通成本(人类多轮才讲清的 → 直接存,不存下次又得重讲);② 否则命中 坑/业务/商业约束/优势 任一类、且强依赖 AI 写本项目代码。**写前对照 [memory-bar-examples.md](memory-bar-examples.md) 的 5 正 5 反 —— 像正例才写、沾反例就丢、拿不准不写。**
三路分流:
- **认知 → auto-memory**:祈使句一事一条 + Why;坑用 symptom→cause→fix(高频给稳定 ID);**写文件 + 同步加「本项目」MEMORY.md(`projects/<cwd>/memory/`,非全局)索引行(否则不生效;同主题 update 不新增、超 ~40 条降级 archive)**;永不自动 commit。
- **易失状态 → current-state 分类表**:只写真在阻塞 / 真在用的临时方案 / 真没还的债;旧条目 recency-wins 删。
- **文件改动清单 → 不记**(git log 已有)。

**收尾自检(写完即扫,把纪律当机制)**:本次若写了 auto-memory → 核对每个新 topic 文件都加了 MEMORY.md 索引行(否则孤儿不注入);若新建/改了 project `CLAUDE.md` → 核对顶部有 `triggers:` frontmatter。这两条可用 `/pmm check` 机检兜底。

## current-state.md 模板(分类表 + 软上限,增量维护)
```markdown
# <project> · current-state ｜ Last scanned: YYYY-MM-DD ｜ 验证: grep <关键类名>
## 🚧 当前阶段(≤3)   ## 🩹 临时方案(≤6,附何时撤)   ## ⚠️ 已知坑(≤8,symptom→cause→fix;可复用的进 memory)
## 🧹 优化债(≤8)     ## ⛔ 阻塞
```
溢出最旧降级 archive;已消除的 TODO/阻塞删掉。安全/审计级内容只放**指针到审计报告**,不在此列密钥位置。

## AI 标准动作模板(写进 project CLAUDE.md 顶部)
```markdown
## 🤖 AI 标准动作(新会话第一步)
0. memory/current-state 是写入时快照非实时 → file:line/路径引用先 grep 复核再用。
1. 命中 current-state/memory 相关条目 → 答前明示"注意:xxx"。
2. build 通过 + 改 ≥5 文件 / 闭合 feature → 走 /pmm log(对照 demo 例子沉淀)。
3. 需要项目结构 / 符号位置 / 调用关系 → 跑 codegraph(`python3 ~/.claude/skills/project-mental-model/tools/codegraph/cli.py map|where <sym>|callers <sym>|deps <file>`;读时即时生成、永不腐化),或直接读代码;本项目不维护骨架文档。
4. 用户说"整理/重做/全量" → 走 /pmm。
不要:Last scanned 超期自动全量 / 小修(<5 文件)沉淀 / 把认知塞 current-state / 写流水。
```

## 命令
`/pmm` 建/刷新 · `/pmm log` 沉淀 · `--rebuild` 重做(列覆盖待确认) · `check` 只体检 · `--project`/`--where` 覆盖。

## check 模式(默认只读体检;仅 `--fix` 写)
1. 跑 `bootstrap-verify.sh` 报四链 PASS/WARN/FAIL(含孤儿 memory 对账、triggers 机检、入口指针机检)。孤儿(topic 文件在、MEMORY.md 无索引行)默认**只报告**;`/pmm check --fix` 对**有 `description` frontmatter** 的孤儿**自动补索引行**(取不到 description 的仍只报、不乱写),消除"写了 memory 忘加索引→静默不注入"的高频失败。
2. **覆盖自检(只召回"已知却漏存的",非完整性保证)**:对照 memory-bar 五类目(坑/业务/商业约束/优势/高沟通成本)逐类问"本项目这一类有无已知却未沉淀的"——给"全"侧一个粗粒度信号(否则只有"省"侧的 ≤150 行/~40 条硬上限,**过省不可观测**)。**边界**:它只能捞回已暴露但漏存的,发现不了 AI 自己都不知道的坑(unknown unknowns);别把它当完整覆盖。
3. **pending 报告**:读 `~/.claude/.pmm-pending/<repo>.flag`,有则报"结构性改动未沉淀,建议 /pmm log"(自包含,接收方无 Tier3 开局注入也能查)。

## 铁律
1. CLAUDE.md ≤150 行常驻,只放不可从 代码/lockfile/linter/git 推导的。
2. 认知进 auto-memory(写前对照例子、加本项目 MEMORY.md 索引),current-state 只放易失状态、只引指针。
3. **不维护骨架/流程/位置文档** —— 结构交给读代码 / codegraph;跨端不变量写进 memory。
4. 增量 > 全量,recency-wins,不写 session log / 文件改动清单。
5. 永不自动 commit/push;环境自举从 `templates/` 复制、幂等只补缺、改完告知。**skill 自包含可移植**:复制整个 `project-mental-model/` 目录 + 跑一次自举(见 bootstrap.md 接收方指南)即在新机器生效,包内零硬编码本机路径;核心链全自包含,全局索引注入(session-start.js)是可选 Tier3。

## 与 memory 的关系(三落点对照 —— pmm 自身只拥有判据与剪裁,注入路径都是借来的)
| 落点 | 放什么 | 注入机制 | 谁实现 |
|---|---|---|---|
| 项目 auto-memory `projects/*/memory/` | 不可推导认知(主落点) | MEMORY.md 索引**开局全量注入** | **harness 原生**(pmm 只叠判据+索引纪律) |
| 全局 memory `~/.claude/memory/`(若有) | 跨项目升级处 | **不自动注入**(靠可选 session-start.js 注入其索引 head) | 公司 brain 层(与项目 auto-memory 是**两个不同文件/池**) |
| `dev-cases/<project>/`(若有) | 项目心智 + 跨项目 idiom case | 靠 `triggers:` frontmatter / INDEX | workspace hook(`inject.js`,本机加速层) |
| repo 根 `CLAUDE.md` | 入口指针(链①) | harness 原生加载 cwd 向上的 CLAUDE.md | harness 原生 |
