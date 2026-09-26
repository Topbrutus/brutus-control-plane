from fractions import Fraction
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from z_stereo_ninefold import (
    fanout3,
    mirror4,
    recombine3,
    recombine4,
    run_topology,
)


class ZStereoNinefoldTests(unittest.TestCase):
    def test_local_1_to_3_roundtrip_is_exact(self):
        x = Fraction(17, 5)
        self.assertEqual(recombine3(fanout3(x, Fraction(2, 7))), x)

    def test_local_mirror_1_to_4_roundtrip_is_exact(self):
        x = Fraction(17, 5)
        self.assertEqual(recombine4(mirror4(x, Fraction(3, 11))), x)

    def test_full_identity_topology_returns_exact_input(self):
        result = run_topology(Fraction(17, 5))
        self.assertEqual(result["global_error"], 0)
        self.assertTrue(result["identity_route"])
        self.assertEqual(result["local_errors"], (Fraction(0),) * 9)
        self.assertEqual(result["trace_points"], 62)

    def test_trace_is_deterministic(self):
        a = run_topology(Fraction(17, 5))
        b = run_topology(Fraction(17, 5))
        self.assertEqual(a["trace_hash"], b["trace_hash"])

    def test_controlled_cross_route_is_detected(self):
        baseline = run_topology(Fraction(17, 5))
        crossed = run_topology(Fraction(17, 5), route=(0, 2, 1, 3))
        self.assertEqual(baseline["global_error"], 0)
        self.assertNotEqual(crossed["global_error"], 0)
        self.assertNotEqual(crossed["local_errors"], (Fraction(0),) * 9)


if __name__ == "__main__":
    unittest.main()
