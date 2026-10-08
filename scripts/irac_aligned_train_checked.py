#!/usr/bin/env python3
"""Artifact-safe entry for a FUTURE explicitly authorized round, not a v1 rerun.

The frozen v1 entry remains byte-identical. This wrapper prevents the observed
missing-output-directory failure and refuses the consumed v1 fit budget.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_artifact_io import preflight
from legal_bench.irac_application.aligned_tasks import ROOT
from scripts.irac_aligned_train import main
if __name__=='__main__':
    if list((ROOT/'training').glob('*-seed*.json')):
        raise SystemExit('Existing attempted fits preserved. No rerun is authorized by this entry; use a separately registered future round.')
    preflight(ROOT)
    main()
