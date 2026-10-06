"""Content-preserving evidence location; all occurrences retained, no fuzzy matching."""
import re
from .legal_rule_support_study import normalize_whitespace

def locate_all(text, quote):
 if not isinstance(quote,str) or not quote.strip():return {'status':'EMPTY_QUOTE','matches':[],'semantic_support_certified':False}
 exact=list(re.finditer(re.escape(quote),text))
 if exact:
  return {'status':'EXACT','matches':[{'raw_start':m.start(),'raw_end':m.end()} for m in exact], 'unique':len(exact)==1,'semantic_support_certified':False}
 norm,mapping=normalize_whitespace(text);needle,_=normalize_whitespace(quote)
 matches=[]
 for m in re.finditer(re.escape(needle),norm):
  a,b=m.span();matches.append({'raw_start':mapping[a][0],'raw_end':mapping[b-1][1], 'normalized_start':a,'normalized_end':b,'normalized_to_original_spans':mapping[a:b]})
 return {'status':'WHITESPACE_ONLY' if matches else 'UNLOCATED','matches':matches,'unique':len(matches)==1,'semantic_support_certified':False}

def quote_supported_address(quote,text):
 return locate_all(text,quote)['status'] in ('EXACT','WHITESPACE_ONLY')
