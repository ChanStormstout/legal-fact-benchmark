"""Complete fictional examples, nonoverlapping field duties, reversible display interning."""
import copy,json
from .contracts import obj,array,enum
from .intermediate_v7 import COMMON
from .intermediate_v8 import source_text
S=lambda:{'type':'string'}

def final_schema(case_ids,law_ids):
 return obj({'outcome':enum(['SUPPORT_GROUND','OPPOSE_GROUND','UNDETERMINED','UNSUPPORTED']),
 'grounds':array(obj({'point':S(),'case_refs':array(enum(case_ids),4),'law_refs':array(enum(law_ids),4),'assessment':enum(['SUPPORTED','REFUTED','UNRESOLVED','UNSUPPORTED']),'explanation':S()}),6),'reason':S()})

EXAMPLES=[{
 'label':'Fictional teaching example 1: fee claim (NOT target law or facts)',
 'question':'Does the supplied record establish the storage operator\'s fee-recovery ground?',
 'case_segments':[{'id':'EX1-C1','text':'The trial court found that keeper Olwen held crate C7 for owner Remi. It also found that waiver W4 applied to the storage charge for C7.'},{'id':'EX1-C2','text':'Olwen alleged that waiver W4 was ineffective, but the court rejected that allegation.'}],
 'law_segments':[{'id':'EX1-L1','text':'FICTIONAL TEACHING RULE ONLY: a keeper may recover this storage fee only if the keeper held the owner\'s crate and no court-approved waiver covers that same storage fee.'}],
 'answer':{'outcome':'OPPOSE_GROUND','grounds':[
 {'point':'Olwen held Remi\'s crate C7.','case_refs':['EX1-C1'],'law_refs':['EX1-L1'],'assessment':'SUPPORTED','explanation':'The trial court expressly found Olwen\'s custody of Remi\'s C7, satisfying the custody condition for this fee.'},
 {'point':'A court-approved waiver covers C7\'s storage fee.','case_refs':['EX1-C1','EX1-C2'],'law_refs':['EX1-L1'],'assessment':'SUPPORTED','explanation':'The court applied W4 to this same fee and rejected Olwen\'s contrary allegation. A supported waiver defeats the fictional rule\'s no-waiver requirement.'}
 ],'reason':'Although custody is established, the court-approved waiver defeats a necessary condition for recovery. The supplied record therefore opposes this fee-recovery ground.'}
},{
 'label':'Fictional teaching example 2: refund claim (NOT target law or facts)',
 'question':'Does the supplied record establish the purchaser\'s refund ground?',
 'case_segments':[{'id':'EX2-C1','text':'The trial court found that purchaser Iona cancelled order O8 from supplier Vale on 6 June.'},{'id':'EX2-C2','text':'Vale alleged that O8 had already been dispatched. The supplied record gives no dispatch date or court finding on dispatch, and contains no other evidence resolving that sequence.'}],
 'law_segments':[{'id':'EX2-L1','text':'FICTIONAL TEACHING RULE ONLY: a purchaser is entitled to this refund when cancellation of the same order occurred before its dispatch.'}],
 'answer':{'outcome':'UNDETERMINED','grounds':[
 {'point':'Iona cancelled order O8 on 6 June.','case_refs':['EX2-C1'],'law_refs':['EX2-L1'],'assessment':'SUPPORTED','explanation':'The court expressly found the purchaser, order and cancellation date; the unknown dispatch sequence does not erase that finding.'},
 {'point':'Cancellation of O8 preceded its dispatch.','case_refs':['EX2-C1','EX2-C2'],'law_refs':['EX2-L1'],'assessment':'UNRESOLVED','explanation':'Vale\'s prior-dispatch allegation is not a court finding. No dispatch date or other resolving evidence establishes which event occurred first for O8; this missing sequence is required by the fictional rule.'}
 ],'reason':'Cancellation is established, but the required cancellation-before-dispatch condition remains unresolved. The supplied material cannot establish or refute the refund ground.'}
}]

FINAL='''FINAL TASK: Answer the fixed eviction-ground question using only the TARGET allowed source and TARGET law package supplied below. The fictional examples teach output organization only; their rules, objects and IDs cannot supply target evidence. Intermediate notes/proposals/checks are fallible. Re-read complete case text and correct intermediate errors; a source address or program check is not semantic certification or a verdict.
Output one complete JSON object with outcome, grounds and reason, then END the answer. outcome is SUPPORT_GROUND, OPPOSE_GROUND, UNDETERMINED or UNSUPPORTED. Use at most six grounds, normally three to five where useful. Each ground has:
point: only ONE short declarative proposition to assess, usually 8-20 words and one sentence. End this field after naming the proposition. No reasoning, rule application or whole verdict in point.
case_refs: target case source IDs supporting this ground; law_refs: target LAW source IDs for its rule/scope. Empty arrays are allowed for a genuine absence of support, which must be explained. Do not cite teaching IDs, intermediate IDs or card IDs as source IDs.
assessment: SUPPORTED, REFUTED, UNRESOLVED or UNSUPPORTED describes the truth/support of THIS point, not the eviction direction. A supported defense may defeat the ground. An uncertain condition is not disproved.
explanation: usually one to three sentences (30-65 words is a soft target), stating relevant objects and events, who asserted what and whether a court adopted it, decisive supporting AND contrary evidence, and application of the supplied rule or the specific gap. Combine these duties here ONCE. Do not repeat another ground or give the full conclusion here. Preserve decisive limits even when short.
reason: one or two sentences explaining what the grounds imply for the eviction issue; do not retell the case or add new rules.
Keep case-fact uncertainty, supplied-law gaps and unimplemented program interpretation distinct. Missing names or dates matter only when decisive. A failed combination is not whole-case absence; no program witness is not contrary source evidence. Already established facts remain established when another condition is unresolved. Do not infer the withheld historical outcome. Concision is a writing goal, not permission to omit decisive evidence, cut strings or invent missing facts. Complete within the unchanged 3072-token budget.
'''

def prompt(source,package,material):
 return (COMMON+'\nTWO COMPLETE FICTIONAL INPUT-OUTPUT EXAMPLES (output duties appear in final instructions)\n'+json.dumps(EXAMPLES,ensure_ascii=False,separators=(',',':'))+'\nEND OF TEACHING EXAMPLES. ONLY FOLLOWING TARGET MATERIAL MAY BE CITED.\nTARGET SHARED LAW PACKAGE\n'+json.dumps(package,ensure_ascii=False)+'\nTARGET INTERMEDIATE MATERIAL (UNVERIFIED)\n'+json.dumps(material,ensure_ascii=False,separators=(',',':'))+'\nTARGET COMPLETE ALLOWED CASE SOURCE\n'+source_text(source)+'\nFINAL TASK REMINDER\n'+FINAL)

def compact_display(view):
 """Intern exact repeated result/state values. No removal of any binding or source."""
 out=copy.deepcopy(view);results={};signals={};states={}
 def intern(table,value,prefix):
  key=json.dumps(value,sort_keys=True,ensure_ascii=False)
  if key not in table:table[key]=(prefix+str(len(table)+1),copy.deepcopy(value))
  return table[key][0]
 for j in out['joins']:j['result_ref']=intern(results,j.pop('result'),'R')
 for c in out['combinations']:
  c['condition_signals_ref']=intern(signals,c.pop('condition_signals'),'S')
  c['state_ref']=intern(states,c.pop('state'),'C')
 out['result_definitions']={k:v for k,v in results.values()};out['signal_definitions']={k:v for k,v in signals.values()};out['state_definitions']={k:v for k,v in states.values()}
 return out

def expand_display(view):
 out=copy.deepcopy(view);rd=out.pop('result_definitions');sd=out.pop('signal_definitions');cd=out.pop('state_definitions')
 for j in out['joins']:j['result']=rd[j.pop('result_ref')]
 for c in out['combinations']:
  c['condition_signals']=sd[c.pop('condition_signals_ref')];c['state']=cd[c.pop('state_ref')]
 return out
