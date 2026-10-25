# V21: implemented rule-assisted legal-source retrieval

This document describes implemented code. `rules-and-verdict-v1/PIPELINE.md` remains an earlier design proposal. There are no new-case legal-answer results: the bounded inventory did not identify an eligible new target unused in answering/method adjustment. Code preparation does not validate complete legal capability.

Flow: saved text/provenance → stable source IDs and reversible reading view → raw-law/rule-description indexes → one neutral query fixed in advance → A/B ranking → original-law/dependency recovery → identical final-answer task → raw website-output import → one source review.

Reading views remove only unambiguous citation wrapper characters, preserving visible text, numbering, and character mappings. Cross-line handling requires the same source document and consecutive original lines; otherwise markers remain. Programs do not merge speakers, guess OCR corrections, or summarize facts. Excluding target outcomes/decisive reasoning still needs explicit configured scope and model-assisted source review; keywords cannot prove no leakage.

The legal corpus retains complete selected logical units, source spans, courts/publishers, dates, jurisdiction, source status, and version gaps. SQLite FTS5 BM25 indexes raw text. Existing rule-card text enters a second index unchanged as a retrieval aid, not new law. Unsatisfied conditions do not imply irrelevant law. Two old cards map to source text; the Telesound card depends on noncontiguous paragraph-12 excerpts and remains saved but disabled. Newly acquired banking sources lack cards, so rule-index balance across three legal scopes is not established.

A retrieves up to 40 raw-text candidates. B retrieves 20 raw-text plus 20 rule-index candidates, deduplicates cards by original legal unit, and merges with existing RRF at k=60. Multiple cards for one unit do not vote repeatedly. Both share explicit scope exclusions configured in advance. Unknown versions/scope retain flags rather than assumed compatibility.

Ranked units are attempted with every configured dependency. Missing/excluded dependencies or a combined size above eight units/20,000 characters skips the whole bundle with a reason, rather than cutting conditions/exceptions. Counts use actual presented text/metadata. Complete recovery of every external cross-reference is unproven and disclosed in corpus coverage.

Final models see selected original legal text/metadata, identical permitted facts/question, two complete fictional examples, and shared answer requirements. Rule cards, program checks, old answers, and evaluation points are excluded. Byte-identical A/B inputs schedule one shared answer; otherwise case order alternates A/B, using independent ordinary High self-contained website chats. No Pro or paid API.

Import preserves full raw output. Complete valid JSON and required fields/types are mandatory; ground/citation counts and writing lengths only warn, never delete content. Invalid/incomplete JSON yields null. Missing citations are source errors, separate from structural success. `assessment` evaluates the row proposition; final `reason` explains its consequence for the current legal ground.

Before execution, freeze sources, corpus, configuration, questions, three to five decisive evaluation points, order, prompts, schema, and code. One consolidated review distinguishes unavailable sources, excluded input scope, corpus gaps, retrieval misses, model misreading, applicability errors, technical failure, and real interpretation disputes. References remain model-assisted, not human gold. Without new-case pairs, no method-benefit evaluation is claimed.

Entry: [scripts/rule_retrieval_v21.py](../../../scripts/rule_retrieval_v21.py); method: [rule_retrieval_v21.py](../../../legal_bench/rules_verdict_v1/rule_retrieval_v21.py). `prepare` saves/freezes local files, `verify` checks hashes, and `import` saves one completed website response. None calls models or pushes GitHub.

```sh
python3 scripts/rule_retrieval_v21.py verify --out outputs/rules-verdict-v21-rule-retrieval
```

This round has an empty sample manifest and execution order. Adding cases/cards to the freeze would create a different configuration. Future source/issue expansion requires a new decision; it does not start automatically.
