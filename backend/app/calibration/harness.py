"""Calibration harness for CSAS.

Feed it labelled Course Outcomes (faculty-judged CO->PO levels) and it reports how
closely the deterministic engine matches that judgement, cell by cell, plus a grid
search over the tunable weights/thresholds that best fit your labels.

The math (weights a/b and thresholds tau) can be re-tuned without touching engine
code — this harness tells you *how* to tune it.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..core.config import DEFAULT_CONFIG, CSASConfig
from ..engine.csas import score_co

POS = [f"PO{i}" for i in range(1, 13)]


# --------------------------------------------------------------------------- #
# Dataset
# --------------------------------------------------------------------------- #
@dataclass
class LabeledCO:
    co: str
    expected: dict[str, int]  # po -> expected level (missing = 0)

    def expected_level(self, po: str) -> int:
        return int(self.expected.get(po, 0))


def load_dataset(path: str | Path) -> list[LabeledCO]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out: list[LabeledCO] = []
    for item in raw["labels"]:
        exp = {k: int(v) for k, v in item.get("expected", {}).items()}
        for po, lvl in exp.items():
            if po not in POS or not (0 <= lvl <= 3):
                raise ValueError(f"Invalid label {po}={lvl} for CO: {item['co'][:40]!r}")
        out.append(LabeledCO(co=item["co"], expected=exp))
    return out


# --------------------------------------------------------------------------- #
# Component cache (config-independent parts) for fast grid search
# --------------------------------------------------------------------------- #
@dataclass
class _Cell:
    sigma: float
    lam: float
    gate: float
    expected: int


def _components(dataset: list[LabeledCO]) -> list[list[_Cell]]:
    """Per CO, per PO: (sigma, lambda, gate) at the default lambda-saturation.

    These are independent of the blend weights (a, b) and thresholds (tau), so the
    grid search can sweep those analytically without re-running the engine.
    """
    grid: list[list[_Cell]] = []
    for lc in dataset:
        row = score_co(lc.co)  # default cfg; sigma/lam/gate don't depend on a/b/tau
        by_po = {c.po: c for c in row.cells}
        grid.append([
            _Cell(by_po[po].semantic, by_po[po].lexical, by_po[po].gate, lc.expected_level(po))
            for po in POS
        ])
    return grid


def _quantize(raw: float, cfg: CSASConfig) -> int:
    if raw >= cfg.tau3:
        return 3
    if raw >= cfg.tau2:
        return 2
    if raw >= cfg.tau1:
        return 1
    return 0


def _predict(cell: _Cell, cfg: CSASConfig) -> int:
    # cell.gate is the raw gate (components cached at the default gate_floor=0);
    # apply the candidate floor analytically: gate = floor + (1-floor)*raw.
    gate = cfg.gate_floor + (1.0 - cfg.gate_floor) * cell.gate
    raw = (cfg.semantic_weight * cell.sigma + cfg.lexical_weight * cell.lam) * gate
    return _quantize(raw, cfg)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
@dataclass
class POStat:
    po: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    exact: int = 0
    total: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class Divergence:
    co_index: int
    co: str
    po: str
    expected: int
    predicted: int
    raw: float
    sigma: float
    lam: float
    gate: float

    @property
    def gap(self) -> int:
        return self.predicted - self.expected


@dataclass
class Report:
    n_cos: int
    n_cells: int
    exact: float          # fraction of cells with predicted == expected
    within1: float        # fraction with |predicted - expected| <= 1
    mae: float            # mean |predicted - expected|
    bias: float           # mean (predicted - expected); + = over-predicting
    precision: float
    recall: float
    f1: float
    per_po: dict[str, POStat]
    divergences: list[Divergence] = field(default_factory=list)


def evaluate(dataset: list[LabeledCO], cfg: CSASConfig = DEFAULT_CONFIG) -> Report:
    """Faithful evaluation using the real engine for the given config."""
    per_po = {po: POStat(po=po) for po in POS}
    n_cells = 0
    sum_abs = 0
    sum_signed = 0
    exact_ct = 0
    within1_ct = 0
    tp = fp = fn = 0
    divergences: list[Divergence] = []

    for i, lc in enumerate(dataset):
        row = score_co(lc.co, cfg)
        by_po = {c.po: c for c in row.cells}
        for po in POS:
            cell = by_po[po]
            p, e = cell.level, lc.expected_level(po)
            n_cells += 1
            d = p - e
            sum_abs += abs(d)
            sum_signed += d
            if p == e:
                exact_ct += 1
            if abs(d) <= 1:
                within1_ct += 1

            st = per_po[po]
            st.total += 1
            if p == e:
                st.exact += 1
            if p > 0 and e > 0:
                st.tp += 1; tp += 1
            elif p > 0 and e == 0:
                st.fp += 1; fp += 1
            elif p == 0 and e > 0:
                st.fn += 1; fn += 1
            else:
                st.tn += 1

            if p != e:
                divergences.append(Divergence(
                    co_index=i, co=lc.co, po=po, expected=e, predicted=p,
                    raw=cell.raw, sigma=cell.semantic, lam=cell.lexical, gate=cell.gate,
                ))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    divergences.sort(key=lambda x: (-abs(x.gap), x.co_index))
    return Report(
        n_cos=len(dataset), n_cells=n_cells,
        exact=exact_ct / n_cells if n_cells else 0.0,
        within1=within1_ct / n_cells if n_cells else 0.0,
        mae=sum_abs / n_cells if n_cells else 0.0,
        bias=sum_signed / n_cells if n_cells else 0.0,
        precision=precision, recall=recall, f1=f1,
        per_po=per_po, divergences=divergences,
    )


# --------------------------------------------------------------------------- #
# Grid search
# --------------------------------------------------------------------------- #
@dataclass
class GridResult:
    best: CSASConfig
    best_exact: float
    best_mae: float
    baseline_exact: float
    baseline_mae: float
    evaluated: int


_DEFAULT_GRID = {
    "a": [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
    "tau1": [0.08, 0.10, 0.12, 0.14, 0.16],
    "tau2": [0.24, 0.28, 0.32, 0.36],
    "tau3": [0.42, 0.48, 0.54, 0.60],
    "gate_floor": [0.0, 0.2, 0.35, 0.5],
}


def _score_config(comps: list[list[_Cell]], cfg: CSASConfig) -> tuple[float, float]:
    """(exact-match fraction, MAE) computed from cached components."""
    n = 0
    exact = 0
    abs_sum = 0
    for row in comps:
        for cell in row:
            p = _predict(cell, cfg)
            n += 1
            if p == cell.expected:
                exact += 1
            abs_sum += abs(p - cell.expected)
    if n == 0:
        return 0.0, 0.0
    return exact / n, abs_sum / n


def grid_search(dataset: list[LabeledCO], grid: dict | None = None) -> GridResult:
    """Search weights/thresholds that best fit the labels.

    Objective: maximise exact-level match, tie-break by lower MAE. lambda_saturation
    is held at the default (components are cached for speed).
    """
    g = grid or _DEFAULT_GRID
    comps = _components(dataset)

    base_exact, base_mae = _score_config(comps, DEFAULT_CONFIG)
    best_cfg = DEFAULT_CONFIG
    best_exact, best_mae = base_exact, base_mae
    evaluated = 0

    for a, t1, t2, t3, gf in itertools.product(
        g["a"], g["tau1"], g["tau2"], g["tau3"], g.get("gate_floor", [0.0])
    ):
        if not (t1 < t2 < t3):
            continue
        cfg = replace(DEFAULT_CONFIG, semantic_weight=a, lexical_weight=round(1 - a, 4),
                      tau1=t1, tau2=t2, tau3=t3, gate_floor=gf)
        evaluated += 1
        exact, mae = _score_config(comps, cfg)
        if (exact > best_exact) or (exact == best_exact and mae < best_mae):
            best_cfg, best_exact, best_mae = cfg, exact, mae

    return GridResult(
        best=best_cfg, best_exact=best_exact, best_mae=best_mae,
        baseline_exact=base_exact, baseline_mae=base_mae, evaluated=evaluated,
    )
