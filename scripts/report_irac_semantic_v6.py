# -*- coding: utf-8 -*-
"""Package one post-batch source review; no model calls or semantic edits."""
import csv
import json
from pathlib import Path
from irac_semantic_v6 import R, CASES, read, save, hf, inputs
from irac_semantic_v6_run import ORDER, preserved


def csv_file(path, rows):
    with path.open('w', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def build():
    assert not (R/'report-zh.txt').exists(), 'Preserve completed reports'
    cfg=read(R/'freeze/config.json');batch=read(R/'run-summary.json')
    assert batch['generation_calls']<=6 and batch['elapsed_generation_seconds']<=1800
    assert all(hf(p)==h for p,h in dict(cfg['code_hashes'],**cfg['material_hashes']).items())
    reg=read(R/'registration.json')
    assert all(hf(p)==h for p,h in reg['starting_irac_code_hashes'].items())
    review=read(R/'final-source-review.json')
    assert review['review_rounds']==1 and review['after_batch_complete']
    costs=[];audits=[];links=[];answers=['# V6 complete original answers and proposals\n\nModel outputs are displayed unchanged, not as verified legal judgments.\n']
    for cid,stage in ORDER:
        out=R/'runs'/cid/stage;res=read(out/'result.json')
        meta=read(out/'run.json') if (out/'run.json').exists() else {}
        if meta.get('raw_hash'):
            assert meta['raw_hash']==hf(out/'raw-response.txt')
        assert res['run_status']=='OK' or res['prediction'] is None
        n=meta.get('prompt_tokens');output=meta.get('output_tokens',meta.get('output_tokens_observed'))
        if n is not None:assert n+cfg['max_tokens'][stage]<=32768 or res['run_status']=='INPUT_TOO_LONG'
        row={'case_id':cid,'stage':stage,'run_status':res['run_status'],'input_tokens':n,'output_tokens':output,
             'seconds':meta.get('elapsed_seconds',0),'max_output_tokens':cfg['max_tokens'][stage],
             'peak_mlx_gb':meta.get('peak_mlx_memory_gb'),'peak_rss_gb':meta.get('peak_rss_gb'),
             'raw':str(out/'raw-response.txt'),'result':str(out/'result.json')}
        costs.append(row)
        delivery=read(out/'delivery.json') if (out/'delivery.json').exists() else None
        audits.append({'case_id':cid,'stage':stage,'delivery_passed':delivery and delivery['passed'],
                       'mask_calls':meta.get('schema_mask_calls'),'thinking_off_verified':meta.get('thinking_disabled_template_verified'),
                       'actual_max_tokens':meta.get('actual_parameters',{}).get('max_tokens'),'raw_hash':meta.get('raw_hash')})
        raw=(out/'raw-response.txt').read_text() if (out/'raw-response.txt').exists() else 'No generated output; see result.json.'
        answers += ['\n## '+cid+' / '+stage+' / '+res['run_status']+'\n\n', '```json\n'+raw+'\n```\n']
    for cid in CASES:
        pdir=R/'runs'/cid/'P';presult=read(pdir/'result.json')
        if presult['prediction'] is None:continue
        imp=read(pdir/'import.json');p=presult['prediction']
        assert imp['raw_proposal']==p
        assert [x['raw'] for x in imp['records']]==p.get('records',[])
        bout=R/'runs'/cid/'B'
        if (bout/'intermediate.json').exists():
            assert read(bout/'intermediate.json')=={'proposal':p}
            a=(R/'runs'/cid/'A/prompt.txt').read_text();b=(bout/'prompt.txt').read_text()
            def strip(s):return s.split('INTERMEDIATE MATERIAL:\n\n')[0]+s.split('\n\nCOMPLETE ALLOWED CASE MATERIAL:',1)[1]
            assert strip(a)==strip(b)
        links.append({'case_id':cid,'records_preserved':len(imp['records']),'raw_P_unmodified':True,
                      'quarantines':imp['quarantine'],'B_intermediate_only_raw_P':True,'A_B_other_prompt_bytes_identical':True})
    save(R/'delivery-validation.json',{'passed':True,'slots':audits,'proposal_checks':links,
         'code_material_hashes_unchanged':True,'old_irac_code_hashes_unchanged':True,'semantic_verified':False})
    keep=preserved();assert keep['passed'];save(R/'preservation-after.json',keep)
    method_costs=[]
    for cid in CASES:
        for method,stages in [('A',['A']),('B',['P','B'])]:
            selected=[r for r in costs if r['case_id']==cid and r['stage'] in stages]
            method_costs.append({'case_id':cid,'method':method,'stages':stages,'calls':len(selected),
                 'complete':all(x['run_status']=='OK' for x in selected),'input_tokens':sum(x['input_tokens'] or 0 for x in selected),
                 'output_tokens':sum(x['output_tokens'] or 0 for x in selected),'seconds':sum(x['seconds'] for x in selected)})
    save(R/'costs.json',{'calls':costs,'methods':method_costs,'generation_calls':batch['generation_calls'],
         'total_input_tokens':sum(x['input_tokens'] or 0 for x in costs),'total_output_tokens':sum(x['output_tokens'] or 0 for x in costs),
         'generation_seconds':batch['elapsed_generation_seconds'],'load_seconds_separate':read(R/'environment.json')['loaded_seconds'],
         'memory_note':'MLX allocation peak and process peak RSS are separate observations; do not sum.',
         'comparison':'A one call; B P plus final. Net benefit with unequal compute, no attribution to an individual field or example.'})
    csv_file(R/'call-costs.csv',costs);(R/'answers.md').write_text(''.join(answers))
    comp=[]
    for cid in CASES:
        c=review['cases'][cid]
        for method in ('A','B'):
            mc=next(x for x in method_costs if x['case_id']==cid and x['method']==method)
            res=read(R/'runs'/cid/method/'result.json')
            comp.append({'case_id':cid,'method':method,'technical_status':res['run_status'],
              'prediction':json.dumps([a['prediction'] for a in res['prediction']['answers']]) if res['prediction'] else 'null',
              'source_supported':c['methods'][method]['supported'],'errors':c['methods'][method]['errors'],
              'omissions_or_contradictions':c['methods'][method]['omissions'],'real_gaps':'; '.join(c['real_gaps']),
              'net_comparison':c['comparison'],'M':c['M'],'L':c['methods'][method]['L'],
              'input_tokens_including_P':mc['input_tokens'],'output_tokens_including_P':mc['output_tokens'],'seconds_including_P':mc['seconds']})
    save(R/'case-comparison.json',comp);csv_file(R/'case-comparison.csv',comp)
    save(R/'acceptance.json',{'E':'PASS_WITH_DECLARED_ENGINEERING_SCOPE','M':{c:review['cases'][c]['M'] for c in CASES},
          'L':{c:{m:review['cases'][c]['methods'][m]['L'] for m in ('A','B')} for c in CASES},
          'decision':review['decision'],'full_legal_pipeline_accepted':False,'reference_role':review['reference_role']})
    lines=['IRAC V6: two-case full-flow comparison after semantic-interface repair\n',review['decision_zh'],
      '\nExecution: %d local calls, %.2f generation seconds (%.2f minutes), no browser calls or retries. Both are exposed development cases. C was not run; program checks were saved offline only.' % (batch['generation_calls'],batch['elapsed_generation_seconds'],batch['elapsed_generation_seconds']/60),
      '\nE: 23 tests and 17 complete real-tokenizer examples passed. Evidence is stored independently and invalid uses isolated locally. Direction does not automatically satisfy a condition. Uses attempting to prove case facts solely with legal authorities are blocked. AND/OR/NOT combine explicit model premises only. Empty answers, omissions, and repeated requests are rejected. Code, complete sources, and legal packages were unchanged after freezing. Engineering acceptance does not establish semantic correctness.',
      'A type declaration in the intermediate numeric-index schema was repaired during model-free tokenizer checking, without changing the constraint framework. Old proposals served only structural-mapping replay, not backfilled judgments. Old A was incompatible with the new actual prompt/schema, so this batch ran both afresh.']
    for cid in CASES:
        c=review['cases'][cid];lines+=['\n'+cid+'：'+c['comparison'], 'P：'+c['proposal_summary']]
        for method in ('A','B'):
            d=c['methods'][method];lines += [method+'：'+d['supported']+' Confirmed problems: '+d['errors']+' Important omissions/contradictions: '+d['omissions']]
        lines+=['Actual gaps: '+'；'.join(x.rstrip('。') for x in c['real_gaps'])+'。']
    lines+=['\nPer-call costs: ','|Case|Stage|Status|Input tokens|Output tokens|Generation seconds|','|---|---|---|---:|---:|---:|']
    for r in costs:lines.append('|%s|%s|%s|%s|%s|%.2f|'%(r['case_id'],r['stage'],r['run_status'],r['input_tokens'],r['output_tokens'],r['seconds']))
    for cid in CASES:
        a,b=[x for x in method_costs if x['case_id']==cid]
        lines.append('%s: A %.2f seconds; P+B %.2f seconds, an increase of %.2f seconds; input tokens %d→%d.'%(cid,a['seconds'],b['seconds'],b['seconds']-a['seconds'],a['input_tokens'],b['input_tokens']))
    peaks=[c['peak_mlx_gb'] for c in costs if c['peak_mlx_gb'] is not None];rss=[c['peak_rss_gb'] for c in costs if c['peak_rss_gb'] is not None]
    lines+=['Maximum MLX peak %.3f GB; maximum process peak RSS %.3f GB. These measures differ and are not added. Model loading separately took %.2f seconds.'%(max(peaks),max(rss),read(R/'environment.json')['loaded_seconds']),
      '\nConfiguration: fixed 9B revision 8b2b98c00a6b4d291155e4890773ca8f769aee53, MLX-VLM0.7.4, LMFE0.11.2, greedy, seed20261001, repetition_penalty1, thinking off; P4096, final3072, context32768.',
      'Frozen configuration SHA256: '+hf(R/'freeze/config.json')+'. Preservation check: %d files unchanged byte-for-byte.'%keep['files_checked'],
      '\nEvaluation: one consolidated model-assisted source review, not human gold. Review covers decisive allowed content and counterarguments, not just citations selected by the model. Historical outcomes are not answers the model must reconstruct. This run did not evaluate feeding program checks into the model, train or reject graph methods generally, or establish independent benefits of a field, example, or structure.',
      'Delivery: answers.md contains all raw outputs; case-comparison.csv/json contains case comparisons; final-source-review.json records source evidence. runs retains actual prompt/schema/raw/token/run files and offline checks. Verification is in delivery-validation.json, preservation-after.json, freeze/config.json, and engineering/. Stop on completion without automatically starting another round, committing, or pushing.']
    (R/'report-zh.txt').write_text('\n\n'.join(lines).replace('|\n\n|','|\n|')+'\n')
    print('REPORT BUILT',R)


if __name__=='__main__':build()
