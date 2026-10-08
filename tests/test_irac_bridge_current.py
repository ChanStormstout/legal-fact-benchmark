import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import scripts.repository_bridge as b
class CurrentBridge(unittest.TestCase):
 def test_generic_current_no_old_scoring_dependency(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)
   for p,text in [('docs/EXPERIMENTS.json',json.dumps({'experiments':[{'id':'v2','role':'dev','report':'outputs/new/report.txt','note':'n'}]})),('outputs/new/report.txt','current'),('README.md','outputs/new/report.txt')]:
    q=r/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text)
   for name in b.GENERATED:
    q=r/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('old review')
   policy={'current_review':{'contract_version':2,'title':'new','summary':'summary','report':'outputs/new/report.txt'},'repository':'test/repo','branch':'test','code_review_files':[],'artifact_roots':['outputs/new'],'extra_artifacts':[]}
   with patch.object(b,'publication_paths',return_value=(['README.md'],[])),patch.object(b,'scan'),patch.object(b,'verify',return_value={'ok':True}):
    b.prepare_current(r,policy)
   s=json.loads((r/'docs/PROJECT_STATE.json').read_text());self.assertEqual(s['active_research_run'],'outputs/new');self.assertIn('outputs/new/report.txt',(r/'review/START_HERE.md').read_text())
if __name__=='__main__':unittest.main()
