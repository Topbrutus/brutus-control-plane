import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from z_stereo_formula_adapters import (
    F1_SOURCE_COMMIT,
    F1_SOURCE_PATH,
    F1_SOURCE_REPO,
    f1_pell_rank_21_power,
)


class F1AdapterTests(unittest.TestCase):
    def test_known_values_k2_to_k8(self):
        expected = {
            2: 84,
            3: 1764,
            4: 37044,
            5: 777924,
            6: 16336404,
            7: 343064484,
            8: 7204354164,
        }
        for k, rank in expected.items():
            with self.subTest(k=k):
                result = f1_pell_rank_21_power(k)
                self.assertEqual(result.kind, "pell_rank_integer")
                self.assertEqual(result.value, rank)

    def test_k3_is_square_rank_case(self):
        result = f1_pell_rank_21_power(3)
        self.assertEqual(result.value, 42 * 42)

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            f1_pell_rank_21_power(1)
        with self.assertRaises(TypeError):
            f1_pell_rank_21_power(2.0)
        with self.assertRaises(TypeError):
            f1_pell_rank_21_power(True)

    def test_provenance_matches_formula_registry(self):
        registry = json.loads(
            (ROOT / "registry" / "z-stereo-formula-bank-v0.1.json").read_text(encoding="utf-8")
        )
        f1 = next(slot for slot in registry["slots"] if slot["slot"] == "F1")
        self.assertEqual(F1_SOURCE_REPO, f1["source_repo"])
        self.assertEqual(F1_SOURCE_COMMIT, f1["source_commit"])
        self.assertEqual(F1_SOURCE_PATH, f1["source_path"])


if __name__ == "__main__":
    unittest.main()
