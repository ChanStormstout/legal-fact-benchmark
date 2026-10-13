import json
import tempfile
import unittest
from pathlib import Path
from legal_bench.proof_carrying.p_monitor_v19 import Monitor, streak


class MonitorTests(unittest.TestCase):
    def test_consecutive_repetition_and_success_reset(self):
        def rows(*statuses):
            return [{'dest': str(i), 'run_status': s} for i, s in enumerate(statuses)]
        self.assertTrue(streak(rows('REPETITION_ABORT', 'REPETITION_ABORT'))['stop'])
        self.assertTrue(streak(rows('OUTPUT_TRUNCATED', 'OUTPUT_TRUNCATED'))['stop'])
        self.assertFalse(streak(rows('REPETITION_ABORT', 'OK', 'REPETITION_ABORT'))['stop'])
        self.assertFalse(streak(rows('REPETITION_ABORT', 'OUTPUT_TRUNCATED'))['stop'])
        self.assertFalse(streak(rows('OUTPUT_TRUNCATED', 'FORMAT_ERROR', 'OUTPUT_TRUNCATED'))['stop'])

    def test_actual_saved_scheduler_stops_before_third_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slots = [{'role': 'P', 'dest': 'local/c/P%02d' % n} for n in [1, 2, 3]]
            saved = []
            statuses = []
            monitor = object.__new__(Monitor)
            def observe(current):
                self.assertTrue((root/current['dest']/'formal-answer.json').exists())
                statuses.append({'dest': current['dest'], 'run_status': current['status']})
                return {'current': current, 'completed_P_calls': len(statuses),
                        'P_technical_success': 0, 'P_technical_failure': len(statuses),
                        'TRAIN_source_reviewed_supervised_disputes': 0,
                        'TRAIN_effective_label_counts': {}, 'P_seconds_remaining': 100,
                        'rolling_guard': streak(statuses), 'common_engineering_exceptions': []}
            monitor.observe = observe
            def perform(slot, dest):
                dest.mkdir(parents=True)
                value = {'run_status': 'REPETITION_ABORT'}
                (dest/'run.json').write_text(json.dumps(value))
                (dest/'formal-answer.json').write_text('{"answer":null}')
                saved.append(slot['dest'])
                return value
            result = monitor.schedule(root, slots, perform)
            self.assertEqual(result, 'STOPPED_BY_USER_MONITOR')
            self.assertEqual(len(saved), 2)
            self.assertFalse((root/slots[2]['dest']).exists())


if __name__ == '__main__':
    unittest.main()
