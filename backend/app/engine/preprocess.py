"""Deterministic text preprocessing for the CSAS engine.

Pure stdlib. No external NLP model, no network, no randomness — the same input
always yields the same tokens, stems and Bloom level. Kept intentionally small and
transparent because it feeds a scoring algorithm we must be able to defend line by line.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# A compact, curated stopword list. Deliberately excludes domain words.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "of", "to", "in",
    "on", "for", "with", "without", "by", "at", "from", "into", "onto", "as", "is",
    "are", "was", "were", "be", "been", "being", "this", "that", "these", "those",
    "it", "its", "their", "them", "they", "we", "our", "you", "your", "he", "she",
    "his", "her", "which", "who", "whom", "whose", "will", "shall", "can", "could",
    "would", "should", "may", "might", "must", "do", "does", "did", "done", "have",
    "has", "had", "having", "not", "no", "so", "such", "than", "too", "very", "up",
    "down", "out", "over", "under", "again", "further", "here", "there", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "own", "same",
    "able", "using", "use", "used", "various", "given", "based", "upon",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _stem(token: str) -> str:
    """Very light, deterministic suffix stripper.

    Not a full Porter stemmer — just enough to fold the inflections that matter for
    keyword matching (plurals and common verb endings). Chosen over NLTK/spaCy so the
    engine has zero heavy dependencies and behaves identically on every machine.
    """
    t = token
    # order matters: strip longer/derived endings first
    for suf in ("izes", "ized", "izing", "ize"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)] + "iz"
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "i"
    if t.endswith("ied") and len(t) > 4:
        return t[:-3] + "i"
    for suf in ("ing", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            base = t[: -len(suf)]
            # avoid mangling words like "gas"/"bus" -> keep >=3 chars
            return base
    return t


def normalize_token(token: str) -> str:
    return _stem(token.lower())


def _verb_key(word: str) -> str:
    """Aggressive canonical form used ONLY for Bloom verb matching.

    Unifies verb inflections that the light content stemmer leaves apart, e.g.
    apply/applies/applied/applying -> 'appli', analyze/analyzing/analyzed -> 'analyz'.
    Kept separate from _stem so noun/lexicon matching stays conservative.
    """
    w = word.lower()
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    if w.endswith("y") and len(w) > 3:
        w = w[:-1] + "i"
    return w


def tokenize(text: str) -> list[str]:
    """Return normalized (stemmed, stopword-filtered) content tokens."""
    if not text:
        return []
    raw = _TOKEN_RE.findall(text.lower())
    out: list[str] = []
    for tok in raw:
        if tok in _STOPWORDS:
            continue
        stem = _stem(tok)
        if len(stem) < 2:
            continue
        if stem in _STOPWORDS:
            continue
        out.append(stem)
    return out


@lru_cache(maxsize=1)
def _bloom_data() -> dict[str, int]:
    """Map each normalized Bloom verb stem -> its cognitive level (1..6)."""
    with open(_DATA_DIR / "bloom_verbs.json", encoding="utf-8") as f:
        data = json.load(f)
    verb_to_level: dict[str, int] = {}
    for level_str, spec in data["levels"].items():
        level = int(level_str)
        for verb in spec["verbs"]:
            # canonicalize so every inflection of a verb maps to one key
            verb_to_level[_verb_key(verb)] = level
    return verb_to_level


DEFAULT_BLOOM = 3  # "Apply" — same neutral default the old system used


def detect_bloom_level(tokens: list[str]) -> int:
    """Highest Bloom cognitive level present among the CO tokens.

    Using the maximum (not just the leading verb) is more robust to phrasings like
    "apply X to analyze Y", where the true cognitive demand is the higher verb.
    """
    verb_to_level = _bloom_data()
    best = 0
    for tok in tokens:
        lvl = verb_to_level.get(_verb_key(tok))
        if lvl and lvl > best:
            best = lvl
    return best if best else DEFAULT_BLOOM


@dataclass
class ProcessedCO:
    text: str
    tokens: list[str]
    term_freq: dict[str, float] = field(default_factory=dict)
    bloom_level: int = DEFAULT_BLOOM

    @property
    def token_set(self) -> set[str]:
        return set(self.tokens)


def preprocess_co(text: str) -> ProcessedCO:
    tokens = tokenize(text)
    tf: dict[str, float] = {}
    for tok in tokens:
        tf[tok] = tf.get(tok, 0.0) + 1.0
    bloom = detect_bloom_level(tokens)
    return ProcessedCO(text=text or "", tokens=tokens, term_freq=tf, bloom_level=bloom)
