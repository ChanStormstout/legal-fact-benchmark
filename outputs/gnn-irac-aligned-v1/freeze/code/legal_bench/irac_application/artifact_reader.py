"""Extract data literals from visible file-generation code; NEVER execute that code.
Only literal containers, existing variable references, indexing, list concatenation
and the displayed q(doc,line,quote) address constructor are interpreted. Unknown
expressions affecting payloads fail; no quote rewriting or semantic repairs.
"""
import ast,json,copy
class Unsupported(ValueError):pass

def recover(codes,source_lookup=None,initial_payload=None):
    env={} if initial_payload is None else {'d':copy.deepcopy(initial_payload)};audit=[];payload_names=set(env);source_lookup=source_lookup or {}
    def value(n):
        if isinstance(n,ast.Constant):return n.value
        if isinstance(n,ast.Name):
            if n.id not in env:raise Unsupported('NAME:'+n.id)
            return env[n.id]
        if isinstance(n,(ast.List,ast.Tuple)):return [value(v) for v in n.elts]
        if isinstance(n,ast.Dict):
            d={}
            for k,v in zip(n.keys,n.values):
                if k is None:d.update(value(v))
                else:d[value(k)]=value(v)
            return d
        if isinstance(n,ast.Subscript):return value(n.value)[value(n.slice)]
        if isinstance(n,ast.Slice):return slice(value(n.lower) if n.lower else None,value(n.upper) if n.upper else None,value(n.step) if n.step else None)
        if isinstance(n,ast.Index):return value(n.value)
        if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Add):return value(n.left)+value(n.right)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='q':
            args=[value(a) for a in n.args]
            if len(args)!=3 or not isinstance(args[2],str):raise Unsupported('Q_INTERFACE')
            sid='IK-'+str(args[0])+':L'+str(args[1]);quote=args[2]
            if sid not in source_lookup or quote not in source_lookup[sid]:raise Unsupported('Q_UNSUPPORTED_BY_SOURCE:'+sid)
            return dict(source_id=sid,quote=quote)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'ref','span'}:
            args=[value(a) for a in n.args];kw={k.arg:value(k.value) for k in n.keywords}
            if len(args)<2 or args[0] not in source_lookup or args[1] not in source_lookup[args[0]]:raise Unsupported('ADDRESS_NOT_LOCATED')
            if n.func.id=='ref' and len(args)==2 and not kw:return dict(source_id=args[0],quote=args[1])
            if n.func.id=='span' and 4<=len(args)<=6:
                return dict(source_id=args[0],quote=args[1],statement_status=args[2],reason=args[3],semantic_stage=kw.get('semantic_stage',args[4] if len(args)>4 else 'PRE_TARGET_RECORD'),court_level=kw.get('court_level',args[5] if len(args)>5 else 'NONE'))
            raise Unsupported('ADDRESS_INTERFACE')
        if isinstance(n,ast.Compare) and len(n.ops)==1 and isinstance(n.ops[0],ast.Eq):return value(n.left)==value(n.comparators[0])
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='next' and len(n.args)==1 and isinstance(n.args[0],ast.GeneratorExp):
            g=n.args[0]
            if len(g.generators)!=1:raise Unsupported('MULTIPLE_GENERATORS')
            gen=g.generators[0]
            for item in value(gen.iter):
                assign(gen.target,item)
                if all(value(c) for c in gen.ifs):return value(g.elt)
            raise Unsupported('NO_GENERATOR_MATCH')
        raise Unsupported(type(n).__name__)
    def assign(t,v):
        if isinstance(t,ast.Name):env[t.id]=v
        elif isinstance(t,ast.Subscript):value(t.value)[value(t.slice)]=v
        else:raise Unsupported('ASSIGN:'+type(t).__name__)
    def mutate_body(body):
        for n in body:
            if isinstance(n,ast.Assign):
                v=value(n.value)
                for t in n.targets:assign(t,v)
            elif isinstance(n,ast.For):
                seq=value(n.iter)
                if not isinstance(seq,list) or len(seq)>1000:raise Unsupported('LOOP_BOUND')
                for item in seq:
                    assign(n.target,item);mutate_body(n.body)
            elif isinstance(n,ast.If):mutate_body(n.body if value(n.test) else n.orelse)
            elif isinstance(n,ast.Expr) and isinstance(n.value,ast.Call):
                c=n.value
                if isinstance(c.func,ast.Attribute) and c.func.attr=='append':value(c.func.value).append(value(c.args[0]))
                else:raise Unsupported('MUTATION_CALL')
            else:raise Unsupported('MUTATION_STATEMENT')
    for block,code in enumerate(codes):
        try:tree=ast.parse(code)
        except SyntaxError:
            audit.append(dict(block=block,action='UNPARSEABLE_BLOCK_NOT_EXECUTED'));continue
        for n in tree.body:
            if isinstance(n,ast.Assign):
                try:
                    v=value(n.value)
                    for t in n.targets:assign(t,v)
                    audit.append(dict(block=block,line=n.lineno,action='STATIC_DATA_ASSIGN'))
                except Unsupported as e:
                    # Payload mutation may not be silently discarded.
                    if any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id in payload_names for t in n.targets):raise
            elif isinstance(n,ast.For) and initial_payload is not None:
                assigns=[x for x in ast.walk(n) if isinstance(x,ast.Assign)]
                if assigns and not any(isinstance(x,ast.Assert) for x in ast.walk(n)):
                    mutate_body([n]);audit.append(dict(block=block,line=n.lineno,action='BOUNDED_LITERAL_MUTATION'))
            elif isinstance(n,ast.Expr) and isinstance(n.value,ast.Call):
                call=n.value
                if isinstance(call.func,ast.Attribute) and call.func.attr=='append' and isinstance(call.func.value,ast.Name) and call.func.value.id in env:
                    try:
                        v=value(call.args[0]);env[call.func.value.id].append(v);audit.append(dict(block=block,line=n.lineno,action='STATIC_DATA_APPEND'))
                    except Unsupported:raise
            for key,v in env.items():
                if isinstance(v,dict) and ('template_id' in v or isinstance(v.get('templates'),list) and v['templates'] or isinstance(v.get('cases'),list) and v['cases']):payload_names.add(key)
    valid=[v for k,v in env.items() if k in payload_names and isinstance(v,dict) and ('template_id' in v or isinstance(v.get('templates'),list) and v['templates'] or isinstance(v.get('cases'),list) and v['cases'])]
    if not valid:raise Unsupported('NO_RECOVERABLE_COMPLETE_PAYLOAD')
    return copy.deepcopy(valid[-1]),audit
