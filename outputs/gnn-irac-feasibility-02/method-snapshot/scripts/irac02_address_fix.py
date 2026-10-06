"""Pre-binding address-only correction: recognize saved PDF segment_offsets.

Never changes rule text, condition semantics, or a model proposal. Initial freeze
retained. No binding generation has started. New active files are immutable.
"""
import datetime,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from irac02_prepare import R,IDS,rd,put,sha,task
assert not list((R/'web').glob('B-*.run.json')), 'No address revision after inference generation'
changes=[]
for cid in IDS:
 p=rd(R/'rule-package'/f'{cid}.json');rules={r['rule_id']:r for r in p['rules']};conditions={c['condition_id']:c for c in p['conditions']};checks=[]
 for prior in p['program_checks']:
  c=conditions[prior['condition_id']];r=rules[c['rule_id']];src=r['source_document'];addresses={c['rule_id']}|{z['id'] for field in ['passage_addresses','segment_offsets'] for z in src.get(field,[])}
  errors=[e for e in prior['locator_and_reference_errors'] if e!='CONDITION_SOURCE_OUTSIDE_RULE']
  if not set(c['source_refs'])<=addresses:errors.append('CONDITION_SOURCE_OUTSIDE_RULE')
  checks.append({'condition_id':c['condition_id'],'locator_and_reference_errors':errors})
  if prior['locator_and_reference_errors']!=errors:changes.append({'case_id':cid,'condition_id':c['condition_id'],'old_errors':prior['locator_and_reference_errors'],'new_errors':errors,'original_source_offsets':src.get('segment_offsets',[])})
 p['program_checks']=checks;sem_block=[z for z in p['independent_review']['condition_reviews']+p['independent_review']['rule_reviews'] if z['status']=='BLOCKING_GAP'];p['rule_complete']=bool(p['proposal']['rule_complete'] and p['independent_review']['rule_complete'] and not p['rule_errors'] and not sem_block and not any(z['locator_and_reference_errors'] for z in checks))
 put('rule-package-address-v2/'+cid+'.json',p)
old=rd(R/'rule-condition-freeze.json');put('rule-condition-freeze-address-v2.json',dict(old,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),rules={c:sha(R/'rule-package-address-v2'/f'{c}.json') for c in IDS},supersedes_address_check_only=sha(R/'rule-condition-freeze.json'),reason='Saved PDF segment_offsets are valid addresses, not just passage_addresses. No rule/condition semantic change; before first blind call.'))
put('pre-binding-address-correction.json',{'changes':changes,'source_mapping_only':True,'old_freeze_preserved':True,'model_retries':0,'no_binding_started':True,'text_condition_equality':all(rd(R/'rule-package'/f'{c}.json')['conditions']==rd(R/'rule-package-address-v2'/f'{c}.json')['conditions'] for c in IDS)})
for cid in IDS:
 item=rd(R/'blind-binding-tasks'/f'{cid}.json');p=rd(R/'rule-package-address-v2'/f'{cid}.json')
 if p['rule_complete'] and item['input'] is None:
  from legal_bench.rules_verdict_v1.irac_gate_v2 import inference_payload
  from irac02_prepare import OLD
  st=rd(R/'stage-partition'/f'{cid}.json');inv=st['admitted_inventory'];x=rd(OLD/'inputs'/f'{cid}.json');grants={z['record_id']:z for z in st['records']}
  item['input']=inference_payload(x['fixed_issue'],p['rules'],p['conditions'],inv['facts'],inv['relations'],inv['objects'],inv['sources']);item['input']['record_stage']=[{k:v for k,v in grants['facts:'+f['id']].items() if k!='reason'} for f in inv['facts']]
 item['rule_complete']=p['rule_complete'];item['skip_reason']=None if p['rule_complete'] else 'RULE_CONDITION_BLOCKING_GAP_SKIP_BINDING';put('blind-binding-tasks-address-v2/'+cid+'.json',item)
for n in range(1,5):
 old_text=(R/'tasks'/f'B-{n}.txt').read_text();instruction=old_text.split('\nMATERIAL\n')[0];data=[rd(R/'blind-binding-tasks-address-v2'/f'{c}.json') for c in IDS[(n-1)*2:n*2]];task('B-'+str(n)+'-address-v2',instruction,data)
put('blind-binding-input-freeze-address-v2.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rule_condition_freeze':sha(R/'rule-condition-freeze-address-v2.json'),'stage_partition_freeze':sha(R/'stage-partition-freeze.json'),'input_hashes':{c:sha(R/'blind-binding-tasks-address-v2'/f'{c}.json') for c in IDS},'prompt_hashes':{f'B-{n}':sha(R/'tasks'/f'B-{n}-address-v2.txt') for n in range(1,5)},'code_hashes':{str(p):sha(p) for p in [Path('scripts/irac02_address_fix.py'),Path('legal_bench/rules_verdict_v1/irac_gate_v2.py')]},'active_rule_path':'rule-package-address-v2','active_input_path':'blind-binding-tasks-address-v2'})
put('active-prebinding-version.json',{'rule_package':'rule-package-address-v2','rule_condition_freeze':'rule-condition-freeze-address-v2.json','binding_inputs':'blind-binding-tasks-address-v2','binding_input_freeze':'blind-binding-input-freeze-address-v2.json','actual_prompt_suffix':'-address-v2','initial_version_retained':True})
print('Address-only prebinding freeze complete; changed',changes)
