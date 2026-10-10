#!/usr/bin/env python3
"""Deterministic CE tokenizer receipt; no weights loaded or model inference."""
import json,sys,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
def main():
 from transformers import AutoTokenizer
 root=Path('outputs/proof-semantic-interface-v13');input_root=Path(sys.argv[1]) if len(sys.argv)>1 else root/'inputs-v13-02';output=Path(sys.argv[2]) if len(sys.argv)>2 else root/'encoding/CE-fullcontext-tokenizer-receipt.json';tok=AutoTokenizer.from_pretrained('.runtime/proof-semantic-v12-model',local_files_only=True);rows=[];errors=[];t=time.monotonic()
 for path in input_root.glob('*/model-information-fullcontext.json'):
  case=path.parent.name;x=json.loads(path.read_text())
  for p in x['ce_pairs']:
   left=tok(p['left'],add_special_tokens=False,truncation=False)['input_ids'];right_text=p['right']+'\nSHARED SAME-CASE GRAPH INFORMATION:\n'+json.dumps(x['shared_case_context'],ensure_ascii=False,sort_keys=True);right=tok(right_text,add_special_tokens=False,truncation=False,return_offsets_mapping=True);ids=right['input_ids'];cap=8192-len(left)-tok.num_special_tokens_to_add(pair=True)
   if cap<1:errors.append({'key':case+'::'+p['id'],'error':'LEFT_FULL_PROPOSITION_EXCEEDS_CE_CONTEXT_NO_TRUNCATION'});continue
   windows=[{'token_range':[a,min(a+cap,len(ids))],'char_range':[right['offset_mapping'][a][0],right['offset_mapping'][min(a+cap,len(ids))-1][1]],'total_input_tokens':len(tok.build_inputs_with_special_tokens(left,ids[a:a+cap]))} for a in range(0,len(ids),cap)]
   rows.append({'key':case+'::'+p['id'],'left_tokens':len(left),'right_tokens':len(ids),'windows':windows,'left_repeated_whole':True,'right_all_token_positions_retained':sum(w['token_range'][1]-w['token_range'][0] for w in windows)==len(ids),'input_hash':hashlib.sha256((p['left']+right_text).encode()).hexdigest(),'weight_model_executed':False})
 out={'rows':rows,'failures':errors,'tokenizer':'.runtime/proof-semantic-v12-model','seconds':time.monotonic()-t,'no_model_pre_run':True,'scope':'Tokenizer-prepared actual complete pair windows, not evidence that a trained CE consumed these inputs','aggregation_if_training_gate_opens':'equal mean logits over all windows; keep original class loss and optimizer; no selected favorable windows'};output.write_text(json.dumps(out,indent=2));print(json.dumps({'pairs':len(rows),'failures':len(errors),'max_input_tokens':max((w['total_input_tokens'] for r in rows for w in r['windows']),default=0),'seconds':out['seconds']}))
if __name__=='__main__':main()
