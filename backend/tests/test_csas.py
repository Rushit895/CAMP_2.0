"""Unit tests for the CSAS engine — pure stdlib unittest, no install required.

Run:  python -m unittest discover -s tests   (from backend/)
"""
from __future__ import annotations

import unittest

from app.core.config import DEFAULT_CONFIG, CSASConfig
from app.engine.bloom import bloom_gate, smoothstep
from app.engine.csas import score_co, score_matrix
from app.engine.lexicon import load_program_outcomes
from app.engine.preprocess import detect_bloom_level, preprocess_co, tokenize


class PreprocessTests(unittest.TestCase):
    def test_stemming_folds_inflections(self):
        self.assertEqual(tokenize("analyzing analyzed analyses"),
                         ["analyz", "analyz", "analys"])

    def test_stopwords_removed(self):
        self.assertNotIn("the", tokenize("the student will use the tool"))

    def test_bloom_detects_highest_verb(self):
        # "apply" (3) and "analyze" (4) present -> take the higher
        pco = preprocess_co("Apply methods to analyze systems")
        self.assertEqual(pco.bloom_level, 4)

    def test_bloom_defaults_to_apply(self):
        self.assertEqual(detect_bloom_level(tokenize("database concepts terminology")), 3)


class BloomGateTests(unittest.TestCase):
    def test_smoothstep_endpoints(self):
        self.assertEqual(smoothstep(0.0), 0.0)
        self.assertEqual(smoothstep(1.0), 1.0)
        self.assertAlmostEqual(smoothstep(0.5), 0.5)

    def test_professional_tier_is_bloom_neutral(self):
        for b in range(1, 7):
            self.assertEqual(bloom_gate("professional", b, DEFAULT_CONFIG), 1.0)

    def test_higher_order_gate_is_monotonic_in_bloom(self):
        gates = [bloom_gate("higher_order", b, DEFAULT_CONFIG) for b in range(1, 7)]
        self.assertEqual(gates, sorted(gates))
        self.assertLess(gates[0], gates[-1])

    def test_knowledge_tier_has_floor(self):
        self.assertGreaterEqual(bloom_gate("knowledge", 1, DEFAULT_CONFIG), 0.5)

    def test_unknown_tier_raises(self):
        with self.assertRaises(ValueError):
            bloom_gate("nonsense", 3, DEFAULT_CONFIG)

    def test_gate_floor_lifts_low_gates(self):
        floored = CSASConfig(gate_floor=0.5)
        # a Bloom-1 higher-order gate is ~0 by default; the floor lifts it to >= 0.5
        strict = bloom_gate("higher_order", 1, DEFAULT_CONFIG)
        lifted = bloom_gate("higher_order", 1, floored)
        self.assertLess(strict, 0.1)
        self.assertGreaterEqual(lifted, 0.5)
        # floor never exceeds 1.0 even for professional tier
        self.assertEqual(bloom_gate("professional", 3, floored), 1.0)

    def test_gate_floor_default_is_noop(self):
        for tier in ("knowledge", "higher_order", "application"):
            for b in range(1, 7):
                self.assertAlmostEqual(
                    bloom_gate(tier, b, DEFAULT_CONFIG),
                    bloom_gate(tier, b, CSASConfig(gate_floor=0.0)))


class DeterminismTests(unittest.TestCase):
    def test_same_input_same_output(self):
        co = "Design and develop a software system using modern engineering tools."
        a = score_co(co).to_dict()
        b = score_co(co).to_dict()
        self.assertEqual(a, b)

    def test_levels_in_range(self):
        rows = score_matrix([
            "Apply data structures to solve problems.",
            "Evaluate environmental sustainability of solutions.",
        ])
        for row in rows:
            for cell in row.cells:
                self.assertIn(cell.level, (0, 1, 2, 3))
                self.assertGreaterEqual(cell.raw, 0.0)


class KnownMappingTests(unittest.TestCase):
    """Anchor a few mappings a human evaluator would agree with."""

    def _level(self, co: str, po: str) -> int:
        row = score_co(co)
        return {c.po: c.level for c in row.cells}[po]

    def test_design_co_maps_strongly_to_po3(self):
        self.assertGreaterEqual(
            self._level("Design and develop a software system using modern tools.", "PO3"), 2)

    def test_ethics_co_maps_strongly_to_po8(self):
        self.assertGreaterEqual(
            self._level("Understand the ethical and professional responsibilities of an engineer.", "PO8"), 2)

    def test_communication_co_maps_to_po10(self):
        self.assertGreaterEqual(
            self._level("Communicate results through reports and presentations.", "PO10"), 2)

    def test_apply_co_does_not_spuriously_hit_design(self):
        # a low-Bloom knowledge CO should be gated out of PO3 (design)
        self.assertEqual(
            self._level("Define the basic concepts and terminology of databases.", "PO3"), 0)

    def test_every_co_maps_to_at_least_one_po(self):
        cos = [
            "Apply data structures and algorithms to solve computational problems.",
            "Analyze the time complexity of algorithms.",
            "Work effectively in a multidisciplinary team.",
        ]
        for row in score_matrix(cos):
            self.assertTrue(any(c.level > 0 for c in row.cells),
                            f"CO mapped to nothing: {row.co_text!r}")


class ConfigTests(unittest.TestCase):
    def test_default_config_valid(self):
        DEFAULT_CONFIG.validate()

    def test_bad_thresholds_rejected(self):
        with self.assertRaises(AssertionError):
            CSASConfig(tau1=0.5, tau2=0.3, tau3=0.4).validate()

    def test_weights_must_sum_to_one(self):
        with self.assertRaises(AssertionError):
            CSASConfig(semantic_weight=0.7, lexical_weight=0.7).validate()


class DataIntegrityTests(unittest.TestCase):
    def test_twelve_pos_loaded(self):
        self.assertEqual(len(load_program_outcomes()), 12)

    def test_every_po_has_lexicon(self):
        for po in load_program_outcomes():
            self.assertTrue(po.lexicon, f"{po.id} has empty lexicon")


if __name__ == "__main__":
    unittest.main(verbosity=2)
