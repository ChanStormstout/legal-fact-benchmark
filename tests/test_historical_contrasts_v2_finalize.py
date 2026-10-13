import hashlib, tempfile, unittest
from pathlib import Path
from legal_bench.historical_contrasts_v1.contracts import ContractError
from scripts.historical_contrasts_v2_finalize import preservation

class FinalizationGuards(unittest.TestCase):
    def test_shared_entry_change_is_reported_without_revert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'README.md';p.write_text('new shared review')
            old={'README.md':hashlib.sha256(b'previous shared review').hexdigest()}
            audit=preservation(root,old)
            self.assertEqual([x['path'] for x in audit['concurrent_shared_metadata_changes']],['README.md'])
            self.assertEqual(p.read_text(),'new shared review')
    def test_source_change_still_blocks_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'source.json';p.write_text('changed source')
            with self.assertRaisesRegex(ContractError,'SOURCE_OR_OLD_MODULE_CHANGED'):
                preservation(root,{'source.json':hashlib.sha256(b'original source').hexdigest()})

if __name__=='__main__':unittest.main()
