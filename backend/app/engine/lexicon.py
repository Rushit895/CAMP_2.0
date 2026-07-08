"""Loads PO definitions and curated lexicons, and computes lexical affinity (lambda).

Lexicon terms are authored in natural English and normalized here through the same
stemmer the CO preprocessor uses, so matching is consistent. Multi-word terms match
when *all* of their tokens are present in the CO.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .preprocess import normalize_token, tokenize

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class LexTerm:
    display: str            # original human-readable term
    tokens: tuple[str, ...]  # normalized token(s) that must all be present
    weight: float


@dataclass(frozen=True)
class ProgramOutcome:
    id: str
    title: str
    description: str
    cognitive_tier: str
    lexicon: tuple[LexTerm, ...]


def _normalize_term(term: str) -> tuple[str, ...]:
    toks = tokenize(term)
    if toks:
        return tuple(toks)
    # single short/stopword-ish term: fall back to bare normalization
    return (normalize_token(term),)


@lru_cache(maxsize=1)
def load_program_outcomes() -> tuple[ProgramOutcome, ...]:
    with open(_DATA_DIR / "po_definitions.json", encoding="utf-8") as f:
        defs = json.load(f)["program_outcomes"]
    with open(_DATA_DIR / "po_lexicon.json", encoding="utf-8") as f:
        lex = json.load(f)["lexicons"]

    outcomes: list[ProgramOutcome] = []
    for d in defs:
        po_id = d["id"]
        raw_lex = lex.get(po_id, {})
        terms: list[LexTerm] = []
        for term, weight in raw_lex.items():
            if term.startswith("_"):
                continue
            terms.append(LexTerm(display=term, tokens=_normalize_term(term), weight=float(weight)))
        outcomes.append(
            ProgramOutcome(
                id=po_id,
                title=d["title"],
                description=d["description"],
                cognitive_tier=d["cognitive_tier"],
                lexicon=tuple(terms),
            )
        )
    return tuple(outcomes)


@dataclass
class LexicalMatch:
    hit: float                       # summed weight of matched terms
    lam: float                       # saturated affinity in [0,1]
    matched: list[dict]              # [{"term": display, "weight": w}, ...]


def lexical_affinity(token_set: set[str], po: ProgramOutcome, saturation: float) -> LexicalMatch:
    """lambda = 1 - exp(-k * sum_of_matched_weights)."""
    hit = 0.0
    matched: list[dict] = []
    for term in po.lexicon:
        if all(tok in token_set for tok in term.tokens):
            hit += term.weight
            matched.append({"term": term.display, "weight": term.weight})
    lam = 1.0 - math.exp(-saturation * hit) if hit > 0 else 0.0
    # strongest contributors first
    matched.sort(key=lambda m: m["weight"], reverse=True)
    return LexicalMatch(hit=hit, lam=lam, matched=matched)
