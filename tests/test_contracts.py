import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import brutus_control_plane as bcp

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'examples' / 'job.example.json').read_text(encoding='utf-8'))

    def test_example_manifest_is_valid(self):
        self.assertEqual(bcp.validate_manifest(self.manifest), [])

    def test_fingerprint_is_deterministic(self):
        a = bcp.fingerprint(self.manifest)
        b = bcp.fingerprint(json.loads(json.dumps(self.manifest)))
        self.assertEqual(a, b)

    def test_status_skip_is_blocked(self):
        ok, missing = bcp.check_transition(self.manifest, 'VERIFIED')
        self.assertFalse(ok)
        self.assertIn('status_skip_forbidden', missing)

    def test_candidate_requires_evidence(self):
        ok, missing = bcp.check_transition(self.manifest, 'CANDIDATE')
        self.assertFalse(ok)
        self.assertEqual(set(missing), {'source_commit', 'input_hash', 'primary_result'})

    def test_event_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'events.jsonl'
            e1 = bcp.append_event({'event':'PASS','run_id':'R1','source_commit':'abc1234'}, path)
            e2 = bcp.append_event({'event':'FAIL','run_id':'R1','source_commit':'abc1234'}, path)
            self.assertIsNone(e1['previous_event_hash'])
            self.assertEqual(e2['previous_event_hash'], e1['event_hash'])
            self.assertNotEqual(e1['event_hash'], e2['event_hash'])

if __name__ == '__main__':
    unittest.main()
