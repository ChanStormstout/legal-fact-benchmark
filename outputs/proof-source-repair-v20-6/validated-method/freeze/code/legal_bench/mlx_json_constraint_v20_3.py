"""Shared source table first, backward C references, and viable unique SRC enums."""
import json
from legal_bench.mlx_json_constraint_v19_6 import UniqueStringParser
from legal_bench.mlx_json_constraint_v20_1 import ViableUniqueEnumParser, SchemaMask as PreviousMask
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer


class SharedSourceParser(ViableUniqueEnumParser):
    def __init__(self,schema,delegate=None,stack=(),string=None,escaped=False,config=None,groups=(),table_closed=False):
        super().__init__(schema,delegate,stack,string,escaped,config)
        self.groups=groups;self.table_closed=table_closed

    def restricted_literals(self):
        if self.string and self.string['key']:
            if len(self.stack)==1 and not self.table_closed:
                return {'"source_sets"'}
            return None
        path=self.value_path()
        if path and path[-1] in ('ref_set','source_set'):
            choices={'C'+str(i+1) for i in range(len(self.groups))}
            if self.spec(path).get('description')=='EMPTY_SOURCE_SET_ALLOWED':choices.add('C0')
            return {json.dumps(c) for c in choices}
        return None

    def get_allowed_characters(self):
        chars=super().get_allowed_characters();literals=self.restricted_literals()
        if self.string is None and self.stack and len(self.stack[-1]['path'])==2 and self.stack[-1]['path'][0]=='source_sets' and tuple(self.stack[-1].get('group_values',())) in self.groups:
            chars=chars.replace(']','')
        if literals is None:return chars
        if self.string is None and '"' not in chars:return chars
        prefix=self.string['raw'] if self.string else ''
        next_chars={s[len(prefix)] for s in literals if s.startswith(prefix) and len(s)>len(prefix)}
        return ''.join(c for c in chars if c in next_chars or (not self.string and c.isspace()))

    def shortcut_key(self):
        if self.restricted_literals() is not None or not self.table_closed:return None
        return super().shortcut_key()

    def add_character(self,char):
        closing_group=char==']' and self.string is None and self.stack and len(self.stack[-1]['path'])==2 and self.stack[-1]['path'][0]=='source_sets'
        closing_table=char==']' and self.string is None and self.stack and self.stack[-1]['path']==('source_sets',)
        completed_source=None
        if char=='"' and self.string and not self.string['key'] and not self.escaped and self.stack and len(self.stack[-1]['path'])==2 and self.stack[-1]['path'][0]=='source_sets':
            completed_source=json.loads(self.string['raw']+'"')
        # The base clone is intentionally reconstructed with our persistent table state.
        state=UniqueStringParser.add_character(self,char)
        stack=list(state.stack);groups=self.groups
        if completed_source is not None:
            stack[-1]=dict(stack[-1]);stack[-1]['group_values']=tuple(stack[-1].get('group_values',()))+(completed_source,)
        if closing_group:
            group=tuple(self.stack[-1].get('group_values',()))
            if group in groups:raise ValueError('DUPLICATE_SHARED_SOURCE_DEFINITION')
            groups=groups+(group,)
        return type(self)(state.schema,state.delegate,tuple(stack),state.string,state.escaped,state.config,groups,self.table_closed or closing_table)


class SchemaMask(PreviousMask):
    def __init__(self,data,schema):
        self.enforcer=CompositeQuoteEnforcer(data,SharedSourceParser(schema))
        self.calls=0;self.prefix_length=None;self.history=[]
