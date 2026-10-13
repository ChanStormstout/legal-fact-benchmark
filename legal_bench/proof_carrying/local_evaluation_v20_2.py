"""Strict prediction accounting and source-score interface; no legal judgement."""
import math
from numbers import Real
from .local_evaluation_v17 import (LABELS, CLAIM_RULE, blind_order,
                                  equal_dispute_summary, semantic_metrics as legacy_semantic,
                                  local_metrics as legacy_local)


def local_metrics(predictions, rows):
    expected = {r['key']: r for r in rows}
    if len(expected) != len(rows):
        raise ValueError('DUPLICATE_REFERENCE_KEY')
    if any(r['label'] not in LABELS for r in rows):
        raise ValueError('OLD_LABEL_NOT_CONVERTED')
    seen, valid, missing_reason = set(), [], {}
    for prediction in predictions:
        key = prediction['key']
        if key in seen:
            raise ValueError('DUPLICATE_PREDICTION_KEY:' + key)
        if key not in expected:
            raise ValueError('UNEXPECTED_PREDICTION_KEY:' + key)
        seen.add(key)
        probabilities = prediction.get('probabilities')
        label = prediction.get('label')
        if probabilities is not None:
            if (len(probabilities) != 3 or any(not isinstance(v, Real) or not math.isfinite(v) or not 0 <= v <= 1 for v in probabilities)
                    or not math.isclose(sum(probabilities), 1.0, rel_tol=0, abs_tol=1e-5)):
                raise ValueError('INVALID_PROBABILITIES:' + key)
        if label is None and probabilities is None:
            missing_reason[key] = 'NO_SEMANTIC_PREDICTION'
            continue
        if label is not None and label not in LABELS:
            raise ValueError('INVALID_PREDICTION_LABEL:' + key)
        if label is not None and probabilities is not None and label!=LABELS[max(range(3),key=lambda i:probabilities[i])]:
            raise ValueError('LABEL_PROBABILITY_MISMATCH:' + key)
        valid.append(prediction)
    for key in expected.keys() - seen:
        missing_reason[key] = 'PREDICTION_NOT_PRESENT'
    result = legacy_local(valid, rows)
    complete = bool(rows) and not missing_reason
    if not complete:
        observed = {k: result[k] for k in ('per_class','macro_f1_observed_classes','macro_f1_all_three',
                    'error_allow_rate','error_block_rate','hierarchical_nll')}
        result['completed_subset_diagnostics'] = observed
        for key in ('macro_f1_observed_classes','macro_f1_all_three','error_allow_rate','error_block_rate','hierarchical_nll'):
            result[key] = None
    result.update(status='COMPLETE' if complete else 'NO_EVALUABLE_ROWS' if not rows else 'INCOMPLETE_PREDICTIONS',
                  planned_connections=len(rows), missing_predictions=sorted(missing_reason),
                  missing_prediction_reasons=missing_reason, comparison_eligible=complete)
    result['unmapped_P_predictions'] = sorted(missing_reason)
    return result


def semantic_metrics(review, reference, expected_ids=None, actuals=None):
    ids = [a['answer_id'] for a in review['answers']]
    if len(ids) != len(set(ids)):
        raise ValueError('DUPLICATE_REVIEW_ANSWER')
    if expected_ids is not None and set(ids) != set(expected_ids):
        raise ValueError('MISSING_OR_EXTRA_PREPLANNED_REVIEW_ANSWERS')
    for answer in review['answers']:
        aid = answer['answer_id']
        if actuals is not None:
            if aid not in actuals or answer['technical_status'] != actuals[aid]['technical_status']:
                raise ValueError('REVIEW_TECHNICAL_STATE_MISMATCH:' + aid)
            if actuals[aid]['technical_status'] != 'OK' and actuals[aid].get('answer') is not None:
                raise ValueError('LOCAL_FAILURE_MUST_BE_NULL')
        if answer['technical_status'] == 'OK':
            allowed = {'CORRECTLY_HANDLED','OMITTED','INCORRECT'}
            if any(row['status'] not in allowed for row in answer['key_items']):
                raise ValueError('INVALID_CHECKLIST_SCORING_STATUS')
    return legacy_semantic(review, reference, expected_ids)

