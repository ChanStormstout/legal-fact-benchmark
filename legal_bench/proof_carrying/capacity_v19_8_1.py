"""Count the actual token IDs, never the number of BatchEncoding fields."""
from collections.abc import Mapping
VERSION='V19_8_CAPACITY_2'
def token_ids(value):
    if isinstance(value,Mapping):
        if 'input_ids' not in value:raise ValueError('TOKENIZER_INPUT_IDS_MISSING')
        value=value['input_ids']
    if hasattr(value,'tolist'):value=value.tolist()
    if isinstance(value,list) and len(value)==1 and isinstance(value[0],list):value=value[0]
    if not isinstance(value,list) or not value or any(type(v) is not int or v<0 for v in value):raise ValueError('TOKENIZER_ID_SHAPE')
    return value

def capacity(value,tokenizer,config):
    encoded=tokenizer.apply_chat_template([{'role':'user','content':value['prompt']}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
    ids=token_ids(encoded);required=len(ids)+config['max_output_tokens']+config['template_margin']
    return {'version':VERSION,'input_tokens':len(ids),'reserved_output_tokens':config['max_output_tokens'],
            'template_margin':config['template_margin'],'required_context':required,'context_budget':config['context_budget'],
            'fits':required<=config['context_budget'],'no_truncation':True,'model_loaded':False}
