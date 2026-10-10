#!/usr/bin/env python3
"""Independent, manifest-pinned V14 receipt/check process."""
import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_checker_v14 import check

if __name__ == "__main__":
    p = Path(sys.argv[1])
    load = lambda n: json.loads((p / n).read_text())
    snapshot, search, policy, manifest = [load(n) for n in ("snapshot.json", "search.json", "policy.json", "manifest.json")]
    for name, value in (("snapshot", snapshot), ("search", search), ("policy", policy)):
        if hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest() != manifest[name + "_sha256"]:
            raise ValueError(name + " hash mismatch")
    print(json.dumps(check(snapshot, search, policy), ensure_ascii=False))
