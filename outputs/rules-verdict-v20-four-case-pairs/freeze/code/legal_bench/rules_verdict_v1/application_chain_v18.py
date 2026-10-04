"""Audited source-preserving application instructions; no legal rule executor."""
import json

from .source_views import digest
from .rule_application_v17 import material_parts, source_map

APPLICATION_REQUIREMENTS = '''
APPLICATION ANALYSIS REQUIREMENTS (generic; no additional case facts or law)
Use the existing outcome/grounds/reason contract and examples. Do not add an extraction stage. The following governs how explanations connect the supplied evidence to law; it does not change any legal rule.
For each decisive issue, explain the chain: proposition -> relevant target evidence and its status -> supplied rule's premise and legal scope -> why the evidence does or does not meet that premise -> strongest relevant opposing argument -> the remaining gap and its consequence. A list of facts followed by case names is not an application. Use up to six grounds if needed, merging discussion of the same issue rather than dropping decisive opposition to meet a soft word target.
Distinguish narration, party allegation, opposing parties' agreement, and a court's finding at its actual level and stage. Lack of a current target-court finding does not by itself erase a reported fact or a visible prior-court finding. Do not silently treat narration or agreement as a final adjudication. Preserve a prior decision when it changes the status of relevant evidence; a bare prior outcome cannot establish an unstated condition.
For each authority actually relied on, distinguish its statutory setting, adopted interpretation, case-specific application, reported precedent, or provisional/reserved view. Explain the supported bridge, limitation or distinction before applying another statute or legal setting. Mere similarity, judicial approval, or a compliance purpose is not by itself an exception: an exception needs supplied legal support. Facts concerning an authority's own parties never become target facts.
Use all supplied shared legal-source blocks, including labeled additional original authorities where present. Candidate cards remain fallible. Cite original CASE/LAW addresses rather than the cards, these instructions, or fictional examples. Do not infer a rule from whichever outcome is desired.
When information is unresolved, identify exactly which premise cannot be determined and why. Distinguish a missing fact, an unresolved interpretation, and limits of the supplied source/version. Preserve conditions already supported. Missing withheld target reasons is not automatically a reason to avoid applying the other supplied law.
If the overall outcome remains UNDETERMINED, state the supported conditional consequence of the unresolved premise where the supplied law permits it, and state what additional determination would change the analysis. Do not invent that determination or force a definite verdict. The reason must follow from the assessed propositions; assessment evaluates its point, not the direction of eviction. Short output is a writing objective, not permission to remove a necessary premise or objection.
Return one complete JSON object under the unchanged schema, followed by END. Do not browse, use other conversations, add legal materials, or seek follow-up clarification.
'''


def refine_prompt(original):
    """A single additive generic instruction block; all old bytes recover."""
    if APPLICATION_REQUIREMENTS in original:
        raise ValueError('Already refined: no duplicate instruction insertion')
    if original.count('FINAL TASK REMINDER\n') != 1:
        raise ValueError('Ambiguous final-task boundary')
    before, intermediate, tail = material_parts(original)
    if intermediate != {}:
        raise ValueError('Direct-source baseline must have empty intermediate material')
    refined = original + APPLICATION_REQUIREMENTS
    if refined[:-len(APPLICATION_REQUIREMENTS)] != original:
        raise AssertionError('Original prompt changed')
    return refined


def audit_view(view, full_source):
    """Verify text lineage, not semantic support or PDF completeness."""
    original = source_map(full_source['segments'])
    current = source_map(view['segments'])
    if view['case_id'] != full_source['case_id'] or view['source_hash'] != digest(full_source):
        raise ValueError('Wrong or changed parent source')
    if view['input_view_hash'] != digest(view['segments']):
        raise ValueError('View hash differs')
    selected = []
    for s in current.values():
        parent = original[s['source_segment_id']]
        start, end = s['start'], s['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(parent['text']):
            raise ValueError('Invalid slice offsets')
        expected = parent['text'][start:end]
        expected_id = parent['id'] if start == 0 and end == len(parent['text']) else '%s@%d:%d' % (parent['id'], start, end)
        if s['text'] != expected or s['id'] != expected_id:
            raise ValueError('Slice content or ID changed')
        selected.append({'id': s['id'], 'parent_id': parent['id'], 'start': start, 'end': end,
                         'text_sha256': digest(expected.encode('utf-8')),
                         'partial_parent': start != 0 or end != len(parent['text'])})
    seen = {s['source_segment_id'] for s in view['segments']}
    excluded = [s['id'] for s in full_source['segments'] if s['id'] not in seen]
    if excluded != view['excluded_segment_ids']:
        raise ValueError('Exclusion list differs')
    if set(current) & set(excluded):
        raise ValueError('Excluded segment in view')
    return {'mechanical_status': 'PASS', 'case_id': view['case_id'], 'selected_slices': selected,
            'parent_source_metadata': {k: v for k, v in full_source.items() if k != 'segments'},
            'excluded_parent_ids': excluded, 'excluded_tail_of_partial_parent_is_not_separate_id': True,
            'PDF_visual_or_terminal_completeness_certified': False, 'semantic_correctness_certified': False}


def audit_prompt(original, schema, case_source, law_package, additional_authorities):
    """Check actual embedded values, cited namespaces and an empty intermediate."""
    case_ids = list(source_map(case_source['segments']))
    laws = source_map(law_package['law_segments'] + [s for a in additional_authorities for s in a['segments']])
    marker = 'TARGET SHARED LAW PACKAGE\n'
    if original.count(marker) != 1:
        raise ValueError('Ambiguous law block')
    embedded, _ = json.JSONDecoder().raw_decode(original.split(marker, 1)[1])
    if embedded != law_package:
        raise ValueError('Embedded law values differ')
    header = 'ADDITIONAL SHARED ORIGINAL AUTHORITIES (other-case sources, not target facts)\n'
    if additional_authorities:
        if original.count(header) != 1:
            raise ValueError('Missing/ambiguous additional authorities')
        embedded, _ = json.JSONDecoder().raw_decode(original.split(header, 1)[1])
        if embedded != additional_authorities:
            raise ValueError('Embedded additional authority values differ')
    elif header in original:
        raise ValueError('Unexpected extra authorities')
    _, intermediate, tail = material_parts(original)
    if intermediate != {}:
        raise ValueError('Prior intermediate leaked into direct task')
    source_render = '\n'.join('['+s['id']+'] '+s['text'] for s in case_source['segments'])
    if tail != '\nTARGET COMPLETE ALLOWED CASE SOURCE\n'+source_render+'\nFINAL TASK REMINDER\n'+tail.split('\nFINAL TASK REMINDER\n', 1)[1]:
        raise ValueError('Rendered case source differs')
    ground = schema['properties']['grounds']['items']['properties']
    if ground['case_refs']['items']['enum'] != case_ids or ground['law_refs']['items']['enum'] != list(laws):
        raise ValueError('Source-address contract differs from supplied material')
    target = case_source['case_id']
    if any(c['source_case'] == target for c in law_package['cards']):
        raise ValueError('Own target RuleCard leakage')
    if any(s.get('source_case') == target for s in law_package['law_segments']):
        raise ValueError('Own target law passage leakage')
    refined = refine_prompt(original)
    return {'status': 'PASS', 'original_prompt_recoverable': refined[:-len(APPLICATION_REQUIREMENTS)] == original,
            'case_addresses': len(case_ids), 'law_addresses': len(laws),
            'common_cards_retained': len(law_package['cards']), 'additional_cards': 0,
            'empty_intermediate': True, 'same_schema_and_source_scope': True,
            'no_reference_or_diagnostic_material_inserted': True,
            'program_executes_legal_rules': False, 'semantic_correctness_certified': False}
