# Recommended Algorithm Design and Meeting Slides (v4)

Historical design dated September 29, 2026. It integrates independent literature research with the latest complete ChatGPT Pro response and supersedes v2/v3's default algorithms and meeting slides. Earlier files remain discussion records.

## Meeting materials

[Eight editable PowerPoint slides](slides/Legal_AI_Final_Methods.pptx) · [PDF](slides/Legal_AI_Final_Methods.pdf) · [English speaker script](slides/中文讲稿.md) · [full preview](slides/Slides_Preview.png).

English slide bodies explain three algorithms, their inputs, execution, examples and rationale. The PPTX speaker notes have also been translated into English; slide contents and layout are unchanged. Text, shapes and tables are editable. The PDF uses rendered slide images for stable reading, not selectable vector text.

## Design and evidence

- [Complete algorithm proposal](最终算法方案.md): representation, A/B/C steps, search limits, exception policy, implementation order and validation.
- [Literature and final choices](文献依据与最终取舍.md): reading coverage, primary sources and adoption/rejection rationale.
- [Complete Pro reply](Pro完整方案答复.txt): an external discussion record, not a substitute for checking original papers.

A represents facts under shared definitions and determines whether unresolved qualifications block a particular use. B proposes executable relations from real passages and revises them using source and execution errors. C derives rules and factual links from legal sources while preserving exceptions, rebuttals and missing premises. C can read A directly; B's frequency or compression benefit does not determine whether a legal fact is usable.

## Editable framework

[draw.io](slides/Core_Framework.drawio) · [SVG](slides/Core_Framework.svg) · [PNG](slides/Core_Framework.png) · [PDF](slides/Core_Framework.pdf).

## Validation limits

The final PPTX contains eight slides, eight note pages and two native tables. File structure, geometry, fonts and reimport were checked, followed by visual inspection of all eight reimported renders. Native Microsoft PowerPoint display was not verified. The separate framework structure and export were checked. Design, slides and script share one example, distinguishing notice dispatch from receipt and separate obligations within a contract.

This is a proposed design requiring implementation and experiments. Superiority to the original alternatives and novelty from combining existing methods are not established. The proposed question is whether purpose-specific treatment of unresolved qualifications reduces misuse while retaining more valid evidence under the same review budget. Historical filenames are preserved.
