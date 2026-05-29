# AI 标准动作模板(写进 project CLAUDE.md 顶部)

```markdown
## 🤖 AI 标准动作(新会话第一步)
0. memory/current-state 是写入时快照非实时 → 引用用 file+符号锚点(非行号);用前先 grep 复核还在。
1. 命中 current-state/memory 条目 → 答前明示"注意:xxx"。
2. build 通过 + 改 ≥5 文件 / 闭合 feature → 走 /pmm log。
3. 需要结构 / 符号位置 / 调用关系 → 直接读代码 / grep;大库要 callers/deps 图查询才跑 codegraph(`python3 ~/.claude/skills/project-mental-model/tools/codegraph/cli.py map|where|callers|deps`)。不维护骨架文档。
4. "整理/重做/全量" → 走 /pmm。
不要:Last scanned 超期自动全量 / 小修(<5 文件)沉淀 / 把认知塞 current-state / 写流水。
```
