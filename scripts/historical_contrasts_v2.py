"""Authorized independent training; no parent queue, external publication or repairs."""
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.runtime/historical-contrasts-v1/site'));sys.path.insert(0,str(ROOT))
OUT=ROOT/'outputs/historical-contrasts-v2'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['assemble','train']);a=p.parse_args()
    if a.mode=='assemble':
        from legal_bench.historical_contrasts_v2.data import assemble
        import json
        print(json.dumps(assemble(OUT)[1],ensure_ascii=False,indent=2))
    else:
        from legal_bench.historical_contrasts_v2.train import experiment
        experiment(ROOT,OUT)
