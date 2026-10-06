"""Four-unit independent overlays. No targets accepted by the graph path."""
import copy
from . import coarse_label_v10 as lab
FAMILY=('LAW:S02:DRC:17','LAW:S02:DRC:18','LAW:V09:GL_WRITTEN_CONSENT','LAW:V09:GL_CONCURRING_LIMIT')
def label_overlay(old,review,source,units):
 out=copy.deepcopy(old);table=[];changes=[]
 for uid in FAMILY:
  prior=copy.deepcopy(old['slots'][uid]);r=review.get(uid);status='REVIEW_NOT_COMPLETED';slot=dict(prior,state='REVIEW_NOT_COMPLETED',reason='NO_VALID_COMPLETE_L_PATH_REVIEW')
  if r:
   try:
    assert str(r['case_id'])==str(source['case_id']) and r['unit_id']==uid
    action=r['action'];assert action in ('KEEP','CHANGE','UNKNOWN','ISOLATE')
    if action=='ISOLATE':slot=dict(prior,state='ISOLATED',reason=r['reason']);status='ISOLATED'
    else:
     row={k:r[k] for k in lab.FIELDS};ins=lab.inspect({'case_id':source['case_id'],'uses':[row]},source,units);slot=ins['slots'][uid]
     if action=='UNKNOWN':assert slot.get('canonical_category')=='UNKNOWN'
     if action=='CHANGE':assert slot.get('canonical_category') in ('CORE','BACKGROUND','IRRELEVANT')
     if action=='KEEP':
      assert prior['state']=='KNOWN' and slot.get('canonical_category')==prior['canonical_category'], 'KEEP_CANNOT_RECOVER_ISOLATION_OR_CHANGE_CATEGORY'
     status='UNKNOWN' if slot['state']=='UNKNOWN' else 'ISOLATED' if slot['state']=='ISOLATED' else action
    slot['semantic_quality']='V11_SINGLE_PASS_INDEPENDENT_L_MODEL_REVIEW_NOT_GOLD';slot['previous_semantic_quality']=prior.get('semantic_quality');slot['review']=r
   except (AssertionError,KeyError,ValueError,TypeError) as e:
    slot=dict(prior,state='ISOLATED',reason='L_INTERFACE_FAILURE: '+str(e),review=r);status='ISOLATED'
  out['slots'][uid]=slot
  item={'case_id':source['case_id'],'unit_id':uid,'path':'L','version':'V11','status':status,'old_value':prior,'new_value':slot,'reason':slot.get('reason',slot.get('record',{}).get('reason')),'source_refs':[] if not r else r.get('case_refs',[])};table.append(item)
  if slot!=prior:changes.append(item)
 assert all(out['slots'][u]==old['slots'][u] for u in old['slots'] if u not in FAMILY)
 return out,table,changes

def graph_overlay(proposal,review,source,rejected):
 """Masks scoped to existing family alignment IDs; shared nodes stay byte-equivalent."""
 out=copy.deepcopy(proposal);masks=set(rejected);refs={s['id'] for s in source['segments']};table=[];changes=[]
 for a in out['alignments']:
  uid=a['unit_id']
  if uid not in FAMILY:continue
  prior=copy.deepcopy(a);r=review.get(uid);status='REVIEW_NOT_COMPLETED'
  try:
   if not r:raise ValueError('G_REVIEW_NOT_COMPLETED')
   assert str(r['case_id'])==str(source['case_id']) and r['unit_id']==uid
   assert r['scope'] in ('DIRECT','ANALOGY','INCOMPATIBLE','UNKNOWN') and r['state'] in ('CANDIDATE','NONE','UNKNOWN','INCOMPATIBLE')
   assert r['reason'] and isinstance(r['case_refs'],list) and all(k in refs for k in r['case_refs'])
   ls=r['link_reviews'];assert len(ls)==len(a['links']) and {l['index'] for l in ls}==set(range(len(a['links'])))
   for l in ls:
    assert l['action'] in ('KEEP','UNKNOWN','ISOLATE') and l['reason'] and all(k in refs for k in l['case_refs'])
    j=l['index']
    if l['action']=='ISOLATE':masks.add(uid+'::alignment'+str(j))
    elif l['action']=='UNKNOWN':a['links'][j]['state']='UNKNOWN'
   a['scope']=r['scope'];a['state']=r['state'];a['reason']=r['reason']
   # NONE/INCOMPATIBLE cannot preserve asserted alignment edges. Mask them,
   # retaining original proposals and independent review; never a negative fact.
   if a['state'] in ('NONE','INCOMPATIBLE'):
    for j in range(len(a['links'])):masks.add(uid+'::alignment'+str(j))
   status='KEEP' if a==prior and not any(l['action']!='KEEP' for l in ls) else 'UNKNOWN' if a['state']=='UNKNOWN' else 'CHANGE'
  except (AssertionError,KeyError,ValueError,TypeError) as e:
   a['scope']='UNKNOWN';a['state']='UNKNOWN';a['reason']='NO_VALID_COMPLETE_G_PATH_REVIEW: '+str(e)
   for l in a['links']:l['state']='UNKNOWN'
   status='REVIEW_NOT_COMPLETED'
  item={'case_id':source['case_id'],'unit_id':uid,'path':'G','version':'V11','status':status,'old_value':prior,'new_value':copy.deepcopy(a),'reason':a['reason'],'source_refs':[] if not r else r.get('case_refs',[]),'review':r,'scoped_masks':[k for k in sorted(masks) if k.startswith(uid+'::alignment')]};table.append(item)
  if a!=prior or item['scoped_masks']:changes.append(item)
 assert all(out[k]==proposal[k] for k in proposal if k!='alignments')
 assert [a for a in out['alignments'] if a['unit_id'] not in FAMILY]==[a for a in proposal['alignments'] if a['unit_id'] not in FAMILY]
 return out,sorted(masks),table,changes

def gate(cfg,labels,ltable,gtable,identity_ok=True,freeze_paths_isolated=True):
 ids=cfg['train']+cfg['dev'];positions={(c,u) for c in ids for u in FAMILY};allowed={'KEEP','CHANGE','UNKNOWN','ISOLATED','REVIEW_NOT_COMPLETED'}
 checks={'all132_L_status':len(ltable)==132 and {(str(x['case_id']),x['unit_id']) for x in ltable}==positions and all(x['status'] in allowed for x in ltable),'all132_G_status':len(gtable)==132 and {(str(x['case_id']),x['unit_id']) for x in gtable}==positions and all(x['status'] in allowed for x in gtable),'train_each_has_supervision':all(any(s['state']=='KNOWN' for s in labels[c]['slots'].values()) for c in cfg['train']),'dev_all180_status':all(len(labels[c]['slots'])==30 and all(s['state'] in ('KNOWN','UNKNOWN','ISOLATED','UNPROCESSED','REVIEW_NOT_COMPLETED') for s in labels[c]['slots'].values()) for c in cfg['dev']),'no_sealed_content':not set(ids)&set(cfg['sealed_ids']),'source_identity_and_no_new_target_text':identity_ok,'independent_paths':freeze_paths_isolated}
 return {'training_allowed':all(checks.values()),'checks':checks,'reference_role':'WEAK_MODEL_ASSISTED_NOT_HUMAN_GOLD','unresolved_not_in_loss':True,'not_zero_error_gate':True}
