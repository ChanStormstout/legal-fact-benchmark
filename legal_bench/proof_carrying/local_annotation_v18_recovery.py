"""Versioned reference contract. Reference-only admission never changes inference input."""
from .local_evaluation_v17 import LABELS

CONTRACT = {
 'version':'V18_USE_REFERENCE_2',
 'classes':list(LABELS),
 'SUPPORTED':'Source supports this exact evidentiary use, including valid opposition. Not whole-premise truth.',
 'UNSUPPORTED':'Demonstrable source, attribution, object, direction, court-stage or scope error in this use.',
 'UNRESOLVED':'Shared input insufficient, or genuinely unresolved source-grounded competing interpretations.',
 'dispute':'True only for grounded unresolved alternatives about the reference label after applying the use contract. Not disagreement with P, litigant disagreement, or opposition direction.',
 'mandatory_basis_refs':'Only source addresses essential to deciding this label. Must be in learner-visible same-case packet union for supervision.',
 'outside_packet_dependencies':'Only indispensable dependencies absent from that union. Supplementary outside references alone do not exclude supervision.',
 'refs':'All actual citations supporting the review; may include explicitly supplementary explanation. Quote must locate exactly in these refs.',
 'legacy':'No bulk flag changes. Reuse requires independently documented semantic compatibility; this version new P has changed prompts so old P-dependent labels are not reused.',
 'reference_status':'MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD',
}

ANNOTATION = '''Review exactly the proposed evidentiary uses in the supplied packet. Return complete English JSON in the response body, not only a download link. Do not search externally, consult other conversations, or rewrite the proposal. The target is the specific use of the cited passage for the specified proposition, object, direction and stage, not whole-premise truth or ultimate legal result. SUPPORTED means source-grounded use; legitimate opposition can be SUPPORTED. UNSUPPORTED means a demonstrable attribution, object, direction, court-stage, scope or citation error. UNRESOLVED means the shared materials cannot settle the use or competing source-grounded interpretations remain unresolved. A party assertion supports that the party made it, not automatically its truth. Background alone need not establish the whole proposition.
The reviewer does not see P's self-labels or whole-premise judgments. The learner does see fallible P judgments, raw records, rules, all typed relationships and the same-case union of all restored packets. A passage elsewhere in that union is visible, not outside input. Read the complete allowed source for decisive restrictions and counterarguments, but do not rescue a wrong use with a different passage.
DISPUTE CONTRACT: dispute:true ONLY means genuinely grounded, still unresolved alternative interpretations of the REFERENCE LABEL after source review. It does NOT mean you disagree with P, parties contested the underlying case, the evidence opposes the proposition, or you identified a clear error. A clear error may correctly be UNSUPPORTED with dispute:false. Explain any genuine dispute concretely in basis.
INPUT COVERAGE CONTRACT: mandatory_basis_refs lists ONLY sources indispensable to determining this label. refs lists actual review citations, including any separately explained supplementary material. outside_packet_dependencies lists ONLY indispensable unavailable dependencies; input_coverage_limited is true only when they are needed. Supplementary outside citations alone do not create an input-coverage obstacle. Do not pretend an indispensable dependency is supplementary. Preserve exact short quote and source addresses. No use is automatically accepted because its citation exists.
Output {"connections":[{"connection_id":"K001","label":"SUPPORTED","basis":"specific source-based explanation, and any genuine competing interpretation or supplementary citation","refs":["source ID"],"quote":"short exact words","mandatory_basis_refs":["essential source ID"],"dispute":false,"input_coverage_limited":false,"outside_packet_dependencies":[]}],"limitations":[]}. Exactly one row per declared use. No self-label confirmation and no missing rows. This is model-assisted source reference, not human gold. One response only.'''


def label_admissibility(label, visible, location):
    # This function only accepts an explicit reference contract; it does not infer a corrected label.
    required={'connection_id','label','basis','refs','quote','mandatory_basis_refs','dispute','input_coverage_limited','outside_packet_dependencies'}
    if not isinstance(label,dict) or set(label)!=required:
        return {'supervised':False,'reason':'REFERENCE_CONTRACT_AMBIGUOUS_OR_LEGACY'}
    if label['label'] not in LABELS or not label['basis'] or location.get('error'):
        return {'supervised':False,'reason':'SOURCE_OR_LABEL_UNCONFIRMED'}
    if any(type(label[k]) is not bool for k in ('dispute','input_coverage_limited')):
        return {'supervised':False,'reason':'REFERENCE_FLAGS_INVALID'}
    if any(not isinstance(label[k],list) for k in ('refs','mandatory_basis_refs','outside_packet_dependencies')):
        return {'supervised':False,'reason':'REFERENCE_DEPENDENCIES_INVALID'}
    essential=set(label['mandatory_basis_refs'])
    if not essential<=set(label['refs']) or (not essential and label['label']!='UNRESOLVED'):
        return {'supervised':False,'reason':'ESSENTIAL_BASIS_UNSPECIFIED'}
    if label['input_coverage_limited'] or label['outside_packet_dependencies'] or not essential<=set(visible):
        return {'supervised':False,'reason':'INDISPENSABLE_INPUT_COVERAGE_LIMITED'}
    if label['dispute']:
        return {'supervised':False,'reason':'GENUINE_REFERENCE_DISPUTE_RETAINED'}
    return {'supervised':True,'reason':'EXPLICIT_SOURCE_CONTRACT_COMPATIBLE'}
