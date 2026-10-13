"""Same V19_8 processing; explicit post-replay capacity/delivery correction."""
from scripts.proof_pipeline_contract_v19_8 import *

def final_run(*args,**kwargs):
    from legal_bench.proof_carrying.final_delivery_v19_8_1 import run
    return run(*args,**kwargs)
