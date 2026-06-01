---
name: project-mental-model
description: 为项目维护"开局即接续"的心智:① CLAUDE.md 宪法 ② 不可推导认知进 auto-memory ③ current-state 易失态;结构交给读代码/codegraph、不手写。`/pmm` 建·`log` 沉淀·`check` 体检;首次 `bootstrap-verify.sh --install` 一键搭建。
---

# Project Mental Model skill

让新会话第一秒就接上项目心智、不重踩老坑。核心原则:**只采集"读代码做不到"的知识** —— 凡是能从代码、注释、全局 rule、模型常识推出来的,一律不记。

每次的工作方式:检查项目 CLAUDE.md 里有没有指向心智文件的指针 —— 没有就创建,有就更新对应文件;把本次对话该沉淀的东西按判据存好,更新指针;最后跑检查脚本确认产物真的会被加载。

## 三种产物

新会话能接上心智靠这三样,按"该写哪、能活多久"分工:

- **① 宪法 = 项目 `CLAUDE.md`**(常驻,≤150 行)
  顶部要有 `triggers:` frontmatter,否则 harness 不会按用户措辞注入它。内容只放:开发范式 / 跨端约束、业务主线一句话、踩坑指针,以及 [AI 标准动作](templates/ai-actions.md)。

- **② 认知 = auto-memory**(`projects/*/memory/`)
  harness 每次会话原生注入。**写了 memory 文件,必须同步往 MEMORY.md 加一行索引**,否则它不会被注入(到底什么该写进来,见下面「什么该进 memory」)。

- **③ 易失态 = [`current-state.md`](templates/current-state.md)**
  记在途阶段、临时方案、坑、技术债、阻塞。不设条数上限,判断标准是"每条现在还成立吗" —— 失效一条删一条。已经沉淀进 ② 的坑,这里只留一行链接,不重抄内容。

## 落点 · 入口指针

- **落点**(三产物放在哪个目录):优先 `dev-cases/`,其次 `docs/mental-model/`,再次 `.mental-model/`(用 `--project` / `--where` 覆盖)。
- **入口指针**:项目 CLAUDE.md 必须有一行指向落点,否则新会话根本找不到心智。没有就跑 `bash …/templates/bootstrap-verify.sh --install` 一键装好(跨机器唯一真正必需的就是这行指针;细节见 [bootstrap.md](bootstrap.md))。

## 什么该进 memory(门槛最高的一道判据)

auto-memory 是末位选择,门槛最高 —— 实测 40 条候选只有 3 条过关。**两道闸,都过才存:**

1. **会复发吗** —— 根因是稳定不变量(设备 / 协议 / 架构 / SDK 行为)才会复发。一次性的问题,即便被纠正过,也不存。
2. **推得出来吗(冷测试)** —— 设想一个只读得到这个 repo 的新 AI,它能不能从「代码 + 注释 + 全局 rule + 模型常识」自己推对?能推对的不存。
   - 用户纠正你只是触发信号、不是充分条件:「我也不知道这个坑」→ 存;「这我知道,只是没执行好」→ 不存。

**过了闸,往最耐久的地方写:**
- 能写进出错点的代码注释 / 类型签名 → 写那儿(最耐久,跟代码一起活)。
- 写不进、又推不出来的不变量 → 才进 memory(末位)。
- 一条教训一旦落进更耐久的地方,对应的 memory 就标 supersede,避免两处重复。

拿不准就不存。正反例见 [memory-bar-examples.md](memory-bar-examples.md)。

## 三种流程

- **A 新建 / 刷新**(触发:`/pmm`、`--rebuild`、用户说"整理 / 重做 / 全量")
  并行 Explore 扫源码注释找坑 + 粗读结构理解业务主线 → 写或刷新 ①③ 和顶层 INDEX 指针,标上 `Last verified` 日期。刷新是增量、不是推倒重来。**不手写会随代码腐烂的结构地图**;大库确实需要结构时才用 codegraph(命令见铁律 2)。

- **B 沉淀(自主 · 持续)**(触发:**每条含决策 / 纠正 / 新约束的用户消息** —— 全局 `UserPromptSubmit` hook `pmm-capture-detect.js` 检出信号即喂入静默指令;也含 `log` 显式调用、build 通过 + 改 ≥5 文件 / feature 闭合)
  **为什么钉在「用户发消息」这个点**:幸存者偏差 —— AI 做得好用户直接走人、根本不会有下一条消息(像商品好评);用户发消息(尤其纠正,即「差评」侧)才是最高价值信号。所以不等里程碑、不等人调用,在消息提交时就自主判断,记录与更新都在这完成。
  动作:回顾本次相关上下文,按上面「什么该进 memory」双闸筛 —— 命中先查既有(MEMORY 索引 / current-state 有无相关条目):**有则更新(recency-wins,旧的标失效或删,不堆重复),无则新增** —— 不可推导认知**静默**存入 auto-memory(写文件必同步 MEMORY 索引行)、易失态写 current-state。不向用户提问、不复述提示。收尾自检 MEMORY 索引行和 `triggers:` 还在不在。
  **你自己在回合内发现的不可推导洞见(读代码发现的约束 / 调试得出的根因)当场就沉淀,别攒到回合末或会话末** —— 幸存者偏差的另一面:hook 钉在「用户发消息」上接不住 AI 侧的发现,用户满意离场就再没机会了,只能靠你回合内主动记。
  落点全在 PMM 自有 store(auto-memory / current-state),**不依赖任何外部技能**;环境若另有 `/learn` 之类反馈分类入口,行为纠偏类可交它兜底(没有也照常工作)。

- **check**(跑 `bootstrap-verify.sh`,默认只读不写)
  报四条生效链的 PASS/WARN/FAIL + 孤儿 memory 对账(`--fix` 自动补索引)+ current-state 锚点对账(符号 grep 不到的标"可能失效")+ 覆盖自检 + 读 `.pmm-pending` 提示。`--install` 则一键装好生效链。

## 铁律

1. **CLAUDE.md ≤150 行常驻**,只放无法从 代码 / lockfile / git 推导的内容;引用代码用「文件 + 符号名」锚点,别写会漂的行号。
2. **不维护可推导的结构地图**(模块图 / 调用图 / 文件树)—— 要这些就当场读代码 / grep。大库才用 codegraph(skill 内已 vendored、零安装):
   `python3 tools/codegraph/cli.py map|where|callers|deps|impact <file>...`
   (想全局安装:`pipx install "git+https://github.com/PsChina/project-mental-model.git#subdirectory=tools/codegraph"`)
3. **增量优先于全量**,新覆盖旧(recency-wins);不写流水账 / 文件清单;**永不自动 commit / push**。
4. **自包含、可移植**:复制整个目录 + 跑一次 `--install` 就在新机生效,包内无硬编码路径。`--install` 同时把**自主沉淀触发器** `pmm-capture-detect.js`(全局 UserPromptSubmit hook)拷到 `~/.claude/hooks/` 并 merge 进 settings —— 它让流程 B 在用户消息提交时自主触发(断了核心仍可手动 `/pmm log`)。全局索引注入(session-start.js)是可选项(Tier3),核心不依赖它。
