"""Post-run, evaluation-only report; never changes frozen selection or policy."""
import json,sys,csv,copy,subprocess,html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import byte_hash
from legal_bench.proof_carrying.contracts_v10 import propose
R=Path('outputs/proof-carrying-selection-readiness-v10');V9=Path('outputs/proof-carrying-dependency-repair-v9')
read=lambda p:json.loads(p.read_text())
def save(p,d):
 if p.exists():raise FileExistsError(p)
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
notes={
'789051':('SOURCE_TYPE_SELECTION','L66–69, L106–113 preserve possession/title non-proof and reservation; judicial settled-possession classification remains an external research premise, not mechanically proved.'),
'1418721':('RANKING_HEADROOM','L85 title basis; L90–101 adverse-possession pleading/proof rejection. Q4 combines two separately checked grounds; does not prove title merely from failure of adverse possession.'),
'1841885':('SELECTION_AND_PREDICATE_MAPPING','L130–137 distinguishes tenancy civil adjudication from trust inquiry; L151–153 does not resolve disputed forcible eviction or entitlement to injunction. Q4 still rejects trust_denial_recorded predicate substitution.'),
'840688':('MACRO_COVERAGE','L129–130 and L183–186 limited expired-lease restoration analysis retained. R2 requires both stages of orders and criticism plus merits review; incomplete components cannot be treated as complete.'),
'161859415':('NO_NEW_CHANGE','L76–77, L151–159 support standing and non-joinder conclusions under attributed Court assessment, not independently established title or timeliness.'),
'74028':('REFERENCE_ADDRESS_AND_OPEN_TEXT','L76 trial reasons; L117–119 prima facie revocation; L122–127 review and merits reservation. Seven exact reference addresses repaired. Q-S2 recorded conclusion quote still cannot be located; do not invent it.'),
'522414':('MACRO_COVERAGE','P07 states no plot160, but old macro also includes misdescription conclusion. L125–134 contains broader Court reasoning; cannot fill the missing premise with the same conclusion to be derived. Earlier two TRUE results are withdrawn under stricter coverage, not model deterioration.'),
'1144022':('COVERAGE_AND_ASSESSMENT','Contract/expiry/continued occupation and split Kasliwal reasoning remain unaligned; opposing opinions and referral are retained. Located quotes do not create missing accepted Court assessments.')}
rows=[];review=[];requests=[]
for cid in read(Path('outputs/proof-carrying-graph-integration-v8/protocol.json'))['case_order']:
 p=R/'results/simple'/cid;pool=R/'results/pool'/cid
 old=read(V9/'results/dependency'/cid/'analysis.json');new=read(p/'analysis.json');oracle=read(pool/'oracle.json');der=read(pool/'derivation.json');snap=read(pool/'snapshot.json');origin=read(pool/'route-origin.json');qmap=read(pool/'request-map.json')
 # Verify the diagnostic witness using only its budgeted candidates and dependency closure.
 selected=set(oracle['selected']);sd=copy.deepcopy(der);sd['steps']=[s for s in sd['steps'] if origin[s['id']] in selected];ids={s['id'] for s in sd['steps']}
 sd['steps']=[s for s in sd['steps'] if all(x['kind']!='STEP' or x['id'] in ids for x in s['inputs'])];ids={s['id'] for s in sd['steps']}
 sd['requests']=[q for q in sd['requests'] if q['step_id'] in ids]
 dest=R/'diagnostic-witness'/cid
 if sd['requests']:
  save(dest/'snapshot.json',snap);save(dest/'derivation.json',sd);save(dest/'certificate.json',propose(snap,sd));save(dest/'manifest.json',{'snapshots':{snap['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(dest/'snapshot.json')}}})
  argv=[sys.executable,'scripts/check_realcase_certificate_v10.py',str(dest/'certificate.json'),'--manifest',str(dest/'manifest.json')];proc=subprocess.run(argv,capture_output=True,text=True,timeout=120);(dest/'stdout.txt').write_text(proc.stdout);(dest/'stderr.txt').write_text(proc.stderr);ck=json.loads(proc.stdout);save(dest/'checked.json',ck)
  confirmed=sorted({qmap[q['id']] for q in ck.get('requests',[]) if q.get('answer')=='TRUE' and not q.get('errors')});assert confirmed==oracle['covered_requests'],(cid,confirmed,oracle['covered_requests'])
 else:confirmed=[]
 save(dest/'budget-validation.json',{'candidate_ids':sorted(selected),'candidate_count':len(selected),'budget':6,'confirmed_requests':confirmed,'evaluation_only':True})
 simple={q['id'] for q in new['requests'] if q['answer']=='TRUE'};oldtrue={q['id'] for q in old['requests'] if q['answer']=='TRUE'}
 elig=read(p/'eligibility.json');ledger=read(R/'prepared'/cid/'reference-address-revision.json');limits=[x for x in der['gaps'] if x.startswith('ROUTE_LIMIT')]
 row={'case':cid,'v9_true':len(oldtrue),'v10_simple_true':len(simple),'budgeted_witness_true':len(confirmed),'requests':len(new['requests']),'recovered':sorted(simple-oldtrue),'withdrawn':sorted(oldtrue-simple),'ranking_headroom':sorted(set(confirmed)-simple),'explicit_exclusions':sum(x['status']=='EXCLUDE_EXPLICIT_CONTRACT_ERROR' for x in elig),'candidate_count':len(elig),'address_revisions':sum(x['status']=='ADDRESS_ONLY_REVISION' for x in ledger),'enumeration_limits':limits,'frontier_capped':oracle['frontier_capped']};rows.append(row)
 review.append({**row,'attribution':notes[cid][0],'source_review':notes[cid][1],'review_label':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','formal_legal_approval':False,'all_counterarguments_preserved_in_offline_audit':True,'not_all_counterarguments_in_budgeted_derivation':True})
 for q in new['requests']:
  requests.append({'case':cid,'request':q['id'],'v9':next(z['answer'] for z in old['requests'] if z['id']==q['id']),'v10':q['answer'],'budgeted_witness':q['id'] in confirmed,'errors':sorted({e for a in q['alternatives'] for e in a.get('errors',[])}),'gaps':sorted({e for a in q['alternatives'] for e in a.get('gaps',[])})})
save(R/'source-review.json',review);save(R/'request-diagnosis.json',requests);save(R/'summary.json',rows)
with (R/'comparison.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
oldhash=read(R/'registration.json')['old_hashes'];changed=[p for p,h in oldhash.items() if not Path(p).is_file() or byte_hash(Path(p))!=h];assert not changed
freeze=read(R/'freeze.json');assert all(byte_hash(Path(p))==h for p,h in freeze['method_hashes'].items());assert all(byte_hash(Path(p))==h for p,h in freeze['input_hashes'].items())
save(R/'delivery-validation.json',{'historical_files_checked':len(oldhash),'historical_changes':changed,'frozen_method_and_inputs_match':True,'new_model_calls':0,'weight_loads':0,'fits':0,'actual_checker_subprocesses':16+sum(bool(r['budgeted_witness_true']) for r in rows),'same_candidate_budget':6,'diagnostic_witnesses_independently_rechecked':True,'legal_approval':False})
links=''.join('<tr><td>'+r['case']+'</td><td>'+str(r['v9_true'])+'</td><td>'+str(r['v10_simple_true'])+'</td><td>'+str(r['budgeted_witness_true'])+'</td><td><a href="results/simple/'+r['case']+'/index.html">Analysis and alternatives</a></td></tr>' for r in rows)
(R/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>V10: cached interface repair and selection readiness</h1><p>Research reconstruction, not legal approval. No model calls/training. Diagnostic witness uses evaluation information; it is not a competing method.</p><a href="report-zh.txt">中文报告</a> · <a href="source-review.json">Source review</a> · <a href="request-diagnosis.json">Request diagnosis</a><table border="1"><tr><th>Case</th><th>V9</th><th>V10 Simple</th><th>Evaluation witness ≤6</th><th>Trace</th></tr>'+links+'</table>')
print(json.dumps(rows,ensure_ascii=False))
