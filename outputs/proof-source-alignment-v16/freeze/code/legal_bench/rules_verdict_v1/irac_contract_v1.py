"""No-dependency validation of the JSON Schema vocabulary used by our contracts.
This checks structure/address only; it is not an upstream semantic validator.
"""
import re

def validate(value,schema,root=None,path='$'):
 root=root or schema;err=[]
 if '$ref' in schema:
  part=root
  for key in schema['$ref'].split('/')[1:]:part=part[key]
  err+=validate(value,part,root,path)
 if 'const' in schema and value!=schema['const']:err.append(path+':CONST')
 if 'enum' in schema and value not in schema['enum']:err.append(path+':ENUM')
 types=schema.get('type',[]);types=[types] if isinstance(types,str) else types
 def istype(t):return {'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),'null':value is None,'integer':isinstance(value,int) and not isinstance(value,bool),'number':isinstance(value,(int,float)) and not isinstance(value,bool),'boolean':isinstance(value,bool)}[t]
 if types and not any(istype(t) for t in types):return err+[path+':TYPE']
 if isinstance(value,dict):
  for k in schema.get('required',[]):
   if k not in value:err.append(path+'.'+k+':MISSING')
  props=schema.get('properties',{})
  for k,v in value.items():
   if k in props:err+=validate(v,props[k],root,path+'.'+k)
   elif schema.get('additionalProperties') is False:err.append(path+'.'+k+':EXTRA')
 if isinstance(value,list):
  if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',float('inf')):err.append(path+':ITEM_COUNT')
  if schema.get('uniqueItems') and any(value[i]==value[j] for i in range(len(value)) for j in range(i)):err.append(path+':DUPLICATE')
  if 'items' in schema:
   for i,v in enumerate(value):err+=validate(v,schema['items'],root,path+f'[{i}]')
 if isinstance(value,str):
  if len(value)<schema.get('minLength',0) or len(value)>schema.get('maxLength',float('inf')):err.append(path+':LENGTH')
  if 'pattern' in schema and not re.search(schema['pattern'],value):err.append(path+':PATTERN')
 for part in schema.get('allOf',[]):err+=validate(value,part,root,path)
 if 'oneOf' in schema and sum(not validate(value,p,root,path) for p in schema['oneOf'])!=1:err.append(path+':ONE_OF')
 if 'if' in schema:
  branch='else' if validate(value,schema['if'],root,path) else 'then'
  if branch in schema:err+=validate(value,schema[branch],root,path)
 return err
