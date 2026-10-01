"""Synthetic program checks only. Never create purported real-case/model labels."""
import json
import sys
import unittest
from pathlib import Path
from legal_bench.core import write_new
from legal_bench.engine import execute, mine, cooccurrence_query

root = Path('outputs/benchmark-pilot/e0')
suite = unittest.defaultTestLoader.discover('tests')
result = unittest.TextTestRunner(verbosity=2).run(suite)
write_new(root / 'tests.json', {'kind': 'SYNTHETIC_PROGRAM_TESTS', 'tests_run': result.testsRun,
                              'failures': len(result.failures), 'errors': len(result.errors),
                              'success': result.wasSuccessful(), 'real_case_accuracy': None})
sys.path.insert(0, 'tests')
from test_pilot import ann, event, query
a = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o2'), event('e3', 'PAYMENT', None)], 'SYNTHETIC_identity_unknown')
b = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o1')], 'SYNTHETIC_match')
pair = query(); pair['atoms'][0]['event_id'] = 'e1'; pair['atoms'][1]['event_id'] = 'e2'
write_new(root / 'mechanisms.json', {'kind': 'SYNTHETIC_NOT_GPT_ANNOTATION',
    'specified_pair': execute(a, pair), 'case_existential': execute(a, query()),
    'type_cooccurrence': execute(a, cooccurrence_query(query())), 'positive_witness': execute(b, query()),
    'mining': mine([a, b])})
raise SystemExit(0 if result.wasSuccessful() else 1)
