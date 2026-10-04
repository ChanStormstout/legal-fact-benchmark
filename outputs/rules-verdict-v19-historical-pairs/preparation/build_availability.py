"""Build the bounded V19 availability record; no inference or method changes."""
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/rules-verdict-v19-historical-pairs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


# These are source-based screening decisions, not answers to the legal task.
OLD_REASONS = [
    ('STATUTE_AND_ISSUE_MISMATCH', '喀拉拉影院房产、继承与土地改革／耕作租户问题，不是公司合并后的Delhi第14(1)(b)租赁权转移。', ['Kerala', 'Land Reforms']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'Karnataka第21(1)(h)条的合理自用需要，不是本轮公司继受争点。', ['21(1)(h)', 'bona fide']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'Bengal非农业租赁法第9条的通知期限和月租关系；公司名称不等于公司合并争点。', ['Non-Agricultural', 'notice']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'Andhra Pradesh非住宅房产的合理自用需要及第10(3)(a)(iii)条。', ['10(3)', 'bona fide']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'Calcutta Thika租赁法修法追溯效力及执行问题。', ['Thika', '28']),
    ('ISSUE_MISMATCH', 'Delhi第21条限期租赁许可及许可效力；不是公司合并后的第14(1)(b)请求。', ['21', 'permission']),
    ('REQUEST_AND_ISSUE_MISMATCH', '共同租户、承认事实判决和普通民事腾退，不是公司合并继受争点。', ['Order XII', '3500']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'Madhya Pradesh房东权属、买卖及租户禁反言问题。', ['Madhya Pradesh', '116']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'East Punjab第13条欠租及首次开庭付款问题。', ['East Punjab', 'tender']),
    ('REQUEST_AND_ISSUE_MISMATCH', '财产分割、租户承认新房东及禁令问题；公司作为租户并不构成合并争点。', ['partition', 'injunction']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'Rishikesh／Uttar Pradesh小额诉讼欠租和租金数额争议。', ['Rishikesh', 'rent']),
    ('STATUTE_AND_PROCEDURE_MISMATCH', 'Mysore房屋租赁及执行、恢复占有管辖问题。', ['Mysore', 'execution']),
    ('REQUEST_AND_PROCEDURE_MISMATCH', 'Amritsar案件的CPC第39条禁令上诉问题。', ['Amritsar', 'Order']),
    ('STATUTE_AND_ISSUE_MISMATCH', 'Calcutta租赁期满后收租、继续占有和TPA第106／116条。', ['Calcutta', '116']),
    ('REQUEST_AND_PROCEDURE_MISMATCH', 'Agra合伙人死亡后的上诉失效和必要当事人问题；不是公司合并。', ['partner', 'appeal']),
    ('STATUTE_AND_PROCEDURE_MISMATCH', 'Lucknow租约及仲裁转介争议；不是Delhi公司继受腾退条件。', ['Lucknow', 'arbitration']),
]

NEW = {
    '197892008': dict(title='Subhash Chand Goel & Ors v Hans Raj Gupta & Co Pvt Ltd', court='Delhi High Court', date='2019-09-02', proceeding='CM(M) 340/2012', subgroup='COMPANY_PROPOSED_AMALGAMATION', decision='SCOPE_COMPATIBLE_INPUT_NOT_FROZEN', reason='DISPL合并进入HRGPL是否构成第14(1)(b)条转租／转移占有；另有时效争点，任务尚未从完整判决切出。', evidence=[71, 75, 79, 85, 90], body=[46, 189], possible_input=[68, 90], limits='Analysis从L91开始；未来任务必须排除目标法院自身分析及结论。'),
    '65127929': dict(title='Ms Asiya Jamil v Canara Bank', court='Delhi Rent Controller', date='2009-04-08', proceeding='E-361/07', subgroup='BANKING_STATUTORY_SUCCESSION', decision='SCOPE_COMPATIBLE_INPUT_NOT_FROZEN', reason='Lakshmi Commercial Bank转归Canara Bank，涉及第14(1)(b)条、法定合并与书面／默示同意；同时有第14(1)(f)条请求，不能合并评分。', evidence=[79, 87, 94, 99, 105], body=[40, 154], possible_input=[79, 106], limits='目标法院实体分析从第11段附近开始；与43070016为已知同一纠纷，不可再纳入后续上诉。'),
    '110204406': dict(title='Raghunandan Saran Ashok Saran (HUF) v National Insurance Co', court='Delhi Rent Controller', date='2011-11-28', proceeding='EC E-13/08/09', subgroup='INSURANCE_STATUTORY_SUCCESSION_SECONDARY_ISSUE', decision='CONDITIONAL_SCOPE_COMPATIBLE_INPUT_LIMIT', reason='第14(1)(b)条员工占有争点中同时讨论New Zealand Insurance被并入National Insurance的非自愿抗辩；合并并非唯一或主要请求事实。', evidence=[159, 160, 206], body=[40, 287], possible_input=None, limits='合并抗辩的明确记载在目标法院分析L206中。尚未确认如何在保留主要双方论点的同时隔离目标理由，因此不能称为已准备好的合格任务；仍作为相容候选上界计数。'),
    '157278563': dict(title='ICICI Bank Ltd v Shakuntla Gupta', court='Delhi High Court', date='2015-08-12', proceeding='RFA(OS) 43/2015', subgroup='ORDINARY_CIVIL_LEASE_OUTSIDE_DRC', decision='EXCLUDED', reason='原文第4段明确房产不受Delhi Rent Control Act保护，属于普通民事租约与银行合并；不能混入本轮第14(1)(b)条实验。', evidence=[91], body=[40, 248], possible_input=None, limits='排除根据明示法条范围，不根据裁判结果或预计收益。'),
    '132592552': dict(title='M/s Puran Chand & Co v Canara Bank', court='Delhi District Court', date='2014-07-09', proceeding='CS-279/2010', subgroup='MORTGAGE_REDEMPTION_AND_CIVIL_POSSESSION', decision='EXCLUDED', reason='抵押赎回／拍卖后占有与租户继受问题，争点包含民事管辖；并非第14(1)(b)条公司转移腾退请求。', evidence=[74, 77, 113, 120], body=None, possible_input=None, limits='现有网页读取仅取得判决前部与争点，足以确认程序范围不同；未认证完整39页判决。'),
    '1295488': dict(title='Sequent Scientific Ltd / P.I. Drugs & Pharmaceuticals Ltd (company petitions)', court='Bombay High Court', date='2009-06-16', proceeding='Company Petitions 99/2009 and 100/2009', subgroup='SCHEME_APPROVAL', decision='EXCLUDED', reason='正文实际是公司合并方案批准及技术供应合同异议，并非搜索标题暗示的Delhi租赁案件。', evidence=[136, 157, 175], body=None, possible_input=None, limits='检索标题与正文不一致，以正文为准；已取得前部足以排除，未认证判决全部末段。'),
    '39942283': dict(title='British Motor Car Company (1939) Ltd v Hindustan Commercial Bank Ltd', court='Supreme Court of India', date='2026-07-09', proceeding='Civil Appeal 5714/2012', subgroup='BANKING_STATUTORY_SUCCESSION', decision='SCOPE_COMPATIBLE_INPUT_NOT_FROZEN', reason='Delhi第14(1)(b)条及Hindustan Commercial Bank转归PNB，呈现Rent Controller／Tribunal／High Court层级和双方争辩。', evidence=[69, 136, 155], body=[44, 281], possible_input=[69, 156], limits='OUR VIEW从L157开始。既有2012年CM(M)485/2001属于同一纠纷，不能当作另一个样本。后续仍需核实合适基础法包。'),
    '1033921': dict(title='Mrs Asha Rohtagi & Ors v Erstwhile New Bank of India / PNB', court='Delhi High Court', date='2005-04-21', proceeding='Article 227; E-288/2004 and RCA-609/2004', subgroup='BANKING_STATUTORY_SUCCESSION', decision='SCOPE_COMPATIBLE_INPUT_NOT_FROZEN', reason='New Bank of India按1993年方案转归PNB；明确是Delhi第14(1)(a)/(b)请求，仅拟使用(b)的继受问题。', evidence=[52, 53, 55, 56, 63], body=[44, 122], possible_input=[52, 63], limits='第4段L65起进入目标判例分析；不得保留目标法院最后的判断来构造任务答案。'),
}


def main():
    started = read(OUT / 'preparation/starting-state.json')
    old_order = read(OUT / 'screening/existing-order.json')
    new_order = read(OUT / 'screening/new-order.json')['entries']
    assert len(old_order) == 16 and len(new_order) == 8
    candidate_ids = [x['case_id'] for x in old_order + new_order]
    assert len(set(candidate_ids)) == 24
    raw_files = sorted(p for p in (OUT / 'screening').glob('*.txt') if 'search' not in p.name)
    # Only split and address already saved tool renderings. No retrieval or rewriting.
    line_views = {cid: {} for cid in NEW}
    file_index = {cid: [] for cid in NEW}
    header = re.compile(r'(?m)^.*\(https://indiankanoon\.org/doc/(\d+)/\)\n')
    for p in raw_files:
        text = p.read_text(encoding='utf-8')
        heads = list(header.finditer(text))
        for i, h in enumerate(heads):
            cid = h[1]
            if cid not in NEW:
                continue
            block = text[h.end():heads[i+1].start() if i+1 < len(heads) else len(text)]
            marks = list(re.finditer(r'\bL(\d+): ?', block))
            entries = []
            for j, m in enumerate(marks):
                end = marks[j+1].start() if j+1 < len(marks) else len(block)
                value = block[m.end():end]
                # Last block may contain the next error/metadata entry: do not treat it as judgment text.
                value = value.split('\nInternal Error ()')[0]
                number = int(m[1])
                entries.append(number)
                line_views[cid].setdefault(number, []).append({'raw_path': p.relative_to(ROOT).as_posix(), 'rendered_text': value})
            file_index[cid].append({'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'first_rendered_line': min(entries) if entries else None, 'last_rendered_line': max(entries) if entries else None, 'contains_body_lines': bool(entries)})
    rows = []
    for order, (entry, reason) in enumerate(zip(old_order, OLD_REASONS), 1):
        source = read(ROOT / entry['source_path'])
        selected = source['segments'][:5]
        matches = [s for s in source['segments'] if any(k.lower() in s['text'].lower() for k in reason[2])]
        selected += matches[:4]
        unique = {s['id']:s for s in selected}
        evidence = [{'segment_id':s['id'], 'page':s['page'], 'text':s['text']} for s in unique.values()]
        save('sources/' + entry['case_id'] + '-screening-evidence.json', {
            'case_id':entry['case_id'], 'source_path':entry['source_path'], 'source_sha256':entry['source_sha256'],
            'parent_source_completeness':source.get('source_completeness'),
            'role':'FOCUSED_SCOPE_SCREENING_NOT_FULL_ANNOTATION_OR_FULL_JUDGMENT_CERTIFICATION',
            'selection':'Opening segments plus deterministic lexical locators for statute/request; decisions read from these original passages, not keyword absence.',
            'evidence':evidence,
        })
        rows.append({**entry, 'screening_order':order, 'source_kind':'EXISTING_SEGMENTS', 'decision':'EXCLUDED', 'reason_code':reason[0], 'reason_zh':reason[1],
                     'evidence_file':'sources/' + entry['case_id'] + '-screening-evidence.json',
                     'prior_use':'PRESENT_IN_SAVED_CANDIDATE_QUEUE; NOT_SELECTED_FOR_ANSWERING',
                     'relationship':'NOT_EXPANDED_AFTER_SCOPE_EXCLUSION', 'full_task_input_frozen':False})
    for order, entry in enumerate(new_order, 17):
        cid = entry['case_id']; d = NEW[cid]; views = line_views[cid]
        assert views, 'Missing saved source body ' + cid
        evidence = [{'source_id':'IK-' + cid + ':L' + str(n), 'line':n, 'renderings':views[n]} for n in d['evidence'] if n in views]
        assert evidence, cid
        body = d['body']
        missing = [n for n in range(body[0], body[1]+1) if n not in views] if body else None
        save('sources/' + cid + '-rendered-lines.json', {
            'case_id':cid, 'url':entry['url'], 'title_from_body':d['title'], 'court':d['court'], 'date':d['date'], 'proceeding':d['proceeding'],
            'provenance':'Saved web open renderings of primary judgment text; not HTML/PDF original bytes.',
            'transformation':'Split existing tool text on document headers and L<number> addresses only; original raw files remain unchanged. Citation/navigation markup retained, no legal wording corrected.',
            'raw_reads':file_index[cid], 'body_range_examined':body, 'missing_body_line_addresses':missing,
            'coverage_status':'RENDERED_BODY_START_THROUGH_TERMINAL_PRESENT_NO_PDF_CERTIFICATION' if body and not missing else 'PARTIAL_RENDERING_SUFFICIENT_FOR_SCOPE_DECISION',
            'lines':[{'line':n, 'renderings':v} for n,v in sorted(views.items()) if not body or body[0] <= n <= body[1]],
        })
        save('sources/' + cid + '-scope-evidence.json', {'case_id':cid, 'evidence':evidence, 'role':'AVAILABILITY_SCOPE_ONLY_NOT_LEGAL_REFERENCE_ANSWER'})
        known_rel = 'KNOWN_SAME_DISPUTE_AS_43070016_LATER_APPEAL_EXCLUDED' if cid == '65127929' else ('KNOWN_SAME_DISPUTE_AS_2012_CM_M_485_2001_NOT_ACQUIRED_SEPARATELY' if cid == '39942283' else 'NO_KNOWN_SAME_DISPUTE_IN_SELECTED_WINDOW; RELATEDNESS_NOT_CERTIFIED')
        prior_hits = [p for p in started['historical_output_sha256'] if cid in p]
        rows.append({**entry, 'screening_order':order, 'source_kind':'NEW_PRIMARY_WEB_RENDERING', 'title_from_body':d['title'], 'court':d['court'], 'date':d['date'], 'proceeding':d['proceeding'],
                     'decision':d['decision'], 'reason_code':d['subgroup'], 'reason_zh':d['reason'], 'evidence_file':'sources/' + cid + '-scope-evidence.json',
                     'prior_use':{'historical_output_filename_hits':prior_hits, 'status':'NO_TARGET_FILE_FOUND_NOT_PROOF_OF_NO_PRIOR_EXPOSURE' if not prior_hits else 'HISTORICAL_PATH_HITS_RECORDED', 'limitation':'No global no-exposure claim; mentions in another judgment do not mean target developed.'},
                     'relationship':known_rel, 'input_feasibility':{'possible_line_window_not_final_allowed_input':d['possible_input'], 'limitation':d['limits']}, 'full_task_input_frozen':False})
    compatible = [r['case_id'] for r in rows if r['decision'].startswith('SCOPE_COMPATIBLE') or r['decision'].startswith('CONDITIONAL_SCOPE')]
    assert len(compatible) == 5
    save('candidate-decisions.json', {'protocol':'preparation/screening-protocol.json', 'rows':rows})
    with (OUT / 'candidate-list.csv').open('w', newline='', encoding='utf-8') as f:
        keys = ['screening_order','case_id','title','source_kind','decision','reason_code','reason_zh','evidence_file']
        w = csv.DictWriter(f, keys); w.writeheader()
        for r in rows:
            w.writerow({k:(r.get('title_from_body') or r.get('title') or r.get('locator_title')) if k == 'title' else r.get(k,'') for k in keys})
    rules = []
    for path in ['outputs/rules-verdict-v15-rule-supplement/rule-package.json', 'outputs/rules-verdict-v16-rule-transfer/rule-collection.json', 'outputs/rules-verdict-v18-application-chain/data-lineage.json']:
        rules.append({'path':path, 'sha256':sha(ROOT/path), 'role':'EXISTING_READ_ONLY_RULE_OR_LINEAGE_MATERIAL; NOT_ASSIGNED_TO_NEW_TASKS'})
    save('preparation/existing-rule-inventory.json', {'files':rules, 'source_case_exclusions':['GENERAL_RADIO','HINDUSTAN_PETROLEUM','TELESOUND','PARASRAM_REPORTED_ONLY','69305','661475','1134266'], 'new_rule_cards_created':0, 'supplement_package_frozen':False})
    save('screening/known-related-locators.json', {'records':[{'case_id':'43070016','related_to':'65127929','basis':'Same named parties and Chasma Building premises; later RCT appeal47/09, dated2009-12-15; locator inspected, no extra full judgment acquired.', 'decision':'EXCLUDED_BEFORE_NEW_ACQUISITION','source':'screening/v19search3-results.txt'}, {'case_id':'2012 CM(M)485/2001','related_to':'39942283','basis':'Target Supreme Court paragraph1 identifies the challenged Delhi High Court judgment; not a second independently sampled dispute.', 'decision':'NOT_ACQUIRED_AS_EXTRA_CANDIDATE','source':'sources/39942283-scope-evidence.json'}], 'independence_certified':False})
    save('screening/retrieval-limitations.json', {
        'new_unique_primary_judgments_acquired':8, 'request_attempt_count_exact':None,
        'observed_transport_failures':[{'method':'direct urllib HTML acquisition','error':'HTTP 403','raw_response_saved':False,'role':'TRANSPORT_FAILURE_NOT_MODEL_ANSWER_FAILURE'}, {'method':'first web open of132592552','error':'Internal Error','raw_response':'screening/new-eight-web-read.txt','subsequent_primary_rendering':'screening/v19puran.txt'}],
        'repeat_opens':'Only already chosen primary documents, to retrieve continuation/body after metadata or short views. Not new candidates, model-answer retries or source expansions.',
        'saved_search_result_batches':4, 'earlier_search_result_batches_not_saved_in_full':2,
        'locator_use':'Search snippets and secondary results locate documents; legal scope decisions use primary body excerpts.',
        'full_judgment_certification':False,
    })
    now = datetime.now(timezone.utc)
    available = {
        'version':'V19', 'status':'NOT_RUN_SAMPLE_SHORTAGE', 'seed':20261003,
        'primary_scope':'Delhi Rent Control Act s14(1)(b), company amalgamation/statutory tenancy succession',
        'candidate_slots_reviewed':24, 'existing_source_candidates':16, 'new_unique_primary_judgments':8,
        'scope_compatible_candidate_upper_bound':5, 'scope_compatible_case_ids':compatible,
        'conditional_input_scope_case_ids':['110204406'], 'fully_frozen_task_count':0,
        'excluded_candidates':19, 'minimum_required_to_start':6,
        'gate_decision':'STOP_BEFORE_PAIR_PREPARATION_AND_MODEL_GENERATION',
        'sampling_and_repeat_selection':'NOT_APPLICABLE_BELOW_GATE; seed saved, no samples/repeats selected',
        'web_model_answers':0, 'local_model_calls':0, 'paid_api_calls':0, 'model_answer_retries':0,
        'complete_paired_cases':0, 'pair_categories':{'B_net_improvement':None,'AB_close':None,'B_worse':None,'indeterminate':None},
        'model_name_displayed':None, 'mode_observed':None, 'tokens':None,
        'answer':None, 'source_review_role':'MODEL_ASSISTED_AVAILABILITY_REVIEW_NOT_HUMAN_GOLD',
        'bounded_screening_complete':True, 'legal_method_benefit_evaluated':False,
        'publication':'LOCAL_ONLY_NO_COMMIT_NO_PUSH', 'recorded_at':now.isoformat(),
        'preparation_elapsed_wall_seconds':(now - datetime.fromisoformat(started['recorded_at'])).total_seconds(),
        'elapsed_measurement':'Elapsed preparation wall time including source retrieval and reading; not model generation time or per-condition cost.',
        'limits':['Focused source screening is not full fact annotation or visual PDF completeness validation.', 'Five is an upper bound of scope-compatible availability, not five already frozen and leakage-audited tasks.', 'No proof of complete dispute independence or global absence of prior exposure.', 'This bounded sample shortage does not show the legal method fails or no suitable cases exist outside the window.'],
    }
    save('availability.json', available)
    save('stop-record.json', {'status':'STOPPED_AT_PREDEFINED_AVAILABILITY_GATE', 'candidate_limit_reached':24,'new_acquisition_limit_reached':8,'minimum_case_gate_met':False,'last_step':'Availability report and local repository integrity/review package','next_model_step':'NOT_STARTED','no_additional_candidates_or_model_runs':True,'no_next_round_or_commit_or_push':True})
    save('decision.json', {'decision':'EVIDENCE_INSUFFICIENT_FOR_RULE_SUPPLEMENT_BENEFIT_NO_MODEL_COMPARISON', 'basis':'Even all five scope-compatible/conditional candidates fall below the predefined minimum6.', 'method_changes':False, 'scope_change':False, 'possible_next_decisions_not_authorized':['Approve a separate larger primary-source window for this statutory issue.', 'Explicitly choose a different issue with a sufficient prepared cohort; do not mix statute scopes to fill this round.']})
    # Original annotations, historical frozen outputs and current method code are read-only.
    preserved = {}; changed = []
    for key in ['historical_output_sha256','starting_code_sha256']:
        for p,h in started[key].items():
            path=ROOT/p
            if not path.is_file() or sha(path)!=h:
                changed.append(p)
        preserved[key] = len(started[key])
    save('preservation-check.json', {'status':'PASS' if not changed else 'FAIL', 'checked':preserved, 'changed_or_missing':changed, 'scope':'All pre-existing output bytes and all starting method/script/test .py bytes; repository docs/review wrappers intentionally updated separately.'})
    assert not changed, changed
    print(json.dumps({'candidate_slots':24,'compatible_upper_bound':5,'model_answers':0,'gate':'STOP','preservation':preserved},ensure_ascii=False))


if __name__ == '__main__':
    main()
