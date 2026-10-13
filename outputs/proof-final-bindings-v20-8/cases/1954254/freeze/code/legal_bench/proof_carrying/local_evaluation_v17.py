"""Frozen V17 evaluation contract. References never participate in inference.

Semantic judgements are supplied by the offline, source-grounded reviewer. This
module checks the review interface and computes denominators; it does not judge
legal meaning by lexical agreement.
"""
import hashlib
import json
import random
from collections import Counter

LABELS = ('SUPPORTED', 'UNSUPPORTED', 'UNRESOLVED')
OVERALL = ('COMPLETE_AND_SOURCED', 'PARTIAL', 'MAJOR_ERROR', 'DISPUTED_OR_UNEVALUABLE')
CLAIM_RULE = (
    'A substantive judgement is one independently assessable proposition about '
    'a fact/object/event/status/stage, a rule/scope/exception, an application, '
    'or a conclusion. Split only when clauses can have different truth or support '
    'values. Merge repetitions and paraphrases of the same proposition, across '
    'fields. Do not count citations, headings, stylistic remarks, or every word '
    'as claims. An explicitly qualified uncertainty or assumption is assessed '
    'in its stated scope. Distinguish an asserted fact from an attributed claim. '
    'Alternative accounts of the same issue remain different claims when their '
    'speakers, objects, stage, or asserted content differ.'
)


def hash_value(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def blind_order(case_id, conditions, seed=20261001):
    """Stable across interpreters; no Python hash() dependence."""
    order = sorted(conditions)
    offset = int(hashlib.sha256(str(case_id).encode()).hexdigest()[:8], 16)
    random.Random(seed + offset).shuffle(order)
    return {f'ANSWER_{i+1:02d}': name for i, name in enumerate(order)}


def semantic_metrics(review, reference, expected_ids=None):
    keys = {x['id'] for x in reference['key_items']}
    if not keys:
        raise ValueError('EMPTY_REFERENCE_CHECKLIST')
    seen, results = set(), {}
    for answer in review['answers']:
        aid = answer['answer_id']
        if aid in seen:
            raise ValueError('DUPLICATE_REVIEW_ANSWER')
        seen.add(aid)
        if answer['technical_status'] != 'OK':
            if answer.get('answer') is not None:
                raise ValueError('TECHNICAL_FAILURE_MUST_BE_NULL')
            results[aid] = {'technical_status': answer['technical_status'],
                            'key_coverage': None, 'unsupported_rate': None,
                            'major_error_case': None, 'overall': None}
            continue
        coverage = answer['key_items']
        if len(coverage) != len(keys) or {x['id'] for x in coverage} != keys:
            raise ValueError('INCOMPLETE_OR_DUPLICATE_CHECKLIST_SCORING')
        correct = sum(x['status'] == 'CORRECTLY_HANDLED' for x in coverage)
        claims = answer['substantive_judgements']
        claim_ids = [x['id'] for x in claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise ValueError('DUPLICATE_CLAIM_IDS')
        valid = {'SUPPORTED', 'CONFIRMED_ERROR_OR_UNSUPPORTED', 'DISPUTED', 'UNEVALUABLE'}
        if any(x['status'] not in valid for x in claims):
            raise ValueError('INVALID_CLAIM_REVIEW_STATUS')
        evaluated = [x for x in claims if x['status'] in valid - {'DISPUTED', 'UNEVALUABLE'}]
        bad = [x for x in evaluated if x['status'] == 'CONFIRMED_ERROR_OR_UNSUPPORTED']
        major = any(x.get('major', False) for x in bad)
        if answer['overall'] not in OVERALL:
            raise ValueError('INVALID_OVERALL_REVIEW')
        if major and answer['overall'] != 'MAJOR_ERROR':
            raise ValueError('MAJOR_ERROR_NOT_REFLECTED_IN_OVERALL')
        # The numerator is confirmed errors, not disagreements with a reference.
        results[aid] = {'technical_status': 'OK', 'correct_key_items': correct,
                        'total_key_items': len(keys), 'key_coverage': correct/len(keys),
                        'confirmed_bad_claims': len(bad), 'evaluable_claims': len(evaluated),
                        'unsupported_rate': len(bad)/len(evaluated) if evaluated else None,
                        'disputed_claims': sum(x['status'] == 'DISPUTED' for x in claims),
                        'unevaluable_claims': sum(x['status'] == 'UNEVALUABLE' for x in claims),
                        'major_error_case': major if evaluated else None,
                        'overall': answer['overall']}
    if expected_ids is not None and seen != set(expected_ids):
        raise ValueError('MISSING_PREPLANNED_REVIEW_ANSWERS')
    return results


def equal_dispute_summary(rows, planned_count):
    """Request means within disputes, then equal dispute weighting.

    Technical failures remain in completion, and have no fabricated semantic
    score. No weighted composite or winner selection is performed here.
    """
    groups = {}
    for row in rows:
        groups.setdefault(row['dispute_id'], []).append(row)
    result = {'planned_tasks': planned_count, 'completed_tasks': sum(r['technical_status'] == 'OK' for r in rows),
              'completion_rate': sum(r['technical_status'] == 'OK' for r in rows)/planned_count if planned_count else None,
              'recorded_tasks': len(rows), 'disputes': len(groups)}
    for key in ('key_coverage', 'unsupported_rate'):
        dispute_means = []
        for group in groups.values():
            available = [r[key] for r in group if r.get(key) is not None]
            if available:
                dispute_means.append(sum(available)/len(available))
        result[key] = sum(dispute_means)/len(dispute_means) if dispute_means else None
        result[key + '_evaluable_disputes'] = len(dispute_means)
    eligible = [g for g in groups.values() if any(r.get('major_error_case') is not None for r in g)]
    result['major_error_dispute_proportion'] = sum(any(r.get('major_error_case') is True for r in g) for g in eligible)/len(eligible) if eligible else None
    result['major_error_evaluable_disputes'] = len(eligible)
    return result


def local_metrics(predictions, rows):
    import math
    ix = {r['key']: r for r in rows}
    matrix = [[0]*3 for _ in LABELS]
    losses, missing = {}, []
    for p in predictions:
        r = ix[p['key']]
        if r['label'] not in LABELS:
            raise ValueError('OLD_LABEL_NOT_CONVERTED')
        probabilities = p.get('probabilities')
        guess = p.get('label')
        if guess is None and probabilities is not None:
            guess = LABELS[max(range(3), key=lambda i: probabilities[i])]
        if guess not in LABELS:
            missing.append(r['key']); continue
        g, y = LABELS.index(r['label']), LABELS.index(guess)
        matrix[g][y] += 1
        if probabilities is not None:
            losses.setdefault(r['dispute_id'], {}).setdefault(r['request_id'], []).append(-math.log(max(probabilities[g], 1e-12)))
    per_class = {}
    for i, label in enumerate(LABELS):
        tp = matrix[i][i]; actual = sum(matrix[i]); predicted = sum(row[i] for row in matrix)
        precision = tp/predicted if predicted else 0.0
        recall = tp/actual if actual else None
        f1 = 2*precision*recall/(precision+recall) if recall is not None and precision+recall else 0.0 if actual else None
        per_class[label] = {'precision': precision, 'recall': recall, 'f1': f1, 'actual': actual, 'predicted': predicted}
    supported, unsupported = sum(matrix[0]), sum(matrix[1])
    f1s = [x['f1'] for x in per_class.values() if x['f1'] is not None]
    hierarchical = [sum(sum(v)/len(v) for v in requests.values())/len(requests) for requests in losses.values()]
    return {'labels': LABELS, 'confusion_gold_rows_prediction_columns': matrix, 'per_class': per_class,
            'macro_f1_observed_classes': sum(f1s)/len(f1s) if f1s else None,
            'macro_f1_all_three': sum(x['f1'] or 0.0 for x in per_class.values())/3,
            'error_allow_rate': matrix[1][0]/unsupported if unsupported else None,
            'error_block_rate': matrix[0][1]/supported if supported else None,
            'unresolved_predictions_by_gold': {label: matrix[i][2] for i, label in enumerate(LABELS)},
            'unmapped_P_predictions': missing, 'hierarchical_nll': sum(hierarchical)/len(hierarchical) if hierarchical else None,
            'disputes': len({r['dispute_id'] for r in rows}), 'scored_connections': sum(map(sum, matrix))}
