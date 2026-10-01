Completed 20-case development iteration: typed relations v2

Start with runs/first-run/report-zh.txt and status-complete-v1.json.
These 20 documents are development data. No held-out evaluation or human gold is claimed.

Same original 277 records: no extraction redo or silent semantic rewrite.
Direct supported part_of and member_of edges are stored separately in relations/.
Missing edges are UNKNOWN; no transitivity, property inheritance or group-act inheritance.
Queries describe scoped assertions, not simultaneous facts or legal sufficiency.

config.json fixes support=2 documents, budget=1000 per pool and the audit selection rule.
input-manifest.json hashes the preceding run's original source and view files.
web-tasks/ preserves exact prompts, replies, observed settings, URLs, screenshots and imports.
Ordinary High mode was used; the UI did not expose the exact model identifier. No paid API.

runs/first-run/:
  candidates.json: every candidate and any truncated frontier (none in this run).
  patterns.json: support, status counts, witnesses, all role variants and display groups.
  all-patterns.txt: readable listing of every query, not only repeated queries.
  traces.jsonl.gz: all 14,540 executions, including failures and unknowns.
  inputs/: source text, views and edge evidence stored once for trace references.
  prior-audit-binding-replay.json: previous nine fixed bindings, with separate operator results.
  artifact-validation.json: 138 tests, source-reference checks and 318 old supports replayed.
  summary.json: computational snapshot written BEFORE the later semantic audit.
  completion-summary-v1.json: completion status joined with the later saved audit validation.

Reproduce local computation from workspace root, preserving the existing output:
  python3 scripts/run_typed_development.py run --out REPLAY-NEW
  python3 -m unittest discover -s tests -v

Display groups are organizational skeletons; they do not merge semantic role variants.
The fixed six-binding source audit is a same-model check, not overall accuracy.
Unknown results require targeted diagnosis; a query empty result is not proof of absence.
