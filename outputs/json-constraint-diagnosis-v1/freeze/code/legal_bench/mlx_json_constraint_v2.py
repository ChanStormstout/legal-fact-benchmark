"""Versioned correction for composite string-ending tokens in LMFE 0.11.2.

Keep the original character parser and fast cache; add exact tree traversal ONLY
for tokens containing a non-leading, non-trailing quote that the fast free-text
cache omits. No schema relaxation, forced delimiter or generated-text rewriting.
"""
from lmformatenforcer import TokenEnforcer,JsonSchemaParser
from lmformatenforcer.tokenizerprefixtree import TokenizerPrefixTreeNode
from legal_bench.mlx_json_constraint import tokenizer_data

class CompositeQuoteEnforcer(TokenEnforcer):
 def __init__(self,data,parser):
  self.composite_tree=TokenizerPrefixTreeNode();self.composite_count=0
  for tid,text,_ in data.regular_tokens:
   if text and not text.startswith('"') and '"' in text[:-1]:
    node=self.composite_tree
    for ch in text:node=node.children.setdefault(ch,TokenizerPrefixTreeNode())
    node.tokens.append(tid);self.composite_count+=1
  super().__init__(data,parser)
 def _collect_allowed_tokens(self,parser,tree_node,allowed_tokens,shortcut_key):
  super()._collect_allowed_tokens(parser,tree_node,allowed_tokens,shortcut_key)
  if isinstance(shortcut_key,tuple) and shortcut_key[0]=='json_freetext':
   # None disables the shortcut only on this small supplementary tree.
   super()._collect_allowed_tokens(parser,self.composite_tree,allowed_tokens,None)

class SchemaMask:
 def __init__(self,data,schema):
  self.enforcer=CompositeQuoteEnforcer(data,JsonSchemaParser(schema));self.calls=0;self.prefix_length=None;self.history=[]
 def __call__(self,tokens,logits):
  import mlx.core as mx
  ids=tokens.tolist()
  if self.prefix_length is None:self.prefix_length=len(ids)
  generated=ids[self.prefix_length:]
  allowed=self.enforcer.get_allowed_tokens(generated).allowed_tokens
  self.history.append({'call':self.calls,'processor_tokens':len(ids),'prefix_length':self.prefix_length,'generated_count':len(generated),'last_generated_id':generated[-1] if generated else None,'allowed_count':len(allowed)})
  if not allowed:raise ValueError('No valid constrained tokens; do not silently disable mask')
  if any(i>=logits.shape[-1] or i<0 for i in allowed):raise ValueError('Tokenizer/model vocabulary mismatch')
  mask=mx.full((logits.shape[-1],),float('-inf'),dtype=logits.dtype);mask[mx.array(allowed)]=0;self.calls+=1
  return logits+mask
