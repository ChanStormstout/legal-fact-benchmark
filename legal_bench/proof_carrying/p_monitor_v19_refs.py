"""Scheduling-only supplement: observe saved P, never change proposals or labels."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from .local_schedule_v19 import checkpoint, run as saved_schedule
from .local_schedule_v18 import append

SEED_DEST = 'local/1066467/P01'
FLOW_FAILURES = {'REPETITION_ABORT', 'OUTPUT_TRUNCATED'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def streak(rows):
    """Actual completed calls in frozen order; distinct failure breaks adjacency."""
    status = None
    length = 0
    for row in rows:
        current = row['run_status']
        if current not in FLOW_FAILURES:
            status, length = None, 0
        else:
            length = length + 1 if current == status else 1
            status = current
        if length >= 2:
            return {'stop': True, 'failure': status, 'consecutive': length,
                    'trigger_dest': row['dest']}
    return {'stop': False, 'failure': status, 'consecutive': length}


class Monitor:
    def __init__(self, entry, supplement):
        self.entry = entry
        self.root = entry.OUT
        self.out = self.root / 'monitor-01'
        self.supplement = supplement

    def completed(self):
        cfg = self.entry.protocol()
        result = []
        seeded = False
        for slot in cfg['local_generation_slots']:
            if slot['role'] != 'P':
                continue
            if slot['dest'] == SEED_DEST:
                seeded = True
            path = self.root / slot['dest'] / 'run.json'
            if not path.exists():
                continue
            row = self.entry.read(path)
            if row.get('model_called') is False or not (path.parent / 'start.json').exists():
                continue
            result.append({'dest': slot['dest'], 'case_id': slot['case_id'],
                           'from_guard_seed': seeded,
                           'run_status': row['run_status'],
                           'elapsed_seconds': row.get('elapsed_seconds'),
                           'output_tokens': row.get('output_tokens'),
                           'failure_stage': row.get('failure_stage'),
                           'finish_reason': row.get('finish_reason'),
                           'record_guard': row.get('record_guard'),
                           'repetition_guard': row.get('repetition_guard'),
                           'run_sha256': digest(path),
                           'raw_path': str(path.parent / 'raw-response.txt'),
                           'raw_sha256': digest(path.parent / 'raw-response.txt')
                           if (path.parent / 'raw-response.txt').exists() else None,
                           'tokens_path': str(path.parent / 'token-ids.json')})
        return result

    def import_snapshot(self, cid):
        # Use the frozen actual converter, merger, production and independent
        # checks. The snapshot is separate from immutable consolidated P.
        from .reference_addresses_v19 import convert, audit as reference_audit
        from .local_checker_v19_refs import check, check_import
        e = self.entry
        f = e.fixture(cid)
        parts, part_states, raw_reference_checks = [], [], []
        for slot in e.protocol()['local_generation_slots']:
            if slot['role'] != 'P' or slot['case_id'] != cid:
                continue
            d = self.root / slot['dest']
            if not (d / 'run.json').exists():
                part_states.append({'part': slot['part']['id'], 'status': 'NOT_COMPLETED'})
                continue
            status = e.read(d / 'run.json')['run_status']
            part_states.append({'part': slot['part']['id'], 'status': status})
            if status != 'OK':
                parts.append((slot['part']['id'], None))
                continue
            raw = e.read(d / 'parsed.json')
            view = {**f['case'], 'segments': [x for x in f['case']['segments']
                                            if x['id'] in slot['part']['source_ids']]}
            version = e.read(d / 'production-version.json').get('version')
            transformed, mapping = convert(raw, view, version)
            transport = check_import(raw, transformed, view, version)
            if transport['status'] != 'OK':
                raise ValueError('INDEPENDENT_REFERENCE_IMPORT_REJECTED:' + str(transport['errors']))
            raw_reference_checks += [{'part': slot['part']['id'], **row} for row in reference_audit(raw, view, version)]
            parts.append((slot['part']['id'], transformed))
        readable = [p for _, p in parts if p is not None]
        if not readable:
            return {'case_id': cid, 'readable_parts': 0, 'usable_connections': 0,
                    'part_states': part_states, 'records': 0, 'uses': 0,
                    'source_reviewed_labels': [], 'independent_status': 'NO_READABLE_P'}
        p, merge_ledger = e.pipe.merge_parts(parts)
        audit = e.pipe.apply_connection_decisions(f['case'], f['rules'], p)
        independent = check(f['case'], f['rules'], p, None, audit)
        data = e.pipe.learner_inputs(f['case'], f['rules'], p)
        if independent['status'] != 'OK':
            raise ValueError('COMMON_CHECKER_RECOMPUTATION_DISAGREEMENT:' + cid)
        if len(p['records']) != audit['raw_records_retained']:
            raise ValueError('COMMON_RECORD_RETENTION_MISMATCH:' + cid)
        if data.get('reference_used') or audit.get('reference_used'):
            raise ValueError('COMMON_REFERENCE_LEAK_FLAG:' + cid)
        e.checkpoint(self.out, cid + '-import', {'proposal': p, 'audit': audit,
                     'independent': independent, 'source_manifest': data['common_material_manifest'],
                     'merge_ledger': merge_ledger})
        labels = []
        label_path = self.root / 'web/labels' / cid / 'parsed.json'
        # Reference admission is accounting only. It never enters p/audit/data.
        if label_path.exists() and all(x['status'] != 'NOT_COMPLETED' for x in part_states):
            ref = e.read(label_path)
            rows = ref.get('connections', []) if isinstance(ref, dict) else []
            visible = set(data['common_material_manifest']['saved_source_ids'])
            for use_id in data['materials']:
                matches = [r for r in rows if r['connection_id'] == use_id]
                if len(matches) != 1:
                    continue
                row = matches[0]
                location = e.pipe.source_match(row, e.pipe.sources(f['case']))
                verdict = e.label_admissibility(row, visible, location)
                if verdict['supervised']:
                    labels.append({'use_id': use_id, 'label': row['label']})
        return {'raw_reference_errors': [r for r in raw_reference_checks if r['status'] not in ('VALID', 'SOURCE_REQUIRES_LEGACY_RESOLUTION')],
                'reference_namespace_version': 'V19_REFERENCE_1',
                'case_id': cid, 'dispute_id': f['case']['dispute_id'],
                'split': f['case']['split'], 'readable_parts': len(readable),
                'part_states': part_states, 'records': len(p['records']), 'uses': len(p['uses']),
                'structurally_valid_connections': sum(not c['errors'] for c in audit['checks']),
                'usable_connections': sum(c['disposition'] == 'CONDITIONALLY_AVAILABLE_USE'
                                          for c in audit['checks']),
                'source_reviewed_labels': labels, 'independent_status': independent['status'],
                'semantic_correctness': 'NOT_ESTABLISHED_BY_TECHNICAL_OR_IMPORT_SUCCESS'}

    def observe(self, current=None):
        self.entry.assert_frozen()
        complete = self.completed()
        rolling = streak([r for r in complete if r['from_guard_seed']])
        cases, errors = [], []
        for cid in dict.fromkeys(r['case_id'] for r in complete):
            try:
                cases.append(self.import_snapshot(cid))
            except Exception as exc:
                errors.append({'case_id': cid, 'status': 'COMMON_IMPORT_CHECK_EXCEPTION',
                               'error': repr(exc)})
        train = [c for c in cases if c.get('split') == 'TRAIN']
        dev = [c for c in cases if c.get('split') == 'DEV']
        cfg = self.entry.protocol()
        status_counts = Counter(r['run_status'] for r in complete)
        new = [r for r in complete if r['dest'] not in
               {x['dest'] for x in cfg['carried_cost']['calls']}]
        p_seconds = cfg['carried_cost']['P_seconds'] + sum(r['elapsed_seconds'] or 0 for r in new)
        report = {'supplement': self.supplement['version'], 'at': self.entry.utc(),
                  'current': current, 'completed_P_calls': len(complete),
                  'P_technical_success': status_counts.get('OK', 0),
                  'P_technical_failure': sum(v for k, v in status_counts.items() if k != 'OK'),
                  'status_counts': dict(status_counts), 'rolling_guard': rolling,
                  'guard_sequence': [r for r in complete if r['from_guard_seed']],
                  'TRAIN_readable_disputes': len({c['dispute_id'] for c in train if c['readable_parts']}),
                  'TRAIN_source_reviewed_supervised_disputes': len({c['dispute_id'] for c in train if c['source_reviewed_labels']}),
                  'TRAIN_effective_label_counts': dict(Counter(l['label'] for c in train for l in c['source_reviewed_labels'])),
                  'DEV_source_reviewed_supervised_disputes': len({c['dispute_id'] for c in dev if c['source_reviewed_labels']}),
                  'DEV_effective_label_counts': dict(Counter(l['label'] for c in dev for l in c['source_reviewed_labels'])),
                  'case_imports': cases, 'common_engineering_exceptions': errors,
                  'raw_reference_error_counts': dict(Counter(r['namespace'] + ':' + r['status'] for c in cases for r in c.get('raw_reference_errors', []))),
                  'raw_reference_errors_not_legal_false': True,
                  'P_seconds_used': p_seconds, 'P_seconds_remaining': max(0, cfg['P_seconds_cap']-p_seconds),
                  'references_used_for_counts_only': True,
                  'technical_failure_not_legal_false': True,
                  'import_success_not_semantic_approval': True}
        checkpoint(self.out, 'cumulative-monitor', report)
        if rolling['stop'] or errors:
            reason = 'TWO_CONSECUTIVE_SAME_P_FLOW_FAILURES' if rolling['stop'] else 'COMMON_ENGINEERING_CHECK_EXCEPTION'
            marker = self.root / 'PAUSE_REQUESTED.json'
            value = {'reason': reason, 'at': self.entry.utc(), 'guard': rolling,
                     'exceptions': errors, 'no_retry_or_method_change': True}
            if not marker.exists():
                self.entry.save(marker, value)
            checkpoint(self.out, 'stop-evidence', {**value, 'completed': complete})
            append(self.root, {'event': 'USER_MONITOR_STOP_AFTER_SAVED', 'reason': reason,
                              'slot': current, 'guard': rolling})
        return report

    def schedule(self, root, slots, perform, after=None):
        user_stop = {'triggered': False, 'original_stop': False}
        def monitored_after(slot, result):
            original_stop = after(slot, result) if after else False
            if slot['role'] != 'P':
                return original_stop
            report = self.observe({'dest': slot['dest'], 'status': result['run_status']})
            print('P_MONITOR', json.dumps({k: report[k] for k in
                  ['current', 'completed_P_calls', 'P_technical_success', 'P_technical_failure',
                   'TRAIN_source_reviewed_supervised_disputes', 'TRAIN_effective_label_counts',
                   'rolling_guard', 'P_seconds_remaining']}), flush=True)
            user_stop['triggered'] = report['rolling_guard']['stop'] or bool(report['common_engineering_exceptions'])
            user_stop['original_stop'] = original_stop
            return original_stop or user_stop['triggered']
        result = saved_schedule(root, slots, perform, after=monitored_after)
        # Do not invoke the old early-stop branch that closes every unstarted
        # case. A user monitor stop is a pause of remaining slots, not absence.
        if result == 'STOPPED_BY_FROZEN_RULE' and user_stop['triggered'] and not user_stop['original_stop']:
            return 'STOPPED_BY_USER_MONITOR'
        return result
