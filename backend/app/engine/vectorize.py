"""TF-IDF cosine similarity (pure stdlib) for the semantic signal (sigma).

IDF is fitted once over the 12 PO descriptors so words common to many POs are
down-weighted. Deterministic and dependency-free — sparse dict vectors, no numpy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .lexicon import ProgramOutcome, load_program_outcomes
from .preprocess import tokenize


def _tf(tokens: list[str]) -> dict[str, float]:
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    return tf


@dataclass
class _FittedSpace:
    idf: dict[str, float]
    po_vectors: dict[str, dict[str, float]]  # po_id -> tfidf vector (normalized)


def _apply_idf(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    vec: dict[str, float] = {}
    for term, freq in tf.items():
        weight = idf.get(term)
        if weight is None:
            continue  # out-of-vocabulary vs the PO corpus contributes nothing to cosine
        vec[term] = freq * weight
    return vec


def _l2_normalize(vec: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm == 0.0:
        return {}
    return {k: v / norm for k, v in vec.items()}


@lru_cache(maxsize=1)
def _fit() -> _FittedSpace:
    outcomes: tuple[ProgramOutcome, ...] = load_program_outcomes()
    docs: dict[str, list[str]] = {po.id: tokenize(po.description) for po in outcomes}

    n_docs = len(docs)
    df: dict[str, int] = {}
    for tokens in docs.values():
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    # smoothed idf, always positive so a term shared by all docs still counts a little
    idf = {term: math.log((1.0 + n_docs) / (1.0 + d)) + 1.0 for term, d in df.items()}

    po_vectors = {
        po_id: _l2_normalize(_apply_idf(_tf(tokens), idf)) for po_id, tokens in docs.items()
    }
    return _FittedSpace(idf=idf, po_vectors=po_vectors)


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    # iterate the smaller dict for speed
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def semantic_similarity(co_tokens: list[str], po_id: str) -> float:
    """Cosine similarity between the CO and PO descriptor in TF-IDF space -> [0,1]."""
    space = _fit()
    co_vec = _l2_normalize(_apply_idf(_tf(co_tokens), space.idf))
    po_vec = space.po_vectors.get(po_id, {})
    sim = _cosine(co_vec, po_vec)
    # cosine of non-negative tfidf vectors is already in [0,1]; clamp for safety
    return max(0.0, min(1.0, sim))
