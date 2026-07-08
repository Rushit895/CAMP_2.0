"""Bloom cognitive gate — the pedagogical core of the CSAS 'signature'.

A Program Outcome is only reachable at high strength when the Course Outcome's
cognitive level fits it. Each PO belongs to a cognitive tier whose gate g(beta) in
[0,1] scales the topical score. beta = bloom_level / 6.
"""
from __future__ import annotations

from ..core.config import CSASConfig

VALID_TIERS = {"knowledge", "higher_order", "application", "professional"}


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def smoothstep(x: float) -> float:
    """Smooth 0->1 ramp: x^2 * (3 - 2x), clamped to [0,1]."""
    x = _clamp01(x)
    return x * x * (3.0 - 2.0 * x)


def bloom_gate(tier: str, bloom_level: int, cfg: CSASConfig) -> float:
    """Return the cognitive gate g(beta) in [0,1] for a PO's tier.

    A configurable floor lifts every non-professional gate so that cognition
    down-weights rather than vetoes: gate = floor + (1 - floor) * gate_raw.
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"unknown cognitive tier: {tier!r}")

    beta = bloom_level / 6.0

    if tier == "professional":
        # Topic-driven POs (ethics, environment, teamwork, communication,
        # lifelong learning): cognition level is irrelevant.
        return 1.0

    if tier == "knowledge":
        # PO1 always contributes; rigor lifts it. Floor 0.5, ceiling 1.0.
        raw = 0.5 + 0.5 * beta
    elif tier == "higher_order":
        lo, hi = cfg.higher_order_lo, cfg.higher_order_hi
        raw = smoothstep((beta - lo) / (hi - lo))
    else:  # application
        lo, hi = cfg.application_lo, cfg.application_hi
        raw = smoothstep((beta - lo) / (hi - lo))

    floor = cfg.gate_floor
    return floor + (1.0 - floor) * raw
