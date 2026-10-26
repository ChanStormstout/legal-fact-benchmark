"""One contract for extraction, decoding and structural consumption.

This module constrains representability, not the legal truth of model statements.
"""
import copy
import contracts as C

MODALITIES = {
    'PARTY_ASSERTION': ['AFFIRMED', 'UNRESOLVED'],
    'PARTY_DENIAL': ['DENIED'],
    'PRIOR_COURT_FINDING': ['AFFIRMED', 'DENIED', 'UNRESOLVED'],
    'NARRATED_EVENT': ['AFFIRMED', 'DENIED', 'UNRESOLVED'],
    'NARRATOR_ANALYSIS': ['AFFIRMED', 'DENIED', 'OPEN', 'UNRESOLVED'],
    'QUOTED_DOCUMENT': ['AFFIRMED', 'DENIED', 'UNRESOLVED'],
    'OPEN_QUESTION': ['OPEN'],
    'UNRESOLVED': ['UNRESOLVED'],
}
DATE_CARDINALITIES = {'RECORDED': (1, 6), 'CONFLICTED': (2, 6),
                      'NOT_STATED': (0, 0), 'UNRESOLVED': (0, 6)}


def alternatives(base, modality_speakers, time_schema):
    """Complete object alternatives work with the existing hosted decoder.

    Unrelated fields remain byte-for-byte equivalent across branches. Cardinality
    and qualification cannot drift between generator and consumer definitions.
    """
    fields = copy.deepcopy(base)
    branches = []
    for mode, polarities in MODALITIES.items():
        branches.append(C.obj({'mode': C.enum([mode]), 'polarity': C.enum(polarities),
                               'speaker': modality_speakers[mode]}))
    fields['qualification'] = {'anyOf': branches}
    fields['dating'] = {'anyOf': [C.obj({'date_status': C.enum([status]),
                                      'times': C.arr(time_schema, hi, lo)})
                                    for status, (lo, hi) in DATE_CARDINALITIES.items()]}
    return C.obj(fields)


def unpack_record(value):
    result = copy.deepcopy(value)
    for field in ('qualification', 'dating'):
        if field in result:
            for key, val in result.pop(field).items():
                if key in result:
                    raise ValueError('CONTRACT_FIELD_COLLISION:' + key)
                result[key] = val
    return result


def pack_record(value):
    result = copy.deepcopy(value)
    result.pop('anchor_source_id', None)
    result['qualification'] = {key: result.pop(key) for key in ('mode', 'polarity', 'speaker')}
    result['dating'] = {key: result.pop(key) for key in ('date_status', 'times')}
    return result


def passage_contract(record_schema):
    return {'anyOf': [
        C.obj({'records': C.arr(record_schema, 8, 1),
               'disposition': C.enum(['REPRESENTED']),
               'limitations': C.arr(C.text(200), 4)}),
        C.obj({'records': C.arr(record_schema, 0),
               'disposition': C.enum(['NO_MATERIAL_STATEMENT', 'INSUFFICIENT_CONTEXT']),
               'limitations': C.arr(C.text(200), 4)})]}
