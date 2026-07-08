"""CSAS — CAMP Signature Alignment Score.

The deterministic, explainable engine that maps a Course Outcome to each of the 12
AICTE Program Outcomes at strength 0/1/2/3. See docs/SIGNATURE_ALGORITHM.md.

    raw(CO, PO_j) = ( a*sigma + b*lambda ) * gate_tier(beta)
    level         = quantize(raw ; tau1, tau2, tau3)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.config import DEFAULT_CONFIG, CSASConfig
from .bloom import bloom_gate
from .lexicon import ProgramOutcome, lexical_affinity, load_program_outcomes
from .preprocess import ProcessedCO, preprocess_co
from .vectorize import semantic_similarity

_LEVEL_LABEL = {0: "None", 1: "Low", 2: "Medium", 3: "High"}


@dataclass
class CellScore:
    po: str
    title: str
    level: int
    raw: float
    semantic: float
    lexical: float
    bloom_level: int
    gate: float
    matched_terms: list[dict] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "po": self.po,
            "title": self.title,
            "level": self.level,
            "label": _LEVEL_LABEL[self.level],
            "raw": round(self.raw, 4),
            "semantic": round(self.semantic, 4),
            "lexical": round(self.lexical, 4),
            "bloom_level": self.bloom_level,
            "gate": round(self.gate, 4),
            "matched_terms": self.matched_terms,
            "rationale": self.rationale,
        }


@dataclass
class CORow:
    co_text: str
    bloom_level: int
    cells: list[CellScore]

    def to_dict(self) -> dict:
        return {
            "co": self.co_text,
            "bloom_level": self.bloom_level,
            "pos": {c.po: c.level for c in self.cells},
            "details": [c.to_dict() for c in self.cells],
        }


def _quantize(raw: float, cfg: CSASConfig) -> int:
    if raw >= cfg.tau3:
        return 3
    if raw >= cfg.tau2:
        return 2
    if raw >= cfg.tau1:
        return 1
    return 0


def _rationale(po: ProgramOutcome, level: int, bloom: int, matched: list[dict]) -> str:
    if level == 0:
        return f"No meaningful alignment with {po.id} ({po.title})."
    terms = ", ".join(m["term"] for m in matched[:3]) if matched else "descriptor overlap"
    strength = _LEVEL_LABEL[level].lower()
    return (
        f"{strength.capitalize()} alignment with {po.id} ({po.title}): "
        f"Bloom {bloom} cognition; lexical hits on {terms}."
    )


def score_cell(pco: ProcessedCO, po: ProgramOutcome, cfg: CSASConfig = DEFAULT_CONFIG) -> CellScore:
    sigma = semantic_similarity(pco.tokens, po.id)
    lex = lexical_affinity(pco.token_set, po, cfg.lambda_saturation)
    gate = bloom_gate(po.cognitive_tier, pco.bloom_level, cfg)

    topical = cfg.semantic_weight * sigma + cfg.lexical_weight * lex.lam
    raw = topical * gate
    level = _quantize(raw, cfg)

    return CellScore(
        po=po.id,
        title=po.title,
        level=level,
        raw=raw,
        semantic=sigma,
        lexical=lex.lam,
        bloom_level=pco.bloom_level,
        gate=gate,
        matched_terms=lex.matched,
        rationale=_rationale(po, level, pco.bloom_level, lex.matched),
    )


def score_co(co_text: str, cfg: CSASConfig = DEFAULT_CONFIG) -> CORow:
    """Score one Course Outcome against all 12 Program Outcomes."""
    pco = preprocess_co(co_text)
    outcomes = load_program_outcomes()
    cells = [score_cell(pco, po, cfg) for po in outcomes]
    return CORow(co_text=co_text, bloom_level=pco.bloom_level, cells=cells)


def score_matrix(cos: list[str], cfg: CSASConfig = DEFAULT_CONFIG) -> list[CORow]:
    """Score a list of COs -> the full CO-PO matrix."""
    return [score_co(co, cfg) for co in cos]
