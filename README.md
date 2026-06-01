# project-mental-model (PMM)

**English** · [简体中文](README.zh-CN.md)

> A "project mental model" skill for Claude Code: lets every new session pick up this project's full context in the first second — no re-stepping on old landmines.

AI agents have a chronic problem: every new session starts amnesiac — the pitfall you corrected last time, the architecture decision you settled on, a component's non-obvious constraint, all gone, and you re-explain from scratch. PMM fixes exactly this.

The core principle is one sentence: **only record what reading the code can't give you.** Anything derivable from code, comments, global rules, or model common sense is not recorded — so the memory store never piles up into noise.

## Three artifacts

What lets a new session "pick up the context" is these three, split by *where it belongs* and *how long it lives*:

| Artifact | Location | Role |
|---|---|---|
| **① Constitution** | project `CLAUDE.md` (resident, ≤150 lines) | dev paradigm / cross-platform constraints / one-line business thread / pitfall pointers |
| **② Cognition** | auto-memory | non-derivable stable invariants (device / protocol / architecture / SDK behavior) |
| **③ Volatile state** | `current-state.md` | in-flight phase / temporary workarounds / known pitfalls / tech debt / blockers |

## The bar: two gates, store only if both pass

1. **Will it recur?** — only a stable invariant root-cause recurs. One-off problems aren't stored.
2. **Can it be derived (cold test)?** — imagine a fresh AI that can only read this repo. Could it figure this out on its own? If yes, don't store it.

In practice ~3 of 40 candidates pass. When in doubt, don't store.

## Autonomous capture (no milestone, no manual call)

PMM ships a global `UserPromptSubmit` hook: **whenever your message contains a decision / correction / new constraint, the AI runs the two gates on the spot and silently records or updates the existing entry** (no duplicates) — you don't have to say "remember this."

> Why pin it to "the moment you send a message": survivorship bias — if the AI did great you just leave and there's no next message; your sending a message (especially a correction) is the highest-value signal.

## Install

```bash
cp -r project-mental-model ~/.claude/skills/project-mental-model
bash ~/.claude/skills/project-mental-model/templates/bootstrap-verify.sh --install
```

`--install` idempotently sets up the chains (command alias / auto-memory skeleton / freshness & autonomous-capture hooks / CLAUDE.md entry pointer) and re-verifies. Reopen a session once so the `/pmm` alias registers.

## Commands

| Command | Action |
|---|---|
| `/pmm` | create / incrementally refresh the project mental model |
| `/pmm log` | capture what this session is worth recording, now |
| `/pmm check` | health-check the four chains + orphan-memory reconciliation + anchor reconciliation |
| `/pmm --rebuild` | rebuild from scratch (lists files to overwrite first) |

## Don't hand-maintain rotting structure maps

When you need a module map / call graph / impact set, read the code on the spot or use the vendored (zero-install) codegraph:

```bash
python3 tools/codegraph/cli.py map|where|callers|deps|impact <file>...
```

## Iron rules

- CLAUDE.md stays ≤150 resident lines; only what can't be derived from code / lockfile / git; reference code by "file + symbol name" anchors, not drifting line numbers.
- Don't maintain derivable structure maps.
- Incremental over full rebuild, new overrides old (recency-wins); no running logs.
- Self-contained & portable: copy the whole directory + run `--install` once and it works on a new machine; no hard-coded paths inside.

## License

[MIT](LICENSE)
