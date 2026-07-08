# CAMP2.O Backend

FastAPI backend for the Course Alignment & Mapping Portal. The CO→PO mapping is
computed by **CSAS** (CAMP Signature Alignment Score) — our own deterministic,
explainable math engine. No LLM sits in the scoring path.

> Full algorithm spec: [`../docs/SIGNATURE_ALGORITHM.md`](../docs/SIGNATURE_ALGORITHM.md)

## Layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── api/routes.py        # /api/health, /api/program-outcomes, /api/map
│   ├── core/config.py       # CSASConfig — all tunable weights & thresholds
│   ├── engine/              # the CSAS math engine (pure stdlib, no deps)
│   │   ├── preprocess.py    # tokenize, stem, Bloom-level detection
│   │   ├── bloom.py         # cognitive gate functions
│   │   ├── lexicon.py       # PO lexicon loader + lexical affinity (lambda)
│   │   ├── vectorize.py     # TF-IDF cosine (semantic sigma)
│   │   └── csas.py          # blend + quantize -> level 0..3
│   ├── data/                # PO definitions, PO lexicons, Bloom verbs (JSON)
│   └── models/schemas.py    # pydantic request/response
└── tests/
    ├── test_csas.py         # unit tests (stdlib unittest)
    └── calibrate.py         # manual matrix eyeball harness
```

The **engine has zero third-party dependencies** — it runs and is fully unit-tested
with the Python standard library alone. FastAPI/uvicorn are only the HTTP wrapper.

## Run

```bash
cd backend
python -m pip install -r requirements.txt      # only needed for the API
python -m uvicorn app.main:app --reload --port 8099
```

- API docs (Swagger): http://127.0.0.1:8099/docs
- Health: `GET /api/health`
- Program outcomes: `GET /api/program-outcomes`
- Map COs (stateless): `POST /api/map`
- Courses (persisted): `POST /api/courses`, `GET /api/courses`, `GET /api/courses/{code}`, `DELETE /api/courses/{code}`
- Export DOCX: `POST /api/export` (from payload) · `GET /api/courses/{code}/export` (from saved course)

### Persistence

Saving a course (`POST /api/courses`) computes its CSAS matrix and stores every
cell with full explainability in a database (SQLite by default at `backend/../camp.db`).
Point `CAMP_DB_URL` at Postgres/MariaDB for a real deployment — nothing else changes.
Schema: `courses` → `course_outcomes` → `co_po_cells` (see `app/db/models.py`).

### Example

```bash
curl -X POST http://127.0.0.1:8099/api/map \
  -H "Content-Type: application/json" \
  -d '{"cos":["Design and develop a web application using modern software tools."]}'
```

Each matrix cell returns not just a level (0–3) but the full derivation —
`semantic`, `lexical`, `bloom_level`, `gate`, `matched_terms`, `rationale` — so any
score is auditable for NBA/AICTE review.

## Test

```bash
cd backend
python -m unittest discover -s tests -p 'test_*.py'   # unit tests
python -m tests.calibrate                              # print sample matrix
```

## Tuning

All knobs live in [`app/core/config.py`](app/core/config.py) (`CSASConfig`): signal
weights, lexical saturation, Bloom-gate breakpoints, and the three quantization
thresholds. Re-calibrating against real labelled COs is a config/data change, never
a code change. The PO lexicons in `app/data/po_lexicon.json` are the other tuning
surface — add domain terms with weights per branch/department.

## Calibration harness

Feed the engine faculty-labelled COs and see how well it matches that judgement,
then let it search for the best weights/thresholds:

```bash
cd backend
python -m app.calibration.run                       # report on the sample dataset
python -m app.calibration.run --dataset labels.json # your labelled COs
python -m app.calibration.run --grid                # also suggest a better config
```

Dataset format (`calibration/sample_labels.json`) — list the expected strength
(1–3) per relevant PO; any PO omitted is treated as expected 0:

```json
{ "labels": [
  { "co": "Design and develop ... using modern tools.",
    "expected": { "PO1": 1, "PO3": 3, "PO5": 3 } }
] }
```

The report gives exact-match / within-±1 / MAE / bias, per-PO precision-recall-F1,
and a **divergence list** showing each mismatch with its `σ/λ/gate` internals so you
know *why* it diverged. `--grid` prints a suggested `CSASConfig`. Suggestions are
specific to the dataset you feed it — calibrate on your real COs, not the sample.
