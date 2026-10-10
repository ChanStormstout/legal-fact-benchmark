"""Render pinned reconstruction records without generating new legal content."""
import html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/proof-carrying-realcase-v2'
def e(x):return html.escape(str(x))
def load(p):return json.loads(p.read_text())
def ref(cid,r):return '<a href="#'+e(cid+'-'+r)+'">'+e(r)+'</a>'
def block(value):return '<pre>'+e(json.dumps(value,ensure_ascii=False,indent=2))+'</pre>'
def main():
    parts=['''<!doctype html><meta charset="utf-8"><title>Real judgment reconstruction v2</title>
<style>body{font:16px/1.55 system-ui;max-width:1150px;margin:32px auto;padding:0 24px;color:#203047;background:#fafafa}a{color:#075bb0}section,article{padding:18px;margin:18px 0;background:white;border:1px solid #ccd5df;border-radius:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 ui-monospace}details{margin:12px 0}summary{cursor:pointer;font-weight:600}nav{position:sticky;top:0;background:#fafafa;padding:10px;border-bottom:1px solid #ccc}.tag{display:inline-block;background:#e7edf4;border-radius:4px;padding:2px 7px;margin:2px}.warn{background:#fff2db;padding:12px;border-left:4px solid #ba7c10}h1,h2,h3{line-height:1.25}</style>
<h1>Real judgment reasoning reconstruction</h1><p class="warn">Research draft only. Model-assisted source review; qualified legal approval is PENDING. A valid typed trace is not legal certification. Complete judgments include their reasons and outcomes: this is reconstruction, not prediction. No exhibit originals or original cited precedents were independently obtained.</p><nav>''']
    for cid in ('789051','1418721','1841885'):parts.append('<a href="#case-'+cid+'">'+cid+'</a> &nbsp; ')
    parts.append('</nav>')
    for cid in ('789051','1418721','1841885'):
        cp=OUT/'cases'/cid;sp=cp/'snapshots/S1.json'
        if not sp.exists():continue
        s=load(sp);parts.append('<section id="case-'+cid+'"><h2>'+cid+'</h2><p>Stage: '+e(s['stage'])+'</p>')
        for version in ('S1','S2'):
            rp=cp/'runs'/version
            if not (rp/'check.json').exists():continue
            result=load(rp/'check.json');cert=load(rp/'certificate.json');snap=load(cp/'snapshots'/(version+'.json'))
            label='Original model proposal' if version=='S1' else 'Explicit maintainer research correction, not a new model answer'
            parts.append('<article><h3>'+version+' · '+label+'</h3>')
            for q in result.get('requests',[]):
                parts.append('<p><b>'+e(q['id'])+'</b> '+e(q['text'])+'</p><p><span class="tag">Executable trace '+e(q['draft_status'])+'</span><span class="tag">Answer '+e(q.get('answer'))+'</span><span class="tag">Legal approval PENDING</span></p>')
                parts.append('<p>Errors: '+e(q.get('errors',[]))+'<br>Gaps: '+e(q.get('gaps',[]))+'</p>')
            for st in cert['proposal']['steps']:
                chk=result.get('steps',{}).get(st['id'],{})
                parts.append('<details id="'+cid+'-'+version+'-'+e(st['id'])+'"><summary>Step '+e(st['id'])+' → '+e(st['rule_ref'])+' · proposed '+e(st['proposed_state'])+' / computed '+e(chk.get('state'))+'</summary>')
                parts.append(block(st)+'<p>Check: '+e(chk.get('status','NOT_VISITED'))+'</p>'+block({'errors':chk.get('errors',[]),'gaps':chk.get('gaps',[])}))
                for i in st['inputs']:
                    anchor=cid+('-premise-'+i['id'] if i['kind']=='PREMISE' else '-'+version+'-'+i['id'])
                    parts.append('<p>'+e(i['slot'])+' ← <a href="#'+e(anchor)+'">'+e(i['kind']+' '+i['id'])+'</a></p>')
                rule=snap['rules'].get(st['rule_ref'])
                if rule:
                    parts.append('<h4>Rule, scope and remaining evaluation</h4>'+block(rule)+'<p>'+', '.join(ref(cid,r) for r in rule['source_refs'])+'</p>')
                parts.append('</details>')
            parts.append('<details><summary>Preserved counterarguments and gaps</summary>'+block({k:cert['proposal'][k] for k in ('counterarguments','gaps')})+'</details></article>')
        parts.append('<h3>Premise records and review decisions</h3>')
        for pid,p in s['premises'].items():
            parts.append('<details id="'+cid+'-premise-'+e(pid)+'"><summary>'+e(pid+' · '+p['statement_status']+' · '+p['state'])+'</summary>'+block(p)+'<p>Review: '+e(s['reviews']['premises'].get(pid,{}).get('decision','MISSING'))+'</p><p>'+', '.join(ref(cid,r) for r in p['refs'])+'</p></details>')
        parts.append('<h3>Complete saved judgment body</h3>')
        for rid,r in s['sources'].items():
            parts.append('<p id="'+e(cid+'-'+rid)+'"><a href="'+e(r['url'])+'">'+e(rid)+'</a> '+e(r['text'])+'</p>')
        parts.append('</section>')
    path=OUT/'walkthrough.html'
    with path.open('x') as f:f.write('\n'.join(parts))
    print(path)
if __name__=='__main__':main()
