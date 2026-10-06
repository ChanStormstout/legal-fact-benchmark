"""Known-use coverage at unit and source-document grain; never unlabeled negatives."""
from .authority_use_v10 import normalize,CLASSES
from . import legal_material_v10 as pack

def evaluate(case_id,method,seed,ranking,slots,units,selection,predictions=None):
 known={u:s['canonical_category'] for u,s in slots.items() if s['state']=='KNOWN'}
 selected=set(selection['selected_ids']);mandatory=set(selection['mandatory_ids']);core={u for u,c in known.items() if c=='CORE'}-mandatory;irrelevant={u for u,c in known.items() if c=='IRRELEVANT'};background={u for u,c in known.items() if c=='BACKGROUND'}
 by={u['id']:u for u in units};doc=lambda uid:str(by[uid].get('source',{}).get('document_id',by[uid].get('source_document_id',uid)))
 feasible={u for u in core if u in pack.select([{'id':u}],units,pack.PRIMARY_CONFIG,mandatory=mandatory)['selected_ids']}
 reasons={}
 for uid in sorted(core-selected):
  d=next((d for d in selection['decisions'] if d['id']==uid),{})
  reasons[uid]='INDIVIDUAL_DEPENDENCY_BUNDLE_TOO_LONG' if uid not in feasible else d.get('decision','NOT_IN_RANKING')
 confusion=[[0]*3 for _ in range(3)]
 if predictions is not None:
  index={u['id']:i for i,u in enumerate(units)}
  for u,c in known.items():confusion[CLASSES.index(c)][int(predictions[index[u]])]+=1
 alldocs={doc(u) for u in core};deliverdocs={doc(u) for u in core&selected};unknown={u for u,s in slots.items() if s['state']!='KNOWN'}
 return {'case_id':case_id,'method':method,'seed':seed,'core_delivered':[len(core&selected),len(core)],'feasible_core_delivered':[len(feasible&selected),len(feasible)],'individually_undeliverable':sorted(core-feasible),'core_document_delivered':[len(deliverdocs),len(alldocs)],'core_missing_reasons':reasons,'known_irrelevant_selected':sorted(irrelevant&selected),'known_irrelevant_characters':sum(len(pack.render([by[u]]))-2 for u in irrelevant&selected),'background_delivered':[len(background&selected),len(background)],'unknown_positions':len(unknown),'unknown_selected':sorted(unknown&selected),'slot_status_counts':{s:sum(v['state']==s for v in slots.values()) for s in ['KNOWN','UNKNOWN','ISOLATED','UNPROCESSED']},'selected_ids':selection['selected_ids'],'legal_characters':selection['legal_characters'],'confusion':confusion,'classification_known':len(known),'not_accuracy_or_complete_recall':True}
