# RAPIDO evaluation framework v2: protocol and completed development annotation

Date: 2026-10-27. This is an **evaluation-only publication**. It does not implement a
new Qwen method, rerun A0, train a model, or create an independent test. The maintained
[evaluation specification](../../docs/evaluation/README.md) fixes metrics, reference
construction, adjudication, missingness, statistics and future change control.

The main metric is important-content coverage **R**: correctly answered important
requirements divided by the frozen requirement count. Source-support precision **P**
checks all distinct substantive assertions, including extra assertions outside those
requirements. Serious errors, main-answer adequacy, delivery, cost and latency remain
mandatory companions. The harmonic **H** is a secondary dashboard summary and cannot
hide serious errors or missing content. Candidate and delivered reports are separate
endpoints; the actual delivered C report is the main endpoint.

## Completed annotation, not an unreadable-reply assumption

The original source-only GPT Web reference and its compact recovery reply were
recovered intact after ready-state checks and repeated reloads. Each proposed 23
requirements. A separate source-only Web audit then checked importance, overlap,
bindings and legal scope without seeing method outputs. Explicit source adjudication
consolidated a **17-item reference**, frozen before the new full blind grading.
The [reference record](web-reference-recovered/reference-adjudication.json) preserves
all consolidation decisions, including disagreement with the audit. No reference
requirement was changed in reaction to a grade.

All three original report texts were anonymized and graded against that same
reference: **51 coverage decisions, 81 assertion records and 12 serious-error
records**. The complete JSON downloaded successfully even while the chat body still
showed “无法加载此回复”. Initial display failures and recovered original bytes are
preserved. A timed-out browser download event did not mean that the file was absent:
the downloaded file was verified directly against all report/source/reference hashes.
Do not regenerate merely because the display cannot load. See [status history](web-annotation-status.json).

The raw [Web labels](web-final-evaluation/labels-web-raw.json), their
[unaltered scores](web-final-evaluation/scores-web-raw.json), all seven
[source-adjudication changes](web-final-evaluation/source-adjudication.json), the
[adjudicated labels](web-final-evaluation/labels-source-adjudicated.json), and
[final arithmetic](web-final-evaluation/scores-source-adjudicated.json) are separate
files. Adjudication corrected, among other things, a false pass for a named appellate
stage, “not raised” versus “not surviving”, and a grader's misreading of “only if”.

These are **source-grounded model reference labels**. GPT Web construction/audit and
one full grading pass were followed by nonblind Codex source adjudication. These
are **provisional single-pass quality results** pending an independent same-reference
grading extension. A second
independent grader under the same 17-item reference has not been completed. This
is neither human gold nor lawyer approval, and the previously exposed case is not
preregistered or independent.

## Primary comparison of existing 1251841 reports

| Existing output | Correct important items R | Supported assertions P | Auxiliary H | Serious events: confirmed + unresolved |
| --- | ---: | ---: | ---: | ---: |
| One ordinary call A0 | 7/17 = 41.2% | 24/34 = 70.6% | 52.0 | 4 + 1 |
| V38 C candidate | 4/17 = 23.5% | 17–20/35 = 48.6–57.1% | 31.7–33.3 | 4 + 1 |
| V38 C actually delivered | 3/17 = 17.6% | 8/12 = 66.7% | 27.9 | 2 + 0 |

All three main answers are **WRONG_OR_OVERREACH**. That does not erase relative
improvement: delivered C has fewer observed serious-error events. However, it has
lower correct important-content coverage and lower support precision than A0. Every
report still contains a serious error, so the serious-error *case rate* is one in
this single dispute for each endpoint. The evidence supports a content/error
tradeoff, not a blanket claim of no progress or of C superiority. See the
[case comparison](case-comparison.md) and [machine-readable record](web-final-evaluation/comparison.json).

Candidate-to-delivery retention is **3/4 correct reference items** under this
reference. The lost item is the lessees' correctly attributed objection that auction
could not terminate their Patta. Supported assertions fall from 17 to 8, including
loss of the historically supported plaintiff-subrogation account. Unqualified
court/party and legal-power errors nevertheless remain in surviving text. No
successful correct rewrite is established by this removal operation.

## Independent user-requested side chat and reference sensitivity

The [separate Codex annotation](sidechat-independent/) wrote its own source-only
12-item reference before opening anonymous outputs, then graded all three. Its phase
log, reference freeze, raw labels, unresolved reference issue and separate scores
are preserved. It is **secondary Codex model evidence**, not Web annotation or a
second pass under the 17-item reference. In particular, its bundled statutory item
R11 remains unresolved. Different item granularity and assertion inventories produce
different scores; do not average them, choose the preferred C score, or calculate
kappa between unmatched inventories.

The [old posthoc twenty-item assessment](archive-v1/case1251841/scores.json) remains
byte-for-byte intact. It gave A0/C-candidate/C-delivered R values 55%/30%/15% and
candidate-to-delivery retention 3/6. Those figures have a different reference and
cannot be mixed with the present 17-item scores. This is reference-version
sensitivity, not improvement or deterioration of unchanged report bytes.

## Evidence boundary and reproduction

The [source-view audit](source-view-audit.json) confirms all 41 core CASE/LAW texts
occur in A0's original request and reconstruct exactly from witness passages in C's
final-generation request. This checks source identity, not semantic adequacy or total
configuration equivalence. Earlier C history/rule processing and continuation
resources remain additional components. No HISTORY source appears in the supplied
final reports, so this evaluation does not establish historical-RAG benefit.

This is a retrospective comparison of an unchanged older A0 output and a V38 C
continuation, not a newly run same-configuration batch. The allowed target reasons
and disposition remain hidden. The old V6 ten-case annotation aggregate has different
report hashes/contracts and is not reused for these texts. Its two missing cases
remain missing, as recorded in the [compatibility inventory](annotation-inventory.json).

Recalculate the primary adjudicated scores from the repository root, choosing a new
output filename:

```sh
python3 scripts/score_rapido_reports_v2.py \
  --sources outputs/rapido-evaluation-framework-2026-10-27-v2/example-1251841/allowed-materials.json \
  --reference outputs/rapido-evaluation-framework-2026-10-27-v2/web-reference-recovered/reference-final.json \
  --packet outputs/rapido-evaluation-framework-2026-10-27-v2/web-final-evaluation/blind-packet.json \
  --labels outputs/rapido-evaluation-framework-2026-10-27-v2/web-final-evaluation/labels-source-adjudicated.json \
  --output /tmp/rapido-eval-new-scores.json
```

The tool verifies exact identities, enum values and source/output quotations and
performs arithmetic. It does not decide legal truth or prove inventory completeness.
It refuses an existing output path. Seven tests cover arithmetic and provenance;
passing them is not method-quality evidence. Do not run archived scripts in place
or overwrite old score files.

V38's 35 frozen files and 43 external dependencies, plus all 26 archived files,
remain unchanged. Publication uses an isolated checkout based on the remote branch,
without staging the unrelated dirty source checkout. No Qwen/API experiment, A0
rerun, GPU job, training, method/default-entry change or budget expansion occurred.
New experimental API billing is zero. Web annotation tokens/billing are unavailable;
the explicitly requested Codex annotation chat is separately identified. UI captures,
conversation URLs and account details stay local rather than entering Git.
