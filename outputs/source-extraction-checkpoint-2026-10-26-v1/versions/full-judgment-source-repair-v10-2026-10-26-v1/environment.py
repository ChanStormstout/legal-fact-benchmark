"""Read-only dependencies; importing this module never constructs a model client."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = Path('/Users/victor/Documents/Codex/2026-09-28/files-mentioned-by-the-user-canonicalizing')
V9 = HERE.parent / 'full-judgment-source-repair-v9-2026-10-25-v1'
V8 = HERE.parent / 'full-judgment-source-repair-v8-2026-10-25-v1'
PREP = HERE.parent / 'full-judgment-extraction-comparison-preparation-2026-10-25-v1'
V7 = REPO / 'outputs/rapido-role-extraction-experiment-v7-2026-10-25'
V25 = REPO / 'outputs/rapido-ontology-source-v25-2026-10-25-v1'
sys.path[:0] = [str(HERE), str(V9), str(V8), str(V7), str(V25 / 'src'), str(REPO)]
