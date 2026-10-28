"""Candidate F: unchanged P prefix, then one source-plan-guided direct edit.

No reference annotations, saved A0, semantic ACCEPT, or second critic message.
The P prefix is a physically shared method endpoint, not an enhanced baseline.
This draft module never dispatches inference on import.
"""
from common import digest, read, save, write
from local_edits import apply_local
from pipeline import execute
import shutil


DIRECT_EDIT = """Read the complete originals, the fallible source-addressed plan,
and the draft. Produce one set of local edits directly from those originals.
No earlier critic interpretation is supplied as evidence or as an instruction.

First revisit the plan's question-material events, attributed positions, legal
conditions and objections against the full originals, including material the
draft never mentions. Then inspect the draft's actual claims. The plan may be
wrong or incomplete. A historical finding can be supported while its current
legal effect is open. Keep actual party arguments apart from your own conditional
analysis and identify what a counterargument attacks. Distinguish the remedy
controlled by a condition from other remedies whose conditions differ.

Use the original context on both sides of a fragment. Preserve uncertainty in
source reading: an OCR interpretation, guessed date, unresolved document mapping
or hypothesized legal connection is not an observed fact. Do not promote one into
a precise factual correction. When only a coarser event/date relation is supported,
retain that supported statement and explain the specific remaining ambiguity.
Check a changed relation against other supplied events and conditions, rather
than assuming that agreement with one fragment resolves the whole issue.
Do not repair an unsupported conclusion merely by saying a party argued it or
a court reasoned it: that attribution needs its own support in the originals.
Otherwise present a warranted connection as your conditional analysis, with its
actual conditions and limits. A hidden final holding does not prevent analysis
of supplied conditions, but it cannot be filled in from memory or a named case
whose holding has not been supplied. Do not guess the legal cause of a reported
remedy simply because that remedy followed a finding.

Return {"plan_use":[{"item_id":"existing W id","draft_quotes":["actual
draft substrings, or empty"],"remaining_gap":"brief specific gap, if any"}],
"edits":[{"id":"E1","op":"REPLACE|INSERT_AFTER","old":"exact UNIQUE
draft substring","new":"local replacement or insertion, with source IDs",
"source_ids":["actual IDs"],"basis":"DIRECT|REASONED|AMBIGUOUS",
"evidence":[{"source_id":"actual ID","quote":"exact original substring"}],
"counterevidence":[{"source_id":"actual ID","quote":"exact substring"}],
"reason":"what changes and why the resulting statement is supported"}],
"unresolved":["concrete remaining source or legal issue"]}.

Every edit must change actual text. Preserve supported material outside and
within a mixed sentence; do not erase a paragraph for one relation error.
INSERT_AFTER keeps its anchor and adds genuinely missing source-supported
content. Use the unchanged draft for all anchors and avoid overlapping edits.
Return only material changes, normally at most eight; do not fill unused slots
with statements that were already correct. Zero edits is allowed and proves
nothing about quality. Keep explanations brief. An exact quote is an address
witness, not proof that your interpretation or legal inference is correct.
No general grade, ACCEPT, reference answer, hidden outcome or entire-report rewrite.
"""


def evidence_diagnostics(proposal, sources):
    """Address diagnostics only; never infer an acceptance or delete a report."""
    rows = []
    edits = proposal.get("edits", [])
    if not isinstance(edits, list):
        return [{"code": "BAD_EDIT_COLLECTION"}]
    for edit in edits:
        if not isinstance(edit, dict):
            rows.append({"code": "NON_OBJECT_EDIT"})
            continue
        for field in ("evidence", "counterevidence"):
            witnesses = edit.get(field, [])
            if not isinstance(witnesses, list):
                rows.append({"edit": edit.get("id"), "code": "BAD_WITNESS_COLLECTION", "field": field})
                continue
            for witness in witnesses:
                if not isinstance(witness, dict):
                    rows.append({"edit": edit.get("id"), "code": "BAD_WITNESS"})
                    continue
                sid, quote = witness.get("source_id"), witness.get("quote")
                if sid not in sources:
                    rows.append({"edit": edit.get("id"), "code": "UNKNOWN_SOURCE", "source_id": sid})
                elif not isinstance(quote, str) or not quote or quote not in sources[sid]["text"]:
                    rows.append({"edit": edit.get("id"), "code": "QUOTE_NOT_EXACT", "source_id": sid})
    return rows


def execute_f(client, dossier, dest, caps, inherited_prefix=None):
    """Execute three calls at most; the caller owns the frozen global budget."""
    dest.mkdir(parents=True, exist_ok=False)
    save(dest / "input.json", dossier)
    prefix_dir = dest / "P-prefix"
    if inherited_prefix is None:
        prefix = execute(client, dossier, "P", prefix_dir, caps)
    else:
        # Actual prior model work, including failures, is inherited unchanged.
        # The runner verifies and charges its frozen receipts separately.
        inherited_prefix = inherited_prefix.resolve()
        assert read(inherited_prefix / "input.json") == dossier
        shutil.copytree(inherited_prefix, prefix_dir)
        prefix = read(prefix_dir / "outcome.json")
        save(dest / "prefix-provenance.json", {
            "directory": str(inherited_prefix), "reissued_calls": 0,
            "model_outputs_not_semantically_replaced": True,
            "resources_included_in_method_accounting": True})
    if not prefix.get("final_report_available"):
        result = {"case_id": dossier["case_id"], "method": "F",
                  "final_report_available": False, "status": "NO_USABLE_PREFIX_REPORT",
                  "prefix_outcome": prefix, "full_chain_completed": False, "quality": None}
        save(dest / "outcome.json", result)
        return result

    draft = (prefix_dir / "final-report.txt").read_text()
    write(dest / "candidate-report.txt", draft)
    material = {"originals": dossier, "source_plan": read(prefix_dir / "resolved-plan.json"),
                "draft": draft, "draft_sha256": digest(draft),
                "plan_failed": any(x.get("stage") == "plan" for x in prefix.get("failures", []))}
    from prompts import TRUST
    save(dest / "direct-edit-input.json", {"system": TRUST + "\n" + DIRECT_EDIT,
                                          "material": material, "cap": caps["direct_edit"]})
    final, failure = draft, None
    audit = {"applied": 0, "semantic_endorsement": False}
    try:
        proposal = client.call(dossier["case_id"] + "-F-direct-edit",
                               TRUST + "\n" + DIRECT_EDIT, material, caps["direct_edit"])
        save(dest / "direct-edit-raw.json", proposal)
        save(dest / "evidence-diagnostics.json", evidence_diagnostics(proposal, dossier["sources"]))
        final, audit = apply_local(draft, proposal, dossier["sources"])
    except Exception as exc:
        failure = {"stage": "direct_edit", "status": "FAILED",
                   "error": type(exc).__name__ + ":" + str(exc), "draft_retained": True}
        audit.update(revision_failed_draft_retained=True)
    save(dest / "edit-audit.json", audit)
    write(dest / "final-report.txt", final)
    result = {"case_id": dossier["case_id"], "method": "F", "final_report_available": True,
              "candidate_available": True, "full_chain_completed": prefix["full_chain_completed"] and failure is None,
              "prefix_outcome": prefix, "edit_failure": failure, "report_changed": final != draft,
              "applied_edits": audit.get("applied", 0), "semantic_gate": False,
              "semantic_correctness": None, "all_semantics_Qwen_proposed": True,
              "A0_used_as_method_input": False, "evaluation_reference_used_as_input": False,
              "P_prefix_is_shared_endpoint": True, "quality": None}
    result["inherited_prefix"] = inherited_prefix is not None
    save(dest / "outcome.json", result)
    return result
