"""Apply the same lossless boolean-format recovery to all B outputs; preserve runs."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.boolean_format_v3 import parse_boolean_literals
from legal_bench.rules_verdict_v1.conditions_v3 import import_facts,execute
from legal_bench.rules_verdict_v1.source_views import write_new,digest

root=Path('outputs/rules-verdict-v3');cid=sys.argv[1]
if cid not in ['661475','69305','1134266']:raise ValueError('Outside fixed cases')
folder=root/'runs'/cid/'B';meta=json.loads((folder/'run.json').read_text())
source=json.loads((root/'sources'/(cid+'-allowed.json')).read_text())
out=root/'format-recovery'/cid
if not (out/'recovery.json').exists():
    raw=(folder/'raw-response.txt').read_text()
    result={'original_run_status':meta['run_status'],'raw_hash':digest(raw.encode()),
        'no_new_generation':True,'semantic_modifications':False,'effective_run_status':meta['run_status']}
    if meta['run_status']=='OK' or (meta['run_status']=='FORMAT_ERROR' and meta.get('finish_reason')=='stop'):
        try:
            parsed,repairs,normalized=parse_boolean_literals(raw)
            view=import_facts(parsed,source)
            write_new(out/'parsed.json',parsed)
            write_new(out/'imported.json',view)
            write_new(out/'execution.json',[execute(view,q,cid) for q in ['Q1','Q2','Q3']])
            result.update(effective_run_status='OK',repairs=repairs,
                normalized_hash=digest(normalized.encode()),quarantined=len(view['quarantine']),
                usable_objects=len(view['objects']),usable_atoms=len(view['atoms']))
        except (ValueError,KeyError,TypeError) as exc:
            result.update(effective_run_status='FORMAT_ERROR',error=str(exc))
    write_new(out/'recovery.json',result)
print((out/'recovery.json').read_text())
