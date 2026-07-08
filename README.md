# CAMP 2.0 — Course Alignment & Mapping Portal

> A robust, reliable rebuild of the CO–PO mapping portal for Outcome-Based Education
> (NBA / AICTE accreditation), powered by **CSAS** — our own deterministic,
> explainable mapping mathematics.

CAMP maps a course's **Course Outcomes (COs)** to the 12 AICTE **Program Outcomes
(PO1–PO12)** at strength levels **0–3**, producing the CO·PO matrix that accreditation
requires — with a full, auditable justification behind every cell.

---

## Why 2.0

The previous version computed the mapping with **non-deterministic LLM prompts** (keyword
extraction → per-keyword PO assignment → browser-side thresholding). Same course could
yield a different matrix on each run, and the reasoning wasn't defensible in an audit.

CAMP 2.0 replaces that with **CSAS (CAMP Signature Alignment Score)** — a deterministic
engine that is:

- **Reproducible** — same COs in, same matrix out. No randomness, no network, no LLM in the scoring path.
- **Explainable** — every cell ships its full derivation (semantic, lexical, Bloom gate, matched terms, rationale).
- **Offline & free** — pure arithmetic over curated data. No paid API, no model download.
- **Tunable** — all weights, thresholds and lexicons live in config/data, calibrated against real COs.

Full spec: **[docs/SIGNATURE_ALGORITHM.md](docs/SIGNATURE_ALGORITHM.md)**

---

## The CSAS formula (in brief)

For a Course Outcome `CO` and Program Outcome `PO_j`:

```
raw(CO, PO_j) = ( a·σ + b·λ ) · gate_tier(β)      →   level ∈ {0,1,2,3}
```

- **σ** — TF-IDF cosine similarity of the CO against the PO descriptor (semantic)
- **λ** — saturating affinity against a curated, weighted PO keyword lexicon (lexical)
- **gate(β)** — a Bloom's-taxonomy cognitive gate that differs per PO tier, so an
  *Apply*-level CO can't spuriously score high on a *Design* outcome, while
  professional POs (ethics, environment, teamwork…) stay Bloom-neutral.

---

## Project structure

```
CAMP_2.0/
├── backend/        Python — CSAS engine (pure stdlib) + FastAPI (/api)
│   ├── app/
│   │   ├── engine/     preprocess · bloom · lexicon · vectorize · csas
│   │   ├── data/       PO definitions, PO lexicons, Bloom verbs (JSON)
│   │   ├── api/        routes
│   │   └── core/       tunable CSASConfig
│   └── tests/          unit tests (stdlib unittest) + calibration harness
├── frontend/       Vanilla HTML/CSS/JS dashboard (served at /app)
├── docs/           SIGNATURE_ALGORITHM.md
```

---

## Quick start

```bash
cd backend
python -m pip install -r requirements.txt        # API layer only; the engine needs no deps
python -m uvicorn app.main:app --app-dir .. --host 127.0.0.1 --port 8099
```

Open **http://127.0.0.1:8099/** → enter Course Outcomes → **Map to POs**.
Click any matrix cell to see exactly why it scored the way it did.

- Swagger API docs: `http://127.0.0.1:8099/docs`
- Health: `GET /api/health` · Map: `POST /api/map`

### Tests

```bash
cd backend
python -m unittest discover -s tests -p 'test_*.py'
python -m tests.calibrate      # print a sample CO·PO matrix
```

---

## Status

| Component | Status |
|-----------|--------|
| CSAS math engine + unit tests | ✅ |
| FastAPI API (`/api/map`, `/api/program-outcomes`, `/api/health`) | ✅ |
| Frontend dashboard (matrix + explainability) | ✅ |
| Persistence / database (SQLAlchemy, SQLite default) | ✅ |
| Course CRUD + save/load in the UI | ✅ |
| DOCX export of accreditation document | ⏳ planned |
| Lexicon / threshold calibration on real COs | ⏳ ongoing |
