"""MLX token-mask adapter for pinned LM Format Enforcer; no PyTorch needed."""
def tokenizer_data(tokenizer,eos_ids):
    from lmformatenforcer import TokenEnforcerTokenizerData
    zero=tokenizer.encode('0',add_special_tokens=False)[-1];special=set(tokenizer.all_special_ids);regular=[]
    for tid in range(len(tokenizer)):
        if tid in special:continue
        after=tokenizer.decode([zero,tid],clean_up_tokenization_spaces=False)[1:]
        alone=tokenizer.decode([tid],clean_up_tokenization_spaces=False)
        regular.append((tid,after,len(after)>len(alone)))
    def decode(ids):return tokenizer.decode(ids,clean_up_tokenization_spaces=False).rstrip('\ufffd')
    return TokenEnforcerTokenizerData(regular,decode,eos_ids,False,len(tokenizer))

class SchemaMask:
    def __init__(self,data,schema):
        from lmformatenforcer import TokenEnforcer,JsonSchemaParser
        self.enforcer=TokenEnforcer(data,JsonSchemaParser(schema));self.calls=0;self.prefix_length=None
    def __call__(self,tokens,logits):
        import mlx.core as mx
        ids=tokens.tolist()
        if self.prefix_length is None:self.prefix_length=len(ids)
        generated=ids[self.prefix_length:]
        allowed=self.enforcer.get_allowed_tokens(generated).allowed_tokens
        if not allowed:raise ValueError('No valid constrained tokens; do not silently disable mask')
        if any(i>=logits.shape[-1] for i in allowed):raise ValueError('Tokenizer/model vocabulary mismatch')
        mask=mx.full((logits.shape[-1],),float('-inf'),dtype=logits.dtype)
        mask[mx.array(allowed)]=0
        self.calls+=1
        return logits+mask
