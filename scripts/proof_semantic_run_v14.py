#!/usr/bin/env python3
"""Bounded local calibration entry. No web, model, labels or training imports."""
import sys, json, hashlib, time, subprocess, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_search_v12 import complete_search


def save(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        raise FileExistsError(p)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def run(snapshot, candidates, requests, policy, dest):
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError(dest)
    dest.mkdir(parents=True)
    start = time.perf_counter()
    try:
        search = complete_search(candidates, snapshot["rules"], requests, snapshot["contracts"])
        files = {"snapshot": snapshot, "search": search, "policy": policy}
        for name, data in files.items():
            save(dest / (name + ".json"), data)
        save(dest / "manifest.json", {name + "_sha256": hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest() for name, data in files.items()})
        p = subprocess.run([sys.executable, "scripts/check_semantic_v14.py", str(dest)], capture_output=True, text=True, timeout=120)
        (dest / "checker.stdout.txt").write_text(p.stdout)
        (dest / "checker.stderr.txt").write_text(p.stderr)
        if p.returncode:
            raise RuntimeError(p.stderr)
        checked = json.loads(p.stdout)
        save(dest / "checked.json", checked)
        save(dest / "run.json", {"status": "OK", "seconds": time.perf_counter() - start, "technical_answer": checked["requests"], "formal_legal_approval": False})
        return checked
    except Exception as e:
        save(dest / "failure.json", {"status": "TECHNICAL_FAILURE", "answer": None, "error": repr(e), "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    for name in ("snapshot", "candidates", "requests", "policy", "out"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    read = lambda path: json.loads(Path(path).read_text())
    run(read(a.snapshot), read(a.candidates), read(a.requests), read(a.policy), a.out)
