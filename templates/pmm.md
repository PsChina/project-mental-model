---
description: 项目心智模型(别名 /pmm)。无参=全量建/刷新;/pmm log=心智沉淀;/pmm check=体检;/pmm --rebuild=重做;/pmm --project|--where 覆盖。
---

# /pmm — Project Mental Model(别名)

调用 `project-mental-model` skill(用 Skill 工具,skill 名 `project-mental-model`),按下方路由解析 `$ARGUMENTS` 决定走哪个模式。**唯一事实源是该 skill 的 SKILL.md / bootstrap.md**,本命令只做入口路由,不复制其逻辑。

## 路由(解析 $ARGUMENTS)

| 输入 | 模式 | 动作 |
|---|---|---|
| (空) | A 建/刷新 | 落点不存在 → 首建(CLAUDE.md 宪法 + current-state);已存在 → 增量刷新 current-state |
| `log` | B 沉淀 | 立即走模式 B 心智沉淀(认知→memory / 易失状态→current-state / 文件清单→不记),不重扫源码 |
| `check` | — | 体检(不写文件):bootstrap-verify 四链 + 孤儿 memory / triggers / 入口指针机检 + current-state 锚点对账(符号 grep 不到的标"可能失效")+ 覆盖自检(memory-bar 五类逐类问有无未沉淀)+ 读 pmm-pending flag 报告 |
| `--rebuild` | A 重做 | 放弃增量从头做,**先列将覆盖的文件,待用户确认再执行** |
| `--project <name>` / `--where <path>` | — | 覆盖项目名 / 落点,再按上面模式跑 |

用户输入:`$ARGUMENTS`

## 必做

- 首次建模(或新机器 / 新 workspace)→ 先按 skill 的 **bootstrap.md** 做环境自举三检(原生 CLAUDE.md 入口 / 注入 hook / auto-memory),缺则生成。
- 遵守 skill 铁律:认知进 auto-memory、**写 memory 必同步加 MEMORY.md 索引行**(否则不被注入)、**永不自动 commit**。

## 不要做

- ❌ 用户敲 `/pmm` 已是明确指令,别再问"要建吗"(`--rebuild` 列覆盖清单确认除外)。
- ❌ 不要把 skill 逻辑复制进本文件——只路由 + 调 skill。
