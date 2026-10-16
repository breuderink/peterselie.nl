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

```bash
npm install                 # @11ty/eleventy (dev dependency)
npx @11ty/eleventy          # builds content/ + archive assets into build/
python3 tools/mediadiet.py  # lossless diet of build/files (zip dedupe, PNG, TIF)
python3 tools/validate.py   # structural + pixel diff of build/ vs the snapshot
```

Content pipeline (after any change to the live snapshot):
`python3 tools/port.py archive/live-2026-10-14 content` regenerates all
page bodies, then `python3 tools/to_md.py` converts the eligible ones to
markdown. Re-validate afterwards — the validator is the gate.

`build/` is deployable as-is (identical URLs and asset paths to the live site).
