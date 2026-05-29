# current-state.md 模板

复制到落点的 `<project>/current-state.md`:

```markdown
# <project> · current-state ｜ Last scanned: YYYY-MM-DD ｜ 验证: grep <关键类名>
## 🚧 当前阶段   ## 🩹 临时方案(附何时撤)   ## ⚠️ 已知坑(symptom→cause→fix)
## 🧹 优化债     ## ⛔ 阻塞
```

**不设硬条数上限**(真实项目合法地 >6 条临时方案,硬数字只刷 ⚠️ 不收敛):准绳是"**每条现在还有效吗**" —— 消除一条删一条,不盲删仍有效的。引用代码用 **file+符号名锚点**(如 `LiveRepository.startRTMPStream`)、不写易漂行号;已沉淀进 memory 的坑**只留一行 link**、不重抄内容。安全/审计内容只放**指针到报告**,不列密钥位置。
