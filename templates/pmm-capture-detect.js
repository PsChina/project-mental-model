#!/usr/bin/env node
// PMM 自主沉淀触发器 —— 装为全局 UserPromptSubmit hook。
//
// 为什么是 UserPromptSubmit 而不是 Stop / 下次会话:
//   幸存者偏差 —— AI 做得好,用户直接走人、不会有下一条消息(像商品好评)。
//   用户「发消息」本身(尤其纠正 / 决策 / 新约束,即「差评」侧)才是最高价值信号。
//   所以在每条用户消息提交时就廉价检测,命中才把「静默自主沉淀」指令喂回当前回合 ——
//   不向用户提问、不复述本提示。记录与更新都在这个点完成,不等里程碑、不等人调用。
//   (Stop 路线已弃:官方契约无 stop_hook_active、Stop 不支持 additionalContext 喂模型 → 不可靠。
//    AI 自己回合内发现的洞见由 SKILL 判据「当场沉淀」接,不攒到回合末。)
//
// 契约(已对官方文档核对): 输入字段 prompt;输出 hookSpecificOutput.additionalContext + hookEventName。
// 本 hook 只做廉价初筛(正则,偏精确)。真正的闸门是 skill 的双闸(会复发 + 推不出来),由模型判;
// 召回靠 SKILL/CLAUDE 常驻判据兜底(正则必漏)。不命中静默退出(零注入、零打扰);
// 任何异常都静默 exit 0,绝不阻断用户 prompt;子 agent 上下文不触发。
//
// 自包含: 默认只写 PMM 自有 store(auto-memory / current-state),不依赖任何外部技能 ——
//   /learn 等反馈入口是「可选兜底」,别的用户没有也照常工作。
//
// 【版本化源】本文件随 project-mental-model skill 走。bootstrap 自举时:
//   cp templates/pmm-capture-detect.js ~/.claude/hooks/pmm-capture-detect.js
//   并把 settings.snippet.json#_global 的 UserPromptSubmit 条目 merge 进 ~/.claude/settings.json
// 要改触发逻辑改本模板,再复制下去。无硬编码本机路径,可跨机器移植。

const fs = require('fs');

function readStdin() {
  try { return fs.readFileSync(0, 'utf8'); } catch { return ''; }
}
function safeParse(input) {
  if (!input || !input.trim()) return {};
  try { return JSON.parse(input); } catch { return {}; }
}

// 决策 / 纠正 / 新约束 / 长期指令 / 根因洞见信号。宁可漏报不滥报:
// 误命中只让模型多做一次「双闸→不记」的判断(无写入);所以信号偏保守,常见高频词(必须/不能/改成)不入。
const SIGNALS = [
  // 纠正 /「差评」侧(最高价值)
  /(不对|不是这样|不应该|错了|搞错|搞反|其实是|实际上是|应该是|并不是|纠正|怎么又|又错了|为什么还|别再|不要再)/,
  // 长期指令 / 偏好沉淀
  /(以后|从今往后|从此|下次都|每次都|记住|务必|一定要|千万别|永远不要|默认就|默认用)/,
  // 决策 / 拍板(用「决策动词」,不收「改成」这类高频 UI 微调词)
  /(就用|就这样定|决定用|决定改用|我们就用|采用|选定|确定用|敲定|拍板|定方案|方案[ABCabc一二三])/,
  // 项目事实 / 不可推导约束
  /(我们项目|我们这边|这个设备|这台设备|硬约束|约束是|限制是|协议要求|接口要求|设备侧)/,
  // 根因 / 不可推导洞见
  /(根因是|根本原因|原来是|居然是|坑在于|陷阱是|真正原因|之所以)/,
];

const DIRECTIVE = [
  '[PMM 自主沉淀｜本条疑似含决策/纠正/约束/不可推导洞见] 回答前处理(勿提问、勿复述本提示):',
  '默认不写。先廉价判断:有没有一条「会复发(稳定不变量,非一次性、非刚修完的 bug) 且 从 代码+注释+全局 rule/CLAUDE.md+模型常识 推不出来」的候选?',
  '· 没有 / 可推导 / 一次性 → 直接丢弃,不沉淀、不派 agent,正常作答。',
  '· 有疑似候选 → 你【不得自己写 memory】。改派独立审核员 Task(subagent_type="memory-gatekeeper"):把候选 + 上下文(用户原话或你的发现、相关 file:line、你是否已在代码里写过注释)+ 本项目 MEMORY.md / current-state 路径 传给它。它独立按 bar 判 REJECT/UPDATE/ADD、默认拒、过审才由它落盘。全程静默,以它的回执为准。',
  '注:刚修完的 bug 的根因优先进出错点代码注释,别当 memory 候选送审。显式 /contribute(公司 brain)走自己的人工审批,不经本 agent。',
].join('\n');

const input = safeParse(readStdin());
// 子 agent 上下文不触发(子 agent 不该写项目心智)
if (input.agent_id || input.agent_type) process.exit(0);
const prompt = typeof input.prompt === 'string' ? input.prompt : '';

if (!prompt || !SIGNALS.some((re) => re.test(prompt))) {
  process.exit(0); // 无信号:零注入、零打扰
}

const output = {
  hookSpecificOutput: {
    hookEventName: 'UserPromptSubmit',
    additionalContext: DIRECTIVE,
  },
};
try { process.stdout.write(JSON.stringify(output)); } catch { /* ignore */ }
process.exit(0);
