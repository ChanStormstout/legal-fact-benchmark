#!/usr/bin/env python3
"""Independent checker process: only hash-pinned untrusted input snapshot and search."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_checker_v13 import check
p=Path(sys.argv[1]);load=lambda n:json.loads((p/n).read_text());s=load('snapshot.json');r=load('search.json');m=load('manifest.json')
for k,x in [('snapshot',s),('search',r)]:
 assert hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()==m[k+'_sha256'], k+' hash mismatch'
print(json.dumps(check(s,r),ensure_ascii=False))
