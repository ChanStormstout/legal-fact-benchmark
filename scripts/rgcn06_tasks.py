#!/usr/bin/env python3
import sys,json,hashlib,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rgcn06_prepare import R,rd,write,task
LAW=rd(R/'sources/laws.json');S=rd(R/'sources/samples.json')
GRAPH='''Build an INPUT representation, not an answer or ranking. See all14 original laws and their source-only condition proposals. Do not score usefulness, select a best law or decide eviction. All14 must have an alignment entry even if none/unknown/incompatible. Output object:
{"case_id":"ID","needs":[{"id":"n1","text":"legal question triggered by allowed case","refs":["case segment ID"]}],"objects":[{"id":"o1","text":"short mention","kind":"PERSON|ORGANIZATION|PROPERTY|GROUP|DOCUMENT|EVENT|OTHER","refs":["segment ID"],"unknown":false}],"facts":[{"id":"f1","text":"one task-relevant source assertion","speaker":"LANDLORD|TENANT|THIRD_PARTY|COURT|NARRATOR|UNKNOWN","status":"CLAIMED|FOUND|REPORTED|DISPUTED|UNKNOWN","court":"TRIAL|APPELLATE|TARGET|NONE|UNKNOWN","stage":"brief procedure stage","polarity":"POSITIVE|NEGATIVE|UNKNOWN","unknown":["specific unresolved fields"],"roles":[{"role":"ACTOR|RECIPIENT|PROPERTY|DOCUMENT|SUBJECT|OBJECT","object_id":"o1"}],"refs":["segment ID"],"quote":"short EXACT substring of one ref"}],"relations":[{"id":"r1","left":"o1","right":"o2","relation":"member_of|part_of|same_as|controls|transferred_to|other","text":"direction and scope","speaker":"...","status":"...","court":"...","stage":"...","polarity":"...","unknown":[],"refs":["segment"],"quote":"exact substring"}],"alignments":[{"unit_id":"lawID","scope":"DIRECT|ANALOGY|INCOMPATIBLE|UNKNOWN","state":"CANDIDATE|NONE|UNKNOWN|INCOMPATIBLE","links":[{"need_id":"n1","condition_id":"c1","fact_ids":["f1"],"relation_ids":[],"kind":"BASE|EXCEPTION|COUNTER|LIMITATION","state":"CANDIDATE|UNKNOWN","reason":"possible analysis connection, NOT condition satisfaction","case_refs":["segment"],"law_quote":"EXACT substring from this legal unit"}],"reason":"scope/missing connection explanation"}],"coverage_limits":[]}
Use documented enum ONE value, not the pipe-separated string. Typically 3–6 distinct needs and 8–16 essential facts; these are soft concision targets, never delete decisive counterevidence for a count. Empty arrays allowed; missing identity never a wildcard. relations are propositions with their own status, not unconditional edges. Keep allegations distinct from findings and preserve lower-court level. Unknown connections must not be asserted. Conditions and IDs come from supplied proposals, whose semantics remain provisional; originals control. All14 alignment entries required. No known relevance labels available. No result of the withheld judgment may be inferred. A complete synthetic fact example: {"id":"f1","text":"Lessee alleges retaining keys","speaker":"TENANT","status":"CLAIMED","court":"NONE","stage":"pleading","polarity":"POSITIVE","unknown":["court acceptance"],"roles":[{"role":"ACTOR","object_id":"o1"}],"refs":["P1"],"quote":"The lessee says she retained the keys."}. No target answer suggested.'''
USES='''Independently judge uses of ALL14 law units for the supplied fixed question and allowed case. No model rankings, answers or input graph are provided. Output {"case_id":"ID","uses":[{"unit_id":"exact law ID","category":"DIRECT|EXCEPTION_COUNTER|BACKGROUND|NO_USE|UNKNOWN","issue":"explicit question served","case_refs":["segment IDs"],"law_quote":"short EXACT substring from unit supporting assessment","reason":"why useful or why no use found in CURRENT scope; not universal irrelevance","dependencies":["law IDs"],"standalone_value":"what this unit alone supports/does not","incremental_value":"potential complement or redundancy when dependencies already present","limits":"scope/version/adoption/uncertainty"}],"coverage_limits":[]}. Categories are exclusive primary use: DIRECT controls a subquestion; EXCEPTION_COUNTER limits/opposes a route; BACKGROUND contextual only; NO_USE after inspecting supplied scope with reason; UNKNOWN insufficient basis. A law whose condition fails may still control; contrary authority can be essential. No citation or prior reference is required for usefulness; all14 assessed symmetrically. Do not manufacture distinctions. Exact quote is location evidence, not automatic adoption. Do not answer final target outcome.'''
PREF='''For each supplied candidate pair, independently compare priority under the fixed question and 20,000-character whole-source/dependency budget. Uses are provisional annotations, originals control. Output {"case_id":"ID","preferences":[{"a":"unit ID","b":"unit ID","decision":"A|B|TIE|INCOMPARABLE|UNKNOWN","reason":"source-based priority and budget reason; not merely category/name","case_refs":["IDs"],"a_quote":"exact substring of a","b_quote":"exact substring of b","standalone":"individual usefulness comparison","bundle_increment":"dependencies/complementarity; not known final selector outcome"}],"coverage_limits":[]}. Answer EVERY supplied pair exactly once. Lower-ranked may still be relevant; do not infer negative relevance. Different functions often incomparable; preserve uncertainty. No ranking/output available.'''
def material(s):
 source=rd(R/('sources/'+s['case_id']+'.json'))
 source=dict(source,segments=[{k:x[k] for k in ('id','text')} for x in source['segments']])
 laws=[{k:v for k,v in u.items() if k!='source'}|{'source':{k:v for k,v in u.get('source',{}).items() if k!='raw_provenance'}} for u in LAW]
 return dict(question=s['question'],case=source,laws=laws)
def main():
 mode=sys.argv[1]
 if mode=='base':
  write('input-contract.txt',GRAPH);write('uses-contract.txt',USES);write('preference-contract.txt',PREF)
  for i,s in enumerate(S,1):task('USE%02d'%i,USES,json.dumps(material(s),ensure_ascii=False))
 elif mode=='graph':
  props=[]
  for i in range(1,5):props+=rd(R/('parsed/LAW%02d.json'%i))['units']
  write('law-proposals.json',props)
  for i,s in enumerate(S,1):task('GRAPH%02d'%i,GRAPH,json.dumps(dict(material(s),source_only_condition_proposals=props),ensure_ascii=False))
 elif mode=='pairs':
  for i,s in enumerate(S,1):
   u=rd(R/('parsed/USE%02d.json'%i));groups={}
   for x in u['uses']:groups.setdefault(x['category'],[]).append(x['unit_id'])
   pairs=set()
   for cat,g in groups.items():
    g.sort()
    if len(g)>1:
     for a,b in zip(g,g[1:]+g[:1]):pairs.add(tuple(sorted([a,b])))
   for x,y in itertools.combinations(sorted(groups),2):
    for a in [groups[x][0],groups[x][-1]]:
     for b in [groups[y][0],groups[y][-1]]:pairs.add(tuple(sorted([a,b])))
   pairs=sorted(pairs,key=lambda p:hashlib.sha256(('20261004'+s['case_id']+'|'.join(p)).encode()).hexdigest())[:16]
   write('pairs/'+s['case_id']+'.json',pairs)
   task('PREF%02d'%i,PREF,json.dumps(dict(material(s),uses=u,pairs=pairs),ensure_ascii=False))
if __name__=='__main__':main()
