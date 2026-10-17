# Mission notes

Five files at the repo root give coding agents — and you — a shared, durable
memory. Git is the archive; these files are the index. They reference code and
documents (`path @ commit`, DOI, message id), never copy them.

| File | What it is |
|------|-----------|
| `STATE.md` | Current truth: goal, established facts with evidence, unknowns, in-progress experiments, next actions. Rewritten, ~100-line limit. |
| `LOG.md` | Append-only event log: decisions, actions, discoveries, dead ends. Each entry prefixed with agent id + UTC timestamp. Rotated monthly (`LOG-YYYY-MM.md`). |
| `KNOWLEDGE.md` | Distilled durable facts, conclusions, paper summaries, experiment results, dead ends. Every entry cited. |
| `TASKS.md` | One line per task: id, description, owner, status. |
| `TIMELINE.md` | (Optional) Investigation chronology: every event has timestamp, source, actor, confidence. |

## The protocol in one paragraph

On session start, an agent reads `STATE.md` in full, reads the tail of
`LOG.md`, reconciles against the actual code, and logs any discrepancy before
acting. Before acting, it logs the decision — with context, options, and
reversibility — and commits. After acting, it appends to `LOG.md`, updates
`STATE.md` if truth changed, and commits. No action without a LOG entry; no
state change without a commit.

## Auditing what happened and why

1. `STATE.md` — what is true now, and on what evidence.
2. `LOG.md` — why, in order. Grep by agent id or date.
3. `git log` — what changed, when, in which commit.

This should take under five minutes. If it doesn't, the log entries lack
context or evidence — that is a defect to fix.

## Building and validating the site

Build inputs (the rewrite — no archive needed):

- `content/*.md` — 179 pages, markdown, the only thing an editor touches
- `files/` — all site media (single copy; also the oracle's media via symlink)
- `themes/ misc/ modules/` — the site CSS
- `_includes/base.html` + `.eleventy.js` — the theme chrome and config

```bash
npm install     # @11ty/eleventy (dev dependency)
npm run build   # = eleventy -> tools/mediadiet.py -> tools/validate.py
```

`validate.py` is the gate: structural + zero-tolerance pixel diff of every
page, `build/` vs the old site. 179/179 PASS = deployable. The old site
(`archive/live-2026-10-14/`: HTML pages + manifest) is the validator's
oracle and the re-import source — NOT a build input (proven: build + diet
succeed with the archive directory removed). Its `files/ themes/ misc/
modules/` are symlinks to the first-class directories (Linux).

Re-import (re-sync from the old site; wipes local .md edits — do not use
for routine editing):
`python3 tools/port.py archive/live-2026-10-14 content` regenerates all
page bodies, then `python3 tools/to_md.py` converts the eligible ones to
markdown. Re-validate afterwards.

`build/` is deployable as-is (identical URLs and asset paths to the live
site; pages are extensionless, as on the old site).
