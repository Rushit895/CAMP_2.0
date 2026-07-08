"""CLI for the CSAS calibration harness.

    python -m app.calibration.run                         # default sample dataset
    python -m app.calibration.run --dataset labels.json   # your labelled COs
    python -m app.calibration.run --grid                  # also suggest better config
    python -m app.calibration.run --max-div 40            # show more divergences

Run from the backend/ directory (so `app` is importable), or with
`--app-dir backend` semantics if you prefer uvicorn-style invocation.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ..core.config import DEFAULT_CONFIG
from .harness import evaluate, grid_search, load_dataset

_DEFAULT_DATASET = Path(__file__).resolve().parent.parent.parent / "calibration" / "sample_labels.json"


def _pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def _print_report(report) -> None:
    print("=" * 68)
    print(f"CSAS CALIBRATION REPORT   ({report.n_cos} COs, {report.n_cells} cells)")
    print("=" * 68)
    print(f"  Exact level match : {_pct(report.exact)}")
    print(f"  Within +/-1 level : {_pct(report.within1)}")
    print(f"  Mean abs error    : {report.mae:.3f} levels")
    print(f"  Bias (pred-exp)   : {report.bias:+.3f}   "
          f"({'over' if report.bias > 0 else 'under'}-predicting)")
    print(f"  Mapped P / R / F1 : {_pct(report.precision)} / {_pct(report.recall)} / {_pct(report.f1)}")

    print("\n  Per-PO (mapped vs not):  PO   F1     P      R    exact")
    for po, st in report.per_po.items():
        if st.tp + st.fp + st.fn == 0 and st.exact == st.total:
            continue  # PO never expected and never predicted -- skip noise
        print(f"    {po:>4}  {_pct(st.f1)}  {_pct(st.precision)}  {_pct(st.recall)}  "
              f"{st.exact}/{st.total}")

    if report.divergences:
        print(f"\n  Divergences ({len(report.divergences)} cells)  "
              f"[exp->pred  raw  sig/lam/gate]:")
        for d in report.divergences:
            arrow = "OVER " if d.gap > 0 else "UNDER"
            print(f"    CO{d.co_index + 1:<2} {d.po:>4}  {arrow} {d.expected}->{d.predicted}"
                  f"   raw={d.raw:.3f}  sig={d.sigma:.2f} lam={d.lam:.2f} g={d.gate:.2f}")
    else:
        print("\n  No divergences -- CSAS matches the labels exactly.")
    print()


def _print_grid(result) -> None:
    print("-" * 68)
    print("GRID SEARCH  (maximise exact match, tie-break lower MAE)")
    print("-" * 68)
    print(f"  Configs evaluated : {result.evaluated}")
    print(f"  Baseline (default): exact {_pct(result.baseline_exact)}   MAE {result.baseline_mae:.3f}")
    print(f"  Best found        : exact {_pct(result.best_exact)}   MAE {result.best_mae:.3f}")
    b = result.best
    improved = result.best_exact > result.baseline_exact or (
        result.best_exact == result.baseline_exact and result.best_mae < result.baseline_mae)
    if improved:
        print("\n  Suggested CSASConfig (edit app/core/config.py):")
        print(f"    semantic_weight = {b.semantic_weight}")
        print(f"    lexical_weight  = {b.lexical_weight}")
        print(f"    tau1, tau2, tau3 = {b.tau1}, {b.tau2}, {b.tau3}")
        print(f"    gate_floor      = {b.gate_floor}")
    else:
        print("\n  Default config already optimal on this dataset. No change suggested.")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Calibrate CSAS against labelled COs.")
    ap.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    ap.add_argument("--grid", action="store_true", help="run grid search for a better config")
    ap.add_argument("--max-div", type=int, default=25, help="max divergences to print")
    args = ap.parse_args()

    dataset = load_dataset(args.dataset)
    report = evaluate(dataset, DEFAULT_CONFIG)
    report.divergences = report.divergences[: args.max_div]
    _print_report(report)

    if args.grid:
        _print_grid(grid_search(dataset))


if __name__ == "__main__":
    main()
