"""Adjudicate the existing anonymous final reports; no experimental calls.

The permitted original record, frozen reference, raw Web judgments and report
bytes remain unchanged. Close reports use common actual assertion units.
"""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent
OLD = RAW.parent.parent
SRC = OLD / "atomic-reference-evaluation-v2/1914817"
packet = json.loads((SRC / "packet.json").read_text())
view = json.loads((SRC / "source-view.json").read_text())
texts = {r["blind_id"]: r["text"] for r in packet["reports"]}
decisions = []

def load(blind, axis):
    return json.loads((RAW / f"{blind}-{axis}-first-pass-raw.json").read_text())

def change(row, field, value, blind, why):
    before = row.get(field)
    if before != value:
        decisions.append(dict(blind_id=blind, id=row.get("item_id", row.get("id")), field=field, before=before, after=value, reason=why))
        row[field] = value

def write(name, obj):
    p = HERE / name
    if p.exists():
        raise ValueError("Preserve prior output: " + str(p))
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")

labels = {}
for blind in texts:
    a = load(blind, "assertions")
    a["coverage"] = load(blind, "coverage")["coverage"]
    a["annotation_status"] = "SOURCE_ADJUDICATED_MODEL_REFERENCE_NOT_HUMAN_GOLD"
    a["main_answer"] = "PARTIAL"
    labels[blind] = a

# Common full-report interpretation, not selection among Web judges' scores.
for blind in ["5IN", "1C3", "TF4"]:
    cov = {r["item_id"]: r for r in labels[blind]["coverage"]}
    change(cov["D09"], "status", "ANNOTATION_UNRESOLVED", blind,
           "All describe initial munafa deductions but not the distinct initial assertion of entitlement to the land's profits. Whether the deduction demand implicitly covers that separate entitlement relation is ambiguous; do not label identical close-report words CORRECT in one and NOT in another.")
    cov["D09"]["reason"] = "Initial munafa deductions are stated; whether this alone conveys the separately required initial profits-entitlement contention is ambiguous. The same interpretation is applied to all three reports."
for blind in ["5IN", "1C3"]:
    cov = {r["item_id"]: r for r in labels[blind]["coverage"]}
    change(cov["D49"], "status", "CORRECT", blind,
           "The identical second-batch set-off allowance and excess-defendant-dues dismissal express the netting operation in ordinary language. Do not require the literal word subtract while accepting equivalent net-calculation wording elsewhere.")
    cov["D49"]["reason"] = "The stated set-off against the plaintiffs' dues and dismissal when defendant dues exceed them together convey the accounting subtraction, even without reproducing the separate operative sentence."
    cov["D49"]["report_quotes"] = ["if the defendant’s dues exceeded the plaintiff’s, the suit for mesne profits would be dismissed"]
    # The identical title allegations are introduced by the first-batch
    # requested title relief and explicitly mirrored by the second batch.
    change(cov["D27"], "status", "ANNOTATION_UNRESOLVED", blind,
           "The second-batch allegations expressly mirror the first and the report names the second plaintiffs, but does not explicitly repeat their title prayer. Implicit incorporation is plausible, not an unqualified absence or a new source-added assertion.")
    cov["D27"]["reason"] = "Named second plaintiffs and mirrored first-batch allegations may incorporate the earlier stated title prayer, but the report does not explicitly identify that prayer for batch two; retain the same ambiguity in both texts."
    cov["D27"]["report_quotes"] = ["by Ganpat Singh and Narpat Singh", "The allegations mirrored those in the first batch"]

cov = {r["item_id"]: r for r in labels["TF4"]["coverage"]}
change(cov["D34"], "status", "ANNOTATION_UNRESOLVED", "TF4",
       "The correct batch, November and 1910 are reported; only day 23 is absent. The frozen criterion names the day but the month already locates the pre/post-possession divide. Flag this reference-granularity ambiguity instead of silently changing the criterion or counting the whole temporal relation absent.")
cov["D34"]["reason"] = "Correct second-batch month and year are stated. The day required literally by the criterion is omitted; its materiality to this question is uncertain, so reference-granularity uncertainty is retained."
cov = {r["item_id"]: r for r in labels["5M4"]["coverage"]}
change(cov["D59"], "status", "CORRECT", "5M4",
       "The report ends with the current higher appeal and proposed grounds still to be resolved, and supplies no final target winner. Apply the same source-boundary interpretation used for the other reports; inaccurate restrictions on the grounds are graded separately.")
cov["D59"]["report_quotes"] = ["The Supreme Court appeal thus centers on whether the High Court erred in law", "The new appellate grounds further challenge the valuation"]
cov["D59"]["reason"] = "It reconstructs the earlier results and identifies the further appellate issue and new grounds without inventing the target disposition. The incorrect only-if restriction on those grounds is a separate assertion error."

# Close-report units are anchored in the 1C3 original inventory. Four explicit
# repetitions are removed in BOTH reports before comparing them. The additional
# original 5IN inventory is retained untouched in the parent raw directory.
base = copy.deepcopy(labels["1C3"]["assertions"])
raw5 = {a["id"]: a for a in load("5IN", "assertions")["assertions"]}
dedup = {
    "A043": "The second-batch transfer repeats the all-appeals abolition/transfer event already stated in A005.",
    "A047": "Generic demand to offset post-delivery costs repeats the batch-specific asserted requests and the central claim already inventoried.",
    "A049": "Generic allowance in both batches repeats the actual first- and second-batch District Judge outcomes in A019 and A040.",
    "A061": "The supposed strategic broadening from entitlement to quantum repeats the valuation-versus-right distinction in A060; no distinct subjective intention is established.",
}
for blind in ["1C3", "5IN"]:
    rows = []
    for original in base:
        aid = original["id"]
        if aid in dedup:
            decisions.append(dict(blind_id=blind, id=aid, operation="SEMANTIC_DEDUPLICATION", reason=dedup[aid]))
            continue
        if blind == "5IN" and aid in {"A048", "A054", "A055", "A056", "A064"}:
            decisions.append(dict(blind_id=blind, id=aid, operation="NO_LONGER_ASSERTED", reason="A048/A054/A055/A056 were actually removed. A064's summary endpoint was corrected to 1927–28 and is now identical to supported A020, so no duplicate supported replacement is added."))
            continue
        a = copy.deepcopy(original)
        if aid == "A051":
            a.update(proposition="The District Judges in both batches excused the late pleas because the litigation was tortuous.",
                     report_quote='a fact the District Judges excused based on the "tortuous" nature of the litigation',
                     label="ANNOTATION_UNRESOLVED",
                     reason="This unchanged conclusion generalizes the recorded first-batch rationale to both batches. The quoted judge says 'all these cases', but the second-batch extract does not independently attribute that rationale; preserve common scope uncertainty rather than opposite labels.")
        if blind == "5IN" and aid == "A050":
            a.update(proposition="The first-batch District Judge treated the set-off as a cross-demand.",
                     report_quote="treating the claim as a cross-demand",
                     reason="The edited report retains the cross-demand description, but no longer states the specific same-transaction nexus. Its narrower actual assertion is supported; the lost relation is counted on D19, not invented back into the report.")
        if blind == "5IN" and aid == "A065":
            a = copy.deepcopy(raw5["A068"])
            a["id"] = "A065"
        rows.append(a)
    if blind == "5IN":
        for rawid, newid in [("A057", "N072"), ("A060", "N073")]:
            a = copy.deepcopy(raw5[rawid]); a["id"] = newid; a["source_annotation_id"] = rawid; rows.append(a)
    labels[blind]["assertions"] = rows

# Severity differs from whether a proposition is wrong. An identical wrong
# same-parties opening cannot be CONFIRMED serious only in the edited report.
# Both later correctly name separate plaintiffs; downstream materiality remains
# ambiguous under the frozen serious-error standard.
for blind in ["5IN", "1C3"]:
    e = labels[blind]["serious_errors"][0]
    change(e, "severity_status", "UNRESOLVED", blind,
           "Same false same-party opening, same later correct party names, same unresolved material effect; retain identical severity. The assertion itself remains CONTRADICTED in both.")
    e["materiality"] = "The same-party opening is wrong and could distort cross-batch mutuality, but each report later names the distinct plaintiffs correctly. Whether this actually changes the legal assessment remains unresolved; apply the same severity in both."

# Complete the same serious-candidate inventory for unchanged passages.
shared_charge = copy.deepcopy(load("5IN", "assertions")["serious_errors"][3])
shared_charge["id"] = "PARENT_SHARED_CHARGE_TYPE"
labels["1C3"]["serious_errors"].append(shared_charge)
shared_reason = copy.deepcopy(load("5IN", "assertions")["serious_errors"][1])
shared_reason["id"] = "PARENT_SHARED_CROSS_BATCH_REASON"
shared_reason["report_quotes"] = ['a fact the District Judges excused based on the "tortuous" nature of the litigation']
labels["1C3"]["serious_errors"].append(shared_reason)

# Preserve the fair retrospective reading of pending appellate resolution in
# all reports, not an imagined claim that this old case is pending today.
tf = labels["TF4"]
a = next(a for a in tf["assertions"] if a["id"] == "A045")
change(a, "label", "SUPPORTED", "TF4",
       "The report expressly reconstructs the supplied procedural record. Pending refers to the endpoint before the withheld merits, not the contemporary docket. Apply whole-context reading as for the other reports.")
a["reason"] = "Within the stated retrospective reconstruction, the endpoint supplied is further appellate review with final reasoning/disposition withheld. No current-day pending status or final winner is asserted."
tf["serious_errors"] = []
decisions.append(dict(blind_id="TF4", id="E001", operation="SERIOUS_CANDIDATE_RESOLVED_NO_ERROR", reason="The fair retrospective reading resolves this ambiguity; original Web serious candidate remains in the unmodified raw file."))

literal = []
for blind, r in labels.items():
    assert r["report_sha256"] == hashlib.sha256(texts[blind].encode()).hexdigest()
    assert len(r["coverage"]) == 59
    for axis in ["coverage", "assertions", "serious_errors"]:
        for x in r[axis]:
            quotes = x.get("report_quotes", []) if axis != "assertions" else [x["report_quote"]]
            for q in quotes:
                if not q or q not in texts[blind]:
                    literal.append(dict(blind_id=blind, axis=axis, id=x.get("item_id",x.get("id")), type="REPORT_WITNESS_REQUIRES_REVIEW", quote=q))
            for fld in ["evidence", "source_evidence"]:
                for e in x.get(fld, []):
                    if e["source_id"] == "SCOPE":
                        e["source_id"] = "scope"
                    sid, q = e["source_id"], e["quote"]
                    original = view["scope"] if sid == "scope" else view["sources"][sid]["text"]
                    if q not in original:
                        at = original.casefold().find(q.casefold())
                        if at >= 0:
                            e["quote"] = original[at:at+len(q)]
                            literal.append(dict(blind_id=blind, id=x.get("item_id",x.get("id")), source_id=sid, before=q, after=e["quote"], type="CASE_ONLY_ORIGINAL_SUBSTRING"))
                        else:
                            literal.append(dict(blind_id=blind, axis=axis, id=x.get("item_id",x.get("id")), source_id=sid, quote=q, type="SOURCE_WITNESS_REQUIRES_REVIEW"))

write("labels-source-adjudicated-shared-units.json", {k:packet[k] for k in ["case_id","source_view_sha256","reference_sha256"]} | {"reports":list(labels.values())})
write("source-adjudication-log.json", dict(at=datetime.now(timezone.utc).isoformat(), decisions=decisions,
    reading="All 43 allowed CASE excerpts, all 59 source-only frozen reference criteria, all four final reports and eight raw annotation files. The 23 allowed LAW excerpts are byte-identical to the previously read 1230342 set and contain no independently supplied general equitable-set-off rule.",
    method_map_opened=False, parent_perfect_blinding_claimed=False,
    provisional_reference="Single model source-only proposal with parent source vetting, no independent design audit.",
    model_reference_not_human_gold=True, intervals_not_statistical_CI=True))
write("literal-witness-review.json", literal)
write("pre-unmask-available-axes-freeze.json", dict(at=datetime.now(timezone.utc).isoformat(), method_map_opened=False,
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob("*.json")}, all_four_axes_received=True))
print(json.dumps(dict(assertion_counts={k:len(v["assertions"]) for k,v in labels.items()}, literal_review=literal),ensure_ascii=False,indent=2))
