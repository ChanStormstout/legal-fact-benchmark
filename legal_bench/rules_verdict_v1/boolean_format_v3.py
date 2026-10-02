"""Narrow lexical repair of Python boolean spelling outside JSON strings."""
import json


def parse_boolean_literals(raw):
    output=[];repairs=[];i=0;quoted=False;escaped=False
    while i<len(raw):
        c=raw[i]
        if quoted:
            output.append(c)
            if escaped: escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
            i+=1;continue
        if c=='"':quoted=True;output.append(c);i+=1;continue
        found=False
        for before,after in [('True','true'),('False','false')]:
            if raw.startswith(before,i) and (i==0 or raw[i-1] in ' \t\r\n[:,') and (i+len(before)==len(raw) or raw[i+len(before)] in ' \t\r\n,}]'):
                output.append(after);repairs.append({'offset':i,'before':before,'after':after,
                    'reason':'JSON_BOOLEAN_LITERAL_CASE_ONLY_OUTSIDE_STRINGS'})
                i+=len(before);found=True;break
        if not found:output.append(c);i+=1
    normalized=''.join(output)
    # No partial objects, control-character rewriting or guessed missing values.
    return json.loads(normalized),repairs,normalized
