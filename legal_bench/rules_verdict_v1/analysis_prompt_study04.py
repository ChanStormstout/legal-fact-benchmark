"""Bounded same-material prompt comparison. No model calls, semantic repairs or retrieval."""
import hashlib,json,random
from .rule_retrieval_v21 import parse_answer

ADDITION = '''ANALYSIS ORGANIZATION FOR THIS ANSWER
Use the existing grounds fields to present a concise, source-supported argument, not internal reasoning or a separate evidence table. For each material issue, distinguish the proposition and who advances it; identify any supplied court treatment at its actual court level and procedural stage, including what remains only alleged, disputed or undecided. Then address the material supporting reason and strongest supplied opposing reason, with the relevant legal premise, scope and limitation, before explaining the consequence or specific unresolved gap. Keep different parties' positions separate when they differ. References must support the proposition and its stated evidentiary status, not merely mention a related subject. A party's assertion is not a court finding; absence of identified proof is not proof of nonexistence. Preserve relevant prior findings without treating them as the withheld final court's endorsement. Do not fill absent facts or laws. If a component is absent or immaterial, explain only the decisive gap rather than inventing an entry. Conclude from the supported grounds with the existing outcome categories. This is one answer: keep the same output contract, do not add a preliminary extraction, exhaustive table or extra fields, and do not repeat the same explanation across grounds.
'''
MARKER='OUTPUT SCHEMA (web has no local token mask)\n'
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def treatment(control):
 if control.count(MARKER)!=1:raise ValueError('Schema marker not unique')
 return control.replace(MARKER,ADDITION+'\n'+MARKER)
def order_cases(case_ids,seed):
 r=random.Random(seed);cs=list(case_ids);r.shuffle(cs);start=r.randrange(2);out=[]
 for n,cid in enumerate(cs):
  arms=['CONTROL','TREATMENT'] if (n+start)%2==0 else ['TREATMENT','CONTROL']
  for arm in arms:out.append({'id':'ANS%02d'%(len(out)+1),'case_id':cid,'arm':arm})
 return out

def parse_raw(raw,case_ids,law_ids):
 try:
  answer,validation=parse_answer(raw,case_ids,law_ids)
  return {'run_status':'OK','answer':answer,'validation':validation,'semantic_correctness_certified':False}
 except (ValueError,TypeError,KeyError) as exc:
  return {'run_status':'FORMAT_ERROR','answer':None,'error':str(exc),'raw_preserved':True}
