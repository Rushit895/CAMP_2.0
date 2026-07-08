"""Tests for the calibration harness. Stdlib unittest."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.calibration.harness import (
    LabeledCO,
    evaluate,
    grid_search,
    load_dataset,
)
from app.engine.csas import score_co

_SAMPLE = Path(__file__).resolve().parent.parent / "calibration" / "sample_labels.json"


def _labels_from_engine(cos: list[str]) -> list[LabeledCO]:
    """Build labels that exactly match what CSAS predicts -> should score 100%."""
    out = []
    for co in cos:
        row = score_co(co)
        expected = {c.po: c.level for c in row.cells if c.level > 0}
        out.append(LabeledCO(co=co, expected=expected))
    return out


class DatasetTests(unittest.TestCase):
    def test_loads_sample(self):
        ds = load_dataset(_SAMPLE)
        self.assertEqual(len(ds), 8)
        self.assertIn("PO1", ds[0].expected)

    def test_missing_po_is_zero(self):
        lc = LabeledCO(co="x", expected={"PO3": 2})
        self.assertEqual(lc.expected_level("PO3"), 2)
        self.assertEqual(lc.expected_level("PO7"), 0)

    def test_invalid_label_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"labels": [{"co": "x", "expected": {"PO99": 2}}]}, f)
            path = f.name
        with self.assertRaises(ValueError):
            load_dataset(path)


class EvaluateTests(unittest.TestCase):
    def test_perfect_labels_score_100(self):
        ds = _labels_from_engine([
            "Design and develop a software system using modern tools.",
            "Communicate results through reports.",
        ])
        report = evaluate(ds)
        self.assertEqual(report.exact, 1.0)
        self.assertEqual(report.divergences, [])
        self.assertEqual(report.mae, 0.0)

    def test_metrics_in_range(self):
        report = evaluate(load_dataset(_SAMPLE))
        self.assertTrue(0.0 <= report.exact <= 1.0)
        self.assertTrue(0.0 <= report.within1 <= 1.0)
        self.assertGreaterEqual(report.within1, report.exact)  # within-1 is looser
        self.assertEqual(report.n_cells, report.n_cos * 12)

    def test_divergences_have_context(self):
        report = evaluate(load_dataset(_SAMPLE))
        for d in report.divergences:
            self.assertNotEqual(d.predicted, d.expected)
            self.assertIn(d.po, [f"PO{i}" for i in range(1, 13)])


class GridSearchTests(unittest.TestCase):
    def test_best_is_never_worse_than_baseline(self):
        result = grid_search(load_dataset(_SAMPLE))
        self.assertGreater(result.evaluated, 0)
        # best must be >= baseline on the objective (exact match)
        self.assertGreaterEqual(result.best_exact, result.baseline_exact)
        # and if exact ties, MAE must not be worse
        if result.best_exact == result.baseline_exact:
            self.assertLessEqual(result.best_mae, result.baseline_mae)

    def test_best_config_is_valid(self):
        result = grid_search(load_dataset(_SAMPLE))
        result.best.validate()  # thresholds increasing, weights sum to 1


if __name__ == "__main__":
    unittest.main(verbosity=2)
