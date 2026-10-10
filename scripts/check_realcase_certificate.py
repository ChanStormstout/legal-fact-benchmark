"""Separate process and independent evaluator for real-case research traces."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.realcase_checker import check_file
def main():
    p=argparse.ArgumentParser();p.add_argument('certificate');p.add_argument('--manifest',required=True);p.add_argument('--current')
    a=p.parse_args()
    try:result=check_file(a.certificate,a.manifest,a.current)
    except Exception as exc:result={'status':'TECHNICAL_OR_CONTRACT_FAILURE','answer':None,'reason':str(exc),'legal_approval':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
