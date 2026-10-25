# V20.5: four actual reruns and V20.5.1 post-generation acceptance

After explicit side-thread authorization, four fixed P tasks ran once each:
569555/P01,1187427/P01,1954254/P01,1954254/P02. Frozen V20.5 retained complete sources,
fixed model, and original16,384-token output limit.

Outputs were10,414/13,651/10,387/6,150 tokens, all naturally terminated with no out-of-
range or blank references. Repetition remained:1954254/P02 repeated an identical
1,684-character paragraph across two list items. Existing detection checked loops
inside one item and missed cross-item duplication. Analysis coverage also fell from
10/13 in the previous version to3/13.

Source review confirmed wrong object correspondence in all four. It also found an old
rule normalizing legal 'person' to a natural-person type and example contamination.
Independent V20.5.1 post-processing corrected false blocking of optional UNMAPPED
without modifying frozen generation/old output. Forty-six related tests,22 old caches,
and the four new outputs passed through actual post-processing entry checks. Old
errors were not released: all new outputs were rejected for confirmed binding errors
and never entered automatic reasoning.

Sources, incorrect answers, unresolved items, main entry, and original batch pause
remain preserved; no training/push. See the [report](../outputs/proof-evidence-binding-rerun-v20-5/report-zh.md)
for full results, source reasons, and limitations.
