# CSAS — CAMP Signature Alignment Score

> The in-house, deterministic math that maps a Course Outcome (CO) to each of the 12
> AICTE Program Outcomes (PO1–PO12) at a strength level of **0, 1, 2, or 3**.

This replaces the old, non-deterministic pipeline (LLM keyword extraction → LLM
per-keyword PO assignment → browser-side `matches/3` thresholding). CSAS is:

- **Deterministic** — same CO in, same matrix out. No RNG, no network, no LLM in the scoring path.
- **Explainable** — every score ships with the exact numbers and matched terms that produced it.
- **Tunable** — all weights and thresholds live in one config, calibrated against real COs.
- **Cheap & offline** — pure arithmetic over curated data; no paid API, no model download.

---

## 1. Notation

For a course outcome `CO` and a program outcome `PO_j` (j = 1..12):

```
S(CO, PO_j)  ∈ {0, 1, 2, 3}      final strength level (the matrix cell)
raw(CO, PO_j) ∈ [0, 1]           continuous score before quantization
```

The pipeline is four stages: **preprocess → three signals → blend+gate → quantize.**

---

## 2. Preprocess the CO

1. Lowercase, strip punctuation, tokenize on non-alphanumerics.
2. Remove stopwords.
3. Light deterministic normalization (plurals `-s/-es/-ies`, verb endings `-ing/-ed`) so
   `analyzing`, `analyzed`, `analyses` all fold to the `analyz-` stem family.
4. Extract:
   - **Bloom level `B ∈ {1..6}`** — the *highest* cognitive verb found in the CO
     (Remember=1 … Create=6). Default `B=3` (Apply) if no verb matches.
   - **Content terms** — the normalized non-stopword tokens with term frequencies,
     used for the semantic and lexical signals.

Normalized cognitive intensity: `β = B / 6  ∈ [0.17, 1.0]`.

---

## 3. The three signals

Each PO carries two curated data assets (in `app/data/`):
- a **descriptor** (its official AICTE text), and
- a **weighted lexicon** — domain terms with weights `w ∈ (0,1]` (e.g. for PO3:
  `design 1.0, prototype 0.8, architecture 0.7, ...`).

### 3a. Semantic alignment  σ ∈ [0,1]

TF-IDF cosine similarity between the CO content vector and the PO descriptor vector,
over a shared vocabulary built from all PO descriptors + lexicons. IDF is computed
across the 12 PO "documents" so generic words (present in many POs) are down-weighted.

```
σ(CO, PO_j) = cos( tfidf(CO) , tfidf(descriptor_j) )
```

### 3b. Lexical affinity  λ ∈ [0,1]

Domain-specific signal the descriptor alone misses. For every CO content term that hits
PO_j's weighted lexicon, accumulate its weight, then squash:

```
hit_j   = Σ  w(term)      over CO terms matching lexicon_j
λ(CO,PO_j) = 1 − exp( −k · hit_j )          (saturating; k = LAMBDA_SAT, default 0.9)
```

Saturation means one strong keyword already lands meaningful affinity, and stacking many
keeps λ bounded at 1 instead of exploding.

### 3c. Bloom gate  g ∈ [0,1]

This is the pedagogical heart of the "signature." A PO is only reachable at high strength
if the CO's cognitive level is appropriate for it. POs fall into **cognitive tiers**, each
with its own gate as a function of `β`:

| Tier | POs | Rationale | Gate `g(β)` |
|------|-----|-----------|-------------|
| `knowledge`   | PO1 | Knowledge/application; always contributes, grows with rigor | `0.5 + 0.5·β` |
| `higher_order`| PO2, PO3, PO4 | Analysis / design / investigation need genuine higher-order cognition | `smoothstep((β−0.33)/0.50)` |
| `application` | PO5, PO11 | Tool use / management need at least "Apply" | `smoothstep((β−0.17)/0.50)` |
| `professional`| PO6–PO10, PO12 | Ethics, environment, teamwork, communication, lifelong learning depend on *topic*, not Bloom level | `1.0` |

`smoothstep(x) = clamp(x,0,1)²·(3 − 2·clamp(x,0,1))` — a smooth 0→1 ramp.
So a low-Bloom CO ("define…", B=1) is *gated out* of a strong PO3 (design) even if it
shares vocabulary, while a "design…" CO (B=6) passes the gate fully.

---

## 4. Blend and quantize

Convex blend of the two topical signals, then gate by cognition:

```
raw(CO, PO_j) = ( a·σ + b·λ ) · g_tier(j)(β)          a + b = 1
                default a = 0.55 (semantic), b = 0.45 (lexical)
```

Quantize with three calibrated thresholds `τ1 < τ2 < τ3`:

```
raw < τ1            → 0   (no meaningful mapping)
τ1 ≤ raw < τ2       → 1   (Low)
τ2 ≤ raw < τ3       → 2   (Medium)
raw ≥ τ3            → 3   (High)

default τ = (0.12, 0.28, 0.48)
```

---

## 5. Explainability payload

Every cell returns not just `S`, but the full derivation:

```json
{
  "po": "PO3", "level": 2, "raw": 0.41,
  "semantic": 0.38, "lexical": 0.52, "bloom_level": 5, "gate": 0.86,
  "matched_terms": [{"term": "design", "weight": 1.0}, {"term": "algorithm", "weight": 0.6}],
  "rationale": "High-order design intent (Bloom 5) with strong lexical hits on design, algorithm."
}
```

This is what makes the matrix **defensible in an NBA/AICTE audit**: a reviewer can see
exactly why CO2→PO3 is a 2 and not a 3.

---

## 6. Calibration & tuning

All constants — `a, b, LAMBDA_SAT (k)`, tier gate breakpoints, and `τ` — live in
`app/core/config.py` (`CSASConfig`). They are calibrated against a labelled set of real
COs in `tests/`. Re-tuning is a data/config change, not a code change.

The LLM is **not** part of scoring. It may optionally be reintroduced later purely to
*suggest* lexicon terms for human review, or to draft prose — never to compute the matrix.
