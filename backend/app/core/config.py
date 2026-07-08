"""Tunable constants for the CSAS engine.

Everything that shapes the numbers lives here so re-calibration is a config change,
not a code change. See docs/SIGNATURE_ALGORITHM.md for what each value means.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CSASConfig:
    # Blend weights for the two topical signals (must sum to 1.0).
    semantic_weight: float = 0.55   # a — TF-IDF cosine vs PO descriptor
    lexical_weight: float = 0.45    # b — curated lexicon affinity

    # Lexical saturation constant k in  lambda = 1 - exp(-k * hit).
    lambda_saturation: float = 0.9

    # Bloom-gate floor in [0,1): raises every non-professional gate so cognition
    # down-weights (rather than vetoes) higher-order POs. 0.0 = strict veto behaviour.
    #   gate = floor + (1 - floor) * gate_raw
    gate_floor: float = 0.0

    # Quantization thresholds (raw score -> level 0/1/2/3).
    tau1: float = 0.12   # >= tau1 -> level 1
    tau2: float = 0.28   # >= tau2 -> level 2
    tau3: float = 0.48   # >= tau3 -> level 3

    # Bloom-gate breakpoints per cognitive tier, expressed on beta = bloom/6.
    # gate = smoothstep((beta - lo) / (hi - lo)); 'knowledge' & 'professional'
    # use closed-form gates in bloom.py instead of these breakpoints.
    higher_order_lo: float = 0.33   # ~ Bloom 2
    higher_order_hi: float = 0.83   # ~ Bloom 5
    application_lo: float = 0.17    # ~ Bloom 1
    application_hi: float = 0.67    # ~ Bloom 4

    def validate(self) -> None:
        assert abs(self.semantic_weight + self.lexical_weight - 1.0) < 1e-9, \
            "semantic_weight + lexical_weight must equal 1.0"
        assert 0.0 < self.tau1 < self.tau2 < self.tau3 < 1.0, \
            "thresholds must be strictly increasing within (0, 1)"
        assert 0.0 <= self.gate_floor < 1.0, "gate_floor must be in [0, 1)"


DEFAULT_CONFIG = CSASConfig()
DEFAULT_CONFIG.validate()
