#!/usr/bin/env node
/**
 * dev-cases 自动注入 hook —— 让新会话「必定」关注开发案例库。
 * 单脚本，按 stdin 的 hook_event_name 分支：
 *
 *   SessionStart      L2 子项目识别：按 cwd 判子项目
 *                       · 有项目心智 → 注入 项目 CLAUDE.md 全文 + INDEX 触发表（完整）
 *                       · 无项目心智 → 只注入一行轻量指针（比例注入）
 *   UserPromptSubmit  L3 任务识别：grep 用户措辞 vs INDEX 触发关键词，命中即注入对应 case 全文
 *
 * 设计红线：
 *   · 路径全部从脚本自身位置 / stdin.cwd 推导，绝不写死机器路径
 *   · 任何异常一律静默 exit 0，绝不打断会话
 *   · 只挂在 code/.claude/settings.json（项目级、本机），不碰共享的 ~/.claude/
 */
'use strict';

const fs = require('fs');
const path = require('path');

const DEV_CASES_DIR = path.resolve(__dirname, '..');      // code/dev-cases
const WORKSPACE_DIR = path.resolve(DEV_CASES_DIR, '..');  // code
const INDEX_PATH = path.join(DEV_CASES_DIR, 'INDEX.md');

// ---- 工具 -----------------------------------------------------------------

function exit0() {
  process.exit(0);
}

/** 输出 additionalContext 后退出（带 flush 回调，防 21KB 注入被截断）。 */
function emit(eventName, context) {
  if (!context) exit0();
  const payload = JSON.stringify({
    hookSpecificOutput: { hookEventName: eventName, additionalContext: context },
  });
  process.stdout.write(payload, () => exit0());
}

function readFileSafe(p) {
  try {
    return fs.readFileSync(p, 'utf8');
  } catch {
    return null;
  }
}

/** cwd → code/ 下第一段目录名（子项目名）。cwd 不在工作区内返回 ''。 */
function subProjectOf(cwd) {
  if (!cwd) return '';
  const rel = path.relative(WORKSPACE_DIR, cwd);
  if (!rel || rel.startsWith('..') || path.isAbsolute(rel)) return '';
  return rel.split(path.sep)[0] || '';
}

/** 子项目名 → dev-cases 项目心智目录（剥 -ios/-android 后缀）。无则 null。 */
function projectEntryOf(subProject) {
  if (!subProject) return null;
  const candidates = [subProject, subProject.replace(/[-_](ios|android)$/i, '')];
  for (const c of candidates) {
    const claudeMd = path.join(DEV_CASES_DIR, c, 'CLAUDE.md');
    if (c && fs.existsSync(claudeMd)) return { dir: c, claudeMd };
  }
  return null;
}

/** 解析 markdown 顶部 YAML frontmatter 的 triggers 列表 (小写)。无 frontmatter / 无 triggers 返回 []。 */
function parseFrontmatterTriggers(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!m) return [];
  const tm = m[1].match(/^triggers:\s*\r?\n((?:[ \t]+-\s*.+\r?\n?)+)/m);
  if (!tm) return [];
  return tm[1]
    .split(/\r?\n/)
    .map((l) => l.replace(/^[\s-]+/, '').trim().toLowerCase())
    .filter(Boolean);
}

/** 扫 dev-cases/<project>/CLAUDE.md, 返回有 frontmatter triggers 的项目: [{dir, claudeMd, triggers, content}]。
 *  让 UserPromptSubmit 能按 user 措辞自动注入对应项目入口(不依赖 cwd 在子目录)。 */
function scanProjectTriggers() {
  const out = [];
  let dirents;
  try {
    dirents = fs.readdirSync(DEV_CASES_DIR, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const d of dirents) {
    if (!d.isDirectory() || d.name.startsWith('.')) continue;
    const claudeMd = path.join(DEV_CASES_DIR, d.name, 'CLAUDE.md');
    const content = readFileSafe(claudeMd);
    if (!content) continue;
    const triggers = parseFrontmatterTriggers(content);
    if (triggers.length === 0) continue;
    out.push({ dir: d.name, claudeMd, triggers, content });
  }
  return out;
}

/**
 * 压缩 INDEX.md 为精简触发表：保留分类标题，每条 case 收成
 * `相对路径` + `⟵ 触发关键词`，丢弃「规则:」摘要 /「适用:」/ 空行 / 散文。
 * 命中后由 AI Read case 文件取完整「规则 + 反例 + 正例」。
 */
function compressIndex(indexText) {
  const out = [];
  let pendingPaths = null; // 当前条目待配「触发:」行的路径
  for (const line of indexText.split('\n')) {
    const t = line.trim();
    if (!t) continue; // 删空行
    if (/^#{1,6}\s/.test(t)) {
      pendingPaths = null;
      out.push('\n' + t);
      continue;
    }
    if (/^\s*-\s*\[/.test(line)) {
      const paths = [];
      const linkRe = /\[[^\]]*\]\(([^)]+\.md)\)/g;
      let lm;
      while ((lm = linkRe.exec(line)) !== null) paths.push(lm[1]);
      pendingPaths = paths.length ? paths : null;
      continue;
    }
    const trg = t.match(/^触发\s*[:：]\s*(.+)$/);
    if (trg && pendingPaths) {
      for (const p of pendingPaths) out.push(`${p}\n  ⟵ ${trg[1]}`);
      pendingPaths = null;
      continue;
    }
    // 规则: / 适用: / 其它明细 / 散文 —— 丢弃
  }
  return out.join('\n').trim();
}

// ---- SessionStart：L2 子项目识别 -----------------------------------------

function handleSessionStart(input) {
  const index = readFileSafe(INDEX_PATH);
  if (index === null) exit0(); // 此机器没有 dev-cases —— 静默退出

  const subProject = subProjectOf(input.cwd);
  const entry = projectEntryOf(subProject);

  if (entry) {
    // 完整注入：有专属项目心智
    const projClaude = readFileSafe(entry.claudeMd) || '';
    emit(
      'SessionStart',
      `[dev-cases 自动注入] 当前子项目：${subProject}\n` +
        `本工作区有开发案例库 dev-cases/。下面是必读项目心智 + 跨项目 idiom 触发表。\n\n` +
        `========== 项目心智：dev-cases/${entry.dir}/CLAUDE.md ==========\n` +
        `${projClaude}\n` +
        `（更多项目文档在 dev-cases/${entry.dir}/ 下：current-state.md —— 按需 Read；结构/调用关系直接读代码 / codegraph）\n\n` +
        `========== 跨项目 idiom 精简触发表（源：dev-cases/INDEX.md）==========\n` +
        `格式 = case 路径（相对 dev-cases/）+ ⟵ 触发关键词（代码 cue / 用户措辞 / 设计稿特征）。\n` +
        `命中任一触发 → Read 该 case 文件取完整规则 + 反例 + 正例。\n` +
        `${compressIndex(index)}\n`
    );
  } else {
    // 轻量注入：无专属项目心智（如后端 / 工具类子项目）
    emit(
      'SessionStart',
      `[dev-cases 自动注入] 本工作区 (code/) 有开发案例库：${INDEX_PATH}\n` +
        `当前子项目「${subProject || '(工作区根)'}」暂无专属项目心智文件。\n` +
        `涉及 UI / 状态机 / 平台坑 / 双端一致性时，grep 该 INDEX 找 trigger → Read 对应 case。\n`
    );
  }
}

// ---- UserPromptSubmit：L3 任务识别 ---------------------------------------

/** 从 INDEX 触发行抽「用户措辞」短语：取引号内文本，按 / 、 拆分。 */
function extractPhrases(text) {
  const phrases = [];
  const re = /[“”「『]([^“”」』]{1,60})[“”」』]|"([^"]{1,60})"/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const raw = m[1] || m[2] || '';
    for (let frag of raw.split(/[\/／,，]/)) {
      frag = frag.trim().toLowerCase();
      if (!frag) continue;
      const hasCJK = /[一-鿿]/.test(frag);
      if (frag.length >= (hasCJK ? 3 : 4)) phrases.push(frag);
    }
  }
  return phrases;
}

/** 解析 INDEX.md → [{ relPath, phrases }]。 */
function parseIndex(indexText) {
  const entries = [];
  let cur = null;
  const flush = () => {
    if (cur && cur.relPath) entries.push(cur);
    cur = null;
  };
  for (const line of indexText.split('\n')) {
    const m = line.match(/^\s*-\s*\[[^\]]*\]\(([^)]+\.md)\)/);
    if (m) {
      flush();
      cur = { relPath: m[1], triggerLine: '' };
      continue;
    }
    if (cur && /触发\s*[:：]/.test(line)) cur.triggerLine += ' ' + line;
  }
  flush();
  for (const e of entries) e.phrases = extractPhrases(e.triggerLine);
  return entries;
}

function handleUserPromptSubmit(input) {
  const prompt = (input.prompt || '').toLowerCase();
  if (!prompt.trim()) exit0();

  // L2 项目入口 trigger 命中 — 让 AI 在 cwd 不在子项目时也能建立项目心智 (不需要 user 手动 prompt 读 CLAUDE.md)
  const cwdEntry = projectEntryOf(subProjectOf(input.cwd));
  const projHits = scanProjectTriggers().filter((p) => {
    if (cwdEntry && cwdEntry.dir === p.dir) return false; // SessionStart 已注入,不重复
    return p.triggers.some((t) => prompt.includes(t));
  });

  // L3 跨项目 idiom case 命中 (现有)
  const index = readFileSafe(INDEX_PATH);
  const idxHits = index
    ? parseIndex(index).filter((e) => e.phrases.some((p) => prompt.includes(p)))
    : [];

  if (projHits.length === 0 && idxHits.length === 0) exit0();

  let ctx = '';

  // 项目入口优先注入: 它建立心智上下文, idiom case 是在其上的细节
  for (const p of projHits) {
    ctx +=
      `[dev-cases 项目入口自动注入] 你的措辞命中项目「${p.dir}」的关键词。` +
      `本次任务应先建立该项目心智(架构 / 范式 / SDK 版本 / 已踩坑), 再处理细节。\n\n` +
      `========== dev-cases/${p.dir}/CLAUDE.md ==========\n${p.content}\n\n`;
  }

  // 跨项目 idiom case 注入 (top 3)
  if (idxHits.length > 0) {
    const MAX = 3;
    ctx += `[dev-cases 命中注入] 你的请求命中以下开发案例，实现前先遵循其规则：\n`;
    for (const h of idxHits.slice(0, MAX)) {
      const content = readFileSafe(path.join(DEV_CASES_DIR, h.relPath));
      if (content === null) continue;
      ctx += `\n========== dev-cases/${h.relPath} ==========\n${content}\n`;
    }
    if (idxHits.length > MAX) {
      ctx +=
        `\n（另有 ${idxHits.length - MAX} 条也命中，按需 Read：` +
        idxHits.slice(MAX).map((h) => 'dev-cases/' + h.relPath).join(' , ') +
        `）\n`;
    }
  }

  emit('UserPromptSubmit', ctx);
}

// ---- 入口 -----------------------------------------------------------------

(function main() {
  let raw = '';
  try {
    raw = fs.readFileSync(0, 'utf8');
  } catch {
    exit0();
  }
  let input = {};
  try {
    input = JSON.parse(raw || '{}');
  } catch {
    exit0();
  }
  try {
    if (input.hook_event_name === 'SessionStart') handleSessionStart(input);
    else if (input.hook_event_name === 'UserPromptSubmit') handleUserPromptSubmit(input);
  } catch {
    /* 静默 —— hook 绝不打断会话 */
  }
  exit0();
})();
