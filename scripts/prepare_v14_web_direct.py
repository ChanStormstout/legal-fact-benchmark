"""Prepare same-information web tasks, without previous answers or review hints."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('outputs/rules-verdict-v14-web-direct')
OLD = Path('outputs/rules-verdict-v13-crosscase')
CASES = ['661475', '1134266']
EXECUTION = ('只依据本任务提供的材料回答，不进行外部搜索，不查找该案件的其他版本，不依赖其他对话。'
             '请一次性按给定格式提供完整最终答案。可使用文件工具生成可下载JSON，但不要额外补充法律资料。')
WRAPPER = ('请完整读取附件任务文件，其中V13 D实际提示词原字节保留，随后附同一输出Schema。'
           '网页端没有复用本地逐token的Schema约束。' + EXECUTION)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f: json.dump(x, f, ensure_ascii=False, indent=2); f.write('\n')

if __name__ == '__main__':
    assert not (ROOT/'freeze.json').exists(), 'Frozen experiment must be continued, never overwritten'
    ROOT.mkdir(parents=True,exist_ok=True)
    oldfiles = {str(p):sha(p) for p in Path('outputs').rglob('*') if p.is_file() and ROOT not in p.parents and '__pycache__' not in p.parts}
    code = {str(p):sha(p) for base in ['legal_bench','scripts','tests'] for p in Path(base).rglob('*.py') if '__pycache__' not in p.parts}
    if not (ROOT/'start-audit.json').exists():
        write(ROOT/'start-audit.json', {'time':datetime.now(timezone.utc).isoformat(), 'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), 'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(), 'historical_files':oldfiles, 'code':code})
        (ROOT/'starting-git-status.txt').write_text(subprocess.check_output(['git','status','--short'],text=True))
    hashes = {}
    for c in CASES:
        dest=ROOT/'tasks'/c; dest.mkdir(parents=True,exist_ok=True)
        items={'prompt.txt':OLD/'runs'/c/'D/prompt.txt', 'schema.json':OLD/'runs'/c/'D/schema.json',
               'source.json':OLD/'sources'/f'{c}.json', 'law-package.json':OLD/'prepared'/c/'law-package.json',
               'retrieval.json':OLD/'retrieval'/c/'result.json'}
        for name, orig in items.items():
            if (dest/name).exists(): assert sha(orig)==sha(dest/name)
            else: shutil.copyfile(orig,dest/name)
        prompt=(dest/'prompt.txt').read_bytes(); schema=(dest/'schema.json').read_bytes()
        task=prompt+b'\n\nOUTPUT SCHEMA (same V13 D contract; web generation is not token-constrained)\n'+schema
        (dest/f'case_{c}_task.txt').write_bytes(task)
        (dest/'submission-text.txt').write_text(WRAPPER,encoding='utf-8')
        hashes[c]={name:sha(dest/name) for name in items}
        hashes[c]['task_file']=sha(dest/f'case_{c}_task.txt')
        hashes[c]['prompt_bytes']=len(prompt)
        assert task[:len(prompt)]==prompt
    write(ROOT/'protocol.json', {'version':'V14', 'order':CASES, 'method':'WEB_DIRECT_SAME_INFORMATION_AS_V13_D',
        'max_web_answers':2,'max_answers_per_case':1,'retries':0,'local_model_calls':0,'paid_api_calls':0,
        'new_sources_or_intermediates':False,'requested_mode':'ordinary High, not Pro','model_identity':'record actual UI; unavailable if not exposed',
        'schema_constraint':'Schema supplied as text; no local token mask on web',
        'execution_wrapper':WRAPPER,'material_hashes':hashes,'review':'one final concentrated source review, not human gold',
        'no_commit_push_or_next_round':True,'comparison_limit':'cross-model/runtime diagnosis, not parameter-size-only controlled experiment'})
    write(ROOT/'evaluation-rules.json', {'not_model_input':True,'compare_to':'V13 D per case; B-P background only',
        'check':['explicit facts and omitted decisive source content','party allegation vs court finding and hierarchy','cross-case contamination',
                 'event date and bounds','permission giver and object','OR/necessary/negation semantics','true vs invented gaps','internal consistency','opposing grounds'],
        'no_accuracy_ranking':True,'reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
    write(ROOT/'freeze.json', {'files':{str(p):sha(p) for p in ROOT.rglob('*') if p.is_file()},'prepared_before_submission':True})
    print(json.dumps({'root':str(ROOT),'cases':CASES,'tasks':hashes},ensure_ascii=False))
