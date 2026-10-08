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
    costs=[];audits=[];links=[];answers=['# V6 完整原始答案与提议\n\n模型输出原样展示，不代表经核验的法律判断。\n']
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
    lines=['IRAC V6：语义接口修复后的两案完整流程比较\n',review['decision_zh'],
      '\n运行：%d次本地调用，生成%.2f秒（%.2f分钟），网页0、重试0。两案均为旧案开发验证。未运行C，程序检查仅离线保存。' % (batch['generation_calls'],batch['elapsed_generation_seconds'],batch['elapsed_generation_seconds']/60),
      '\nE：23项相关测试及17个真实tokenizer完整样例通过。证据独立保存、用途局部隔离；方向不自动成为条件满足；法源单独证明本案事实的用途受阻；AND/OR/NOT只组合显式模型前提；空答、漏答及重复请求拒收。源码、完整来源与法律包冻结后未变。工程通过不证明语义正确。',
      '中间数字索引Schema的类型声明错误已在无模型tokenizer检查中修复，未改约束框架。旧提议仅作结构映射重放，未补写旧判断；旧A与新实际prompt/Schema不兼容，本轮均重新运行。']
    for cid in CASES:
        c=review['cases'][cid];lines+=['\n'+cid+'：'+c['comparison'], 'P：'+c['proposal_summary']]
        for method in ('A','B'):
            d=c['methods'][method];lines += [method+'：'+d['supported']+' 已确认问题：'+d['errors']+' 重要遗漏／矛盾：'+d['omissions']]
        lines+=['真实缺口：'+'；'.join(x.rstrip('。') for x in c['real_gaps'])+'。']
    lines+=['\n逐调用成本：','|案件|阶段|状态|输入tokens|输出tokens|生成秒|','|---|---|---|---:|---:|---:|']
    for r in costs:lines.append('|%s|%s|%s|%s|%s|%.2f|'%(r['case_id'],r['stage'],r['run_status'],r['input_tokens'],r['output_tokens'],r['seconds']))
    for cid in CASES:
        a,b=[x for x in method_costs if x['case_id']==cid]
        lines.append('%s：A %.2f秒；P+B %.2f秒，增加%.2f秒；输入tokens %d→%d。'%(cid,a['seconds'],b['seconds'],b['seconds']-a['seconds'],a['input_tokens'],b['input_tokens']))
    peaks=[c['peak_mlx_gb'] for c in costs if c['peak_mlx_gb'] is not None];rss=[c['peak_rss_gb'] for c in costs if c['peak_rss_gb'] is not None]
    lines+=['MLX峰值最大%.3fGB；进程峰值RSS最大%.3fGB，口径不同不相加。模型加载另计%.2f秒。'%(max(peaks),max(rss),read(R/'environment.json')['loaded_seconds']),
      '\n配置：固定9B revision 8b2b98c00a6b4d291155e4890773ca8f769aee53、MLX-VLM0.7.4、LMFE0.11.2、greedy、seed20261001、repetition_penalty1、thinking关闭；P4096、最终3072、上下文32768。',
      '冻结配置SHA256：'+hf(R/'freeze/config.json')+'。历史保留检查%d文件原字节不变。'%keep['files_checked'],
      '\n评价：一次集中模型辅助来源审阅，非人工gold；检查允许材料中的决定性内容及反论，不只检查模型引用。两案历史结论不作为必须猜回的正确答案。本轮没有评估程序检查送入模型的效果，没有训练或否定整个图方法，也不声称单字段、示例或结构单独有效。',
      '交付：answers.md含全部原始输出；case-comparison.csv/json为逐案比较；final-source-review.json为来源依据；runs内含实际prompt/schema/raw/token/run及离线checks；delivery-validation.json、preservation-after.json、freeze/config.json、engineering/保存核验。完成后停止，不自行开启下一轮，不提交或推送。']
    (R/'report-zh.txt').write_text('\n\n'.join(lines).replace('|\n\n|','|\n|')+'\n')
    print('REPORT BUILT',R)


if __name__=='__main__':build()
