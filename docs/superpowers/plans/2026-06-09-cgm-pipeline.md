# CGM Pipeline Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the WS4 Chessboard Governance Multiplier pipeline: evidence-grounded LLM rater panel scoring 6 countries on 5 governance rubrics, with a Cohen's-kappa QA gate, in the `gramercy-workstream-4` repo and a new `cgm` Postgres DB.

**Architecture:** WS3-style flat package `cgm/` of single-responsibility modules orchestrated by `run_cgm.py` phases (anchors → evidence → rate → arbitrate → score → verify → gap). All LLM/HTTP/DB I/O lives in thin wrappers; scoring, kappa, prompt-building, and combination logic are pure functions tested without network or Postgres.

**Tech Stack:** Python 3.13, psycopg2-binary, python-dotenv, requests (World Bank + Tavily), anthropic SDK, pytest. No trained models — rubrics, formulas, and deterministic (`temperature=0`) LLM prompts only.

**Spec:** `docs/superpowers/specs/2026-06-09-cgm-csi-design.md` (approved 2026-06-09). Plans 2 (gramercy-csi master repo) and 3 (WS1 harmonization PR) follow after this plan ships.

**Working directory for all commands:** `/Users/shankar/Desktop/Gramercy/gramercy-workstream-4`

---

## File structure

```
cgm/
  cgm_db.py           # .env loading, connect(), run-row helpers          (Task 2)
  cgm_schema.sql      # all tables + v_cgm_latest                         (Task 2)
  setup_cgm.py        # create `cgm` DB if missing + apply schema         (Task 2)
  cgm_rubrics.py      # rubrics/weights/checklists/archetypes as data     (Task 3)
  cgm_kappa.py        # linear-weighted kappa + degeneracy + agreement    (Task 4)
  cgm_llm.py          # Anthropic wrapper: temp=0, retry, JSON extract    (Task 5)
  cgm_anchors.py      # World Bank quantitative anchors                   (Task 6)
  cgm_evidence.py     # Tavily+Claude evidence packs + coverage           (Task 7)
  cgm_raters.py       # 2 blind raters, citation enforcement, caching     (Task 8)
  cgm_arbiter.py      # >1pt divergence resolution                        (Task 9)
  cgm_scoring.py      # combination, composite, ±10pp sensitivity         (Task 10)
  cgm_verify.py       # QA gate, exit 1                                   (Task 11)
  cgm_gap_report.py   # open gaps + coverage report                       (Task 12)
  run_cgm.py          # orchestrator: --only <phase>                      (Task 13)
tests/
  conftest.py                                                             (Task 1)
  test_rubrics.py test_kappa.py test_llm.py test_anchors.py
  test_evidence.py test_raters.py test_arbiter.py test_scoring.py
  test_verify.py
docs/CGM_METHODOLOGY.md                                                   (Task 14)
.github/workflows/ci.yml  .env.example  .gitignore  requirements.txt  README.md
```

Dimension keys used everywhere: `ai_policy`, `permitting`, `value_capture`, `tech_stack`, `workforce`. Countries: `US, AE, BR, IN, SG, PH` (ISO-2, matching WS1–WS3).

---

### Task 1: Repo scaffolding

**Files:**
- Create: `.gitignore`, `requirements.txt`, `.env.example`, `tests/conftest.py`, `README.md`

- [ ] **Step 1: Write scaffolding files**

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.env
.DS_Store
*.log
```

`requirements.txt`:
```
psycopg2-binary>=2.9
python-dotenv>=1.0
requests>=2.31
anthropic>=0.40
pytest>=8.0
```

`.env.example`:
```
POSTGRES_HOST=
POSTGRES_PORT=5432
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_BOOTSTRAP_DB=postgres
CGM_DB=cgm
ANTHROPIC_API_KEY=
TAVILY_API_KEY=
CGM_RATER_A_MODEL=claude-sonnet-4-6
CGM_RATER_B_MODEL=claude-opus-4-5
CGM_ARBITER_MODEL=claude-opus-4-5
CGM_RATE_FORCE=0
```

`tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cgm"))
```

`README.md`:
```markdown
# Gramercy WS4 - CGM (Chessboard Governance Multiplier)

Scores 6 countries (US, AE, BR, IN, SG, PH) on 5 governance dimensions using
structured 1-5 rubrics, an LLM rater panel (2 blind raters + arbiter), and a
Cohen's-kappa QA gate. Fourth index in the Gramercy capstone (WS1 SDI, WS2 CII,
WS3 CLDV).

**CGM = 0.25*AIPolicy + 0.20*Permitting + 0.20*ValueCapture + 0.20*TechStack + 0.15*Workforce**

## Setup
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # fill POSTGRES_*, ANTHROPIC_API_KEY, TAVILY_API_KEY
.venv/bin/python cgm/setup_cgm.py
```

## Usage
```bash
cd cgm
python run_cgm.py               # full pipeline
python run_cgm.py --only rate   # one phase: anchors|evidence|rate|arbitrate|score|verify|gap
```

See `docs/CGM_METHODOLOGY.md` and `docs/superpowers/specs/2026-06-09-cgm-csi-design.md`.
```

- [ ] **Step 2: Create venv, install, verify pytest runs**

Run: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m pytest`
Expected: `no tests ran` (exit 5 — fine, nothing collected yet)

- [ ] **Step 3: Commit**

```bash
git add .gitignore requirements.txt .env.example tests/conftest.py README.md
git commit -m "chore: repo scaffolding (deps, env template, pytest path, README)"
```

---

### Task 2: Database layer — `cgm_db.py`, `cgm_schema.sql`, `setup_cgm.py`

**Files:**
- Create: `cgm/cgm_db.py`, `cgm/cgm_schema.sql`, `cgm/setup_cgm.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write the failing test** (`tests/test_schema.py`) — schema is static SQL; assert the contract every later module depends on:

```python
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parent.parent / "cgm" / "cgm_schema.sql").read_text()

REQUIRED_TABLES = [
    "cgm_runs", "cgm_collection_log", "cgm_raw_anchors", "cgm_evidence",
    "cgm_rater_scores", "cgm_arbitrations", "cgm_kappa_results",
    "cgm_score_final", "cgm_score_methodology", "cgm_data_gaps",
]

def test_all_required_tables_present():
    for t in REQUIRED_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {t}" in SCHEMA, t

def test_latest_view_present():
    assert "CREATE OR REPLACE VIEW v_cgm_latest" in SCHEMA

def test_idempotent_only():
    assert "DROP TABLE" not in SCHEMA.upper()

def test_rater_unique_constraint():
    assert "UNIQUE (country_iso, dimension, rater_model)" in SCHEMA
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_schema.py -v`
Expected: FAIL (FileNotFoundError — schema doesn't exist)

- [ ] **Step 3: Write `cgm/cgm_schema.sql`**

```sql
-- CGM (Chessboard Governance Multiplier) schema. Idempotent.
CREATE TABLE IF NOT EXISTS cgm_runs (
    run_id      UUID PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    phases      TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cgm_collection_log (
    id      SERIAL PRIMARY KEY,
    run_id  UUID REFERENCES cgm_runs(run_id),
    source  TEXT NOT NULL,
    status  TEXT NOT NULL,           -- ok | error | skipped
    detail  TEXT,
    ts      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cgm_raw_anchors (
    id          SERIAL PRIMARY KEY,
    country_iso TEXT NOT NULL,
    metric      TEXT NOT NULL,
    value       NUMERIC,
    unit        TEXT,
    year        INT,
    source_url  TEXT NOT NULL,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB,
    UNIQUE (country_iso, metric, year)
);

CREATE TABLE IF NOT EXISTS cgm_evidence (
    evidence_id    SERIAL PRIMARY KEY,
    run_id         UUID REFERENCES cgm_runs(run_id),
    country_iso    TEXT NOT NULL,
    dimension      TEXT NOT NULL,
    checklist_item TEXT NOT NULL,
    claim          TEXT NOT NULL,
    quote          TEXT,
    source_url     TEXT NOT NULL,
    source_type    TEXT,
    accessed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cgm_rater_scores (
    id            SERIAL PRIMARY KEY,
    country_iso   TEXT NOT NULL,
    dimension     TEXT NOT NULL,
    rater_model   TEXT NOT NULL,
    score         INT CHECK (score BETWEEN 1 AND 5),
    rubric_clause TEXT,
    evidence_ids  INT[],
    rationale     TEXT,
    scored_at     TIMESTAMPTZ,
    UNIQUE (country_iso, dimension, rater_model)
);

CREATE TABLE IF NOT EXISTS cgm_arbitrations (
    id             SERIAL PRIMARY KEY,
    country_iso    TEXT NOT NULL,
    dimension      TEXT NOT NULL,
    rater_a_score  INT NOT NULL,
    rater_b_score  INT NOT NULL,
    resolved_score INT NOT NULL CHECK (resolved_score BETWEEN 1 AND 5),
    arbiter_model  TEXT NOT NULL,
    reasoning      TEXT NOT NULL,
    ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (country_iso, dimension)
);

CREATE TABLE IF NOT EXISTS cgm_kappa_results (
    id                 SERIAL PRIMARY KEY,
    run_id             UUID REFERENCES cgm_runs(run_id),
    dimension          TEXT NOT NULL,        -- 5 dims + 'pooled'
    kappa_linear       NUMERIC,              -- NULL when degenerate
    degenerate         BOOLEAN NOT NULL DEFAULT FALSE,
    raw_agreement      NUMERIC NOT NULL,
    adjacent_agreement NUMERIC NOT NULL,
    n                  INT NOT NULL,
    computed_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cgm_score_final (
    id            SERIAL PRIMARY KEY,
    run_id        UUID REFERENCES cgm_runs(run_id),
    country_iso   TEXT NOT NULL,
    archetype     TEXT NOT NULL,             -- substrate | processor
    ai_policy     NUMERIC NOT NULL,
    permitting    NUMERIC NOT NULL,
    value_capture NUMERIC NOT NULL,
    tech_stack    NUMERIC NOT NULL,
    workforce     NUMERIC NOT NULL,
    cgm_score     NUMERIC NOT NULL,          -- 0-5 scale
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, country_iso)
);

CREATE TABLE IF NOT EXISTS cgm_score_methodology (
    id           SERIAL PRIMARY KEY,
    run_id       UUID REFERENCES cgm_runs(run_id),
    weights      JSONB NOT NULL,
    rater_models JSONB NOT NULL,
    sensitivity  JSONB,
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cgm_data_gaps (
    id          SERIAL PRIMARY KEY,
    run_id      UUID REFERENCES cgm_runs(run_id),
    country_iso TEXT,
    dimension   TEXT,
    gap         TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'warn',  -- warn | blocker
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE VIEW v_cgm_latest AS
SELECT f.country_iso, f.archetype,
       f.ai_policy, f.permitting, f.value_capture, f.tech_stack, f.workforce,
       f.cgm_score,
       RANK() OVER (ORDER BY f.cgm_score DESC) AS rank,
       f.computed_at
FROM cgm_score_final f
WHERE f.run_id = (SELECT run_id FROM cgm_score_final
                  ORDER BY computed_at DESC LIMIT 1);
```

- [ ] **Step 4: Write `cgm/cgm_db.py`**

```python
"""Shared DB access for the CGM pipeline. All modules get connections from here."""
import os
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SCHEMA_PATH = Path(__file__).resolve().parent / "cgm_schema.sql"


def connect(dbname=None):
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=dbname or os.environ.get("CGM_DB", "cgm"),
    )


def start_run(conn):
    run_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("INSERT INTO cgm_runs (run_id) VALUES (%s)", (run_id,))
    conn.commit()
    return run_id


def log_phase(conn, run_id, phase):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cgm_runs SET phases = phases || %s::text WHERE run_id = %s",
            (phase, run_id),
        )
    conn.commit()


def finish_run(conn, run_id):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cgm_runs SET finished_at = now() WHERE run_id = %s", (run_id,)
        )
    conn.commit()


def log_collection(conn, run_id, source, status, detail=""):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO cgm_collection_log (run_id, source, status, detail)"
            " VALUES (%s, %s, %s, %s)",
            (run_id, source, status, detail[:2000]),
        )
    conn.commit()


def add_gap(conn, run_id, country_iso, dimension, gap, severity="warn"):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO cgm_data_gaps (run_id, country_iso, dimension, gap, severity)"
            " VALUES (%s, %s, %s, %s, %s)",
            (run_id, country_iso, dimension, gap, severity),
        )
    conn.commit()
```

- [ ] **Step 5: Write `cgm/setup_cgm.py`**

```python
"""Create the `cgm` database (if missing) and apply the schema. Idempotent."""
import os

import psycopg2

import cgm_db


def main():
    target = os.environ.get("CGM_DB", "cgm")
    bootstrap = os.environ.get("POSTGRES_BOOTSTRAP_DB", "postgres")
    conn = cgm_db.connect(dbname=bootstrap)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{target}"')
            print(f"created database {target}")
    conn.close()

    conn = cgm_db.connect()
    with conn.cursor() as cur:
        cur.execute(cgm_db.SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()
    print(f"schema applied to {target}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests**

Run: `.venv/bin/python -m pytest tests/test_schema.py -v`
Expected: 4 PASS

- [ ] **Step 7: Provision the live DB**

Run: `cp .env.example .env`, fill `POSTGRES_*` from `../gramercy-workstream-3/.env` plus API keys, then `.venv/bin/python cgm/setup_cgm.py`
Expected output: `created database cgm` (first run) then `schema applied to cgm`

- [ ] **Step 8: Commit**

```bash
git add cgm/cgm_db.py cgm/cgm_schema.sql cgm/setup_cgm.py tests/test_schema.py
git commit -m "feat: cgm database layer - schema, setup, run/log helpers"
```

---

### Task 3: Rubrics as data — `cgm_rubrics.py`

Single source of truth for dimensions, weights, rubric text (verbatim from the sponsor spec — full text is in `docs/superpowers/specs/2026-06-09-cgm-csi-design.md` §"Dimensions, weights, and rubrics"), evidence checklists, and archetype routing.

**Files:**
- Create: `cgm/cgm_rubrics.py`
- Test: `tests/test_rubrics.py`

- [ ] **Step 1: Write the failing test** (`tests/test_rubrics.py`):

```python
import math

from cgm_rubrics import (
    ARCHETYPE, COUNTRIES, DIMENSIONS, EVIDENCE_CHECKLIST, WEIGHTS, rubric_for,
)


def test_weights_sum_to_one():
    assert math.isclose(sum(WEIGHTS.values()), 1.0)
    assert set(WEIGHTS) == set(DIMENSIONS)


def test_every_dimension_has_five_levels():
    for dim in DIMENSIONS:
        for country in COUNTRIES:
            rubric = rubric_for(dim, country)
            assert sorted(rubric) == [1, 2, 3, 4, 5], (dim, country)
            assert all(len(text) > 20 for text in rubric.values())


def test_archetype_routing():
    assert {c: ARCHETYPE[c] for c in COUNTRIES} == {
        "US": "substrate", "AE": "substrate", "BR": "substrate",
        "SG": "processor", "IN": "processor", "PH": "processor",
    }
    # value_capture rubric differs by archetype; others identical
    assert rubric_for("value_capture", "US") != rubric_for("value_capture", "SG")
    assert rubric_for("ai_policy", "US") == rubric_for("ai_policy", "SG")


def test_checklists_nonempty():
    for dim in DIMENSIONS:
        for country in COUNTRIES:
            items = EVIDENCE_CHECKLIST[dim] if dim != "value_capture" \
                else EVIDENCE_CHECKLIST[dim][ARCHETYPE[country]]
            assert len(items) >= 3, dim
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_rubrics.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_rubrics)

- [ ] **Step 3: Write `cgm/cgm_rubrics.py`** — rubric strings copied **verbatim** from the spec document §"Dimensions, weights, and rubrics" (all five levels for D1, D2, D3-substrate, D3-processor, D4, D5; do not paraphrase). Structure:

```python
"""CGM rubrics, weights, evidence checklists, archetypes. Data only - no logic
beyond rubric_for(). Rubric text is verbatim from the sponsor scope document."""

COUNTRIES = ["US", "AE", "BR", "IN", "SG", "PH"]
COUNTRY_NAMES = {
    "US": "United States", "AE": "United Arab Emirates", "BR": "Brazil",
    "IN": "India", "SG": "Singapore", "PH": "Philippines",
}
DIMENSIONS = ["ai_policy", "permitting", "value_capture", "tech_stack", "workforce"]
WEIGHTS = {
    "ai_policy": 0.25, "permitting": 0.20, "value_capture": 0.20,
    "tech_stack": 0.20, "workforce": 0.15,
}
ARCHETYPE = {
    "US": "substrate", "AE": "substrate", "BR": "substrate",
    "SG": "processor", "IN": "processor", "PH": "processor",
}

RUBRICS = {
    "ai_policy": {
        5: "National AI strategy with dedicated funding, minimal regulatory friction, explicit goal of AI leadership",
        4: "Active strategy, moderate funding, generally permissive regulation, proactive investment incentives",
        3: "Strategy exists but implementation uneven, mixed regulatory signals, moderate compliance burden",
        2: "Heavy regulatory framework creating significant compliance costs and deployment delays",
        1: "Restrictive or punitive regulation, no coherent strategy, active barriers to deployment",
    },
    "permitting": {
        5: "Fast-track permitting, weeks-to-months cycles, government actively facilitates",
        4: "Streamlined, 3-12 months, clear pathway, limited opposition mechanisms",
        3: "Standard, 12-24 months, multiple agencies, some community opposition",
        2: "Slow, 24-48 months, complex multi-stakeholder, frequent legal challenges",
        1: "Gridlock, 48+ months, unpredictable, regulatory capture by incumbents",
    },
    "value_capture": {
        "substrate": {
            5: "Stable resource taxation; sovereign wealth fund; active conversion of resource revenue into compute; strong anti-corruption checks",
            4: "Generally stable regime; some safeguards; growing but uneven compute conversion",
            3: "Unstable regime; resource nationalism risk; corruption siphons value; compute conversion throttled by governance",
            2: "High corruption, opaque contracts, weak controls, minimal compute conversion despite endowment",
            1: "Conflict-affected extraction, kleptocratic governance, zero value capture",
        },
        "processor": {
            5: "Large fiscal reserves; active retraining at scale; demonstrated history of economic pivots; actively building compute to offset services decline",
            4: "Adequate fiscal position; some retraining; moderate diversification; some compute investment",
            3: "Limited fiscal buffer; unproven retraining; high services dependence; minimal compute",
            2: "Weak fiscal position; no transition strategy; very high concentration in vulnerable services",
            1: "No buffer, no plan, total dependence on single vulnerable sector",
        },
    },
    "tech_stack": {
        5: "Deep integration with leading stack; secure advanced chip access; hosting critical AI infrastructure",
        4: "Good access; some chip dependency but manageable; growing hyperscaler presence",
        3: "Dual-alignment with long-term uncertainty; or moderate access to one stack with limited depth",
        2: "Peripheral to both stacks; limited chip access; no hyperscaler presence",
        1: "Technology-denied or self-isolated; sanctioned; no AI infrastructure",
    },
    "workforce": {
        5: "World-class education, high digital literacy, extensive retraining, young demographics, English proficiency, strong STEM pipeline",
        4: "Good education, above-average digital literacy, functioning retraining, favorable demographics",
        3: "Average education, moderate digital literacy, limited retraining, mixed demographics",
        2: "Weak education, low digital literacy, minimal retraining, unfavorable demographics",
        1: "Education in crisis, very low digital literacy, no retraining, demographic headwinds",
    },
}

EVIDENCE_CHECKLIST = {
    "ai_policy": [
        "national AI strategy document",
        "dedicated AI budget (USD and % of GDP)",
        "time from AI system development to legal deployment",
        "tax incentives or disincentives for AI",
        "regulatory sandbox count and scope",
        "national AI coordinating body existence and mandate",
    ],
    "permitting": [
        "average permitting timeline for data centers and power generation",
        "announced vs completed projects (3-year completion ratio)",
        "special economic zones or fast-track frameworks",
        "documented delays or cancellations",
    ],
    "value_capture": {
        "substrate": [
            "resource taxation regime stability",
            "sovereign wealth fund existence and mandate",
            "conversion of resource revenue into compute infrastructure",
            "anti-corruption controls in extractive sector",
        ],
        "processor": [
            "fiscal reserves and budget position",
            "workforce retraining programs at scale",
            "history of economic pivots and diversification",
            "compute investment to offset services decline",
        ],
    },
    "tech_stack": [
        "chip import access by generation",
        "hyperscaler commitments (list and USD)",
        "technology alliance participation",
        "bilateral tech agreements",
        "domestic AI model capability",
    ],
    "workforce": [
        "education quality (PISA or equivalent)",
        "digital literacy and ICT development",
        "retraining program scale",
        "demographic projections",
        "STEM pipeline and English proficiency",
    ],
}


def rubric_for(dimension, country_iso):
    rubric = RUBRICS[dimension]
    if dimension == "value_capture":
        return rubric[ARCHETYPE[country_iso]]
    return rubric


def checklist_for(dimension, country_iso):
    items = EVIDENCE_CHECKLIST[dimension]
    if dimension == "value_capture":
        return items[ARCHETYPE[country_iso]]
    return items
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_rubrics.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_rubrics.py tests/test_rubrics.py
git commit -m "feat: rubrics, weights, evidence checklists, archetype routing as data"
```

---

### Task 4: Kappa math — `cgm_kappa.py`

**Files:**
- Create: `cgm/cgm_kappa.py`
- Test: `tests/test_kappa.py`

- [ ] **Step 1: Write the failing test** (`tests/test_kappa.py`). The 4/7 fixture is hand-computed: a=[3,3,4,4,5,5], b=[3,4,4,4,5,4]; observed disagreement = (0+1+0+0+0+1)/4/6 = 1/12; expected = 28/144 = 7/36; kappa = 1 − (1/12)/(7/36) = 4/7.

```python
import math

from cgm_kappa import agreement_stats, linear_weighted_kappa


def test_perfect_agreement_with_variance():
    a = [1, 2, 3, 4, 5, 5]
    assert math.isclose(linear_weighted_kappa(a, a), 1.0)


def test_hand_computed_moderate_case():
    a = [3, 3, 4, 4, 5, 5]
    b = [3, 4, 4, 4, 5, 4]
    assert math.isclose(linear_weighted_kappa(a, b), 4 / 7)


def test_degenerate_identical_constant_returns_none():
    # both raters give every country a 4: perfect agreement, zero variance
    assert linear_weighted_kappa([4] * 6, [4] * 6) is None


def test_constant_but_different_is_zero_not_none():
    # A all 4s, B all 3s: kappa defined and 0 (observed == expected disagreement)
    assert math.isclose(linear_weighted_kappa([4] * 6, [3] * 6), 0.0)


def test_agreement_stats():
    a = [3, 3, 4, 4, 5, 5]
    b = [3, 4, 4, 4, 5, 2]
    stats = agreement_stats(a, b)
    assert math.isclose(stats["raw_agreement"], 4 / 6)
    assert math.isclose(stats["adjacent_agreement"], 5 / 6)  # |5-2|=3 fails ±1
    assert stats["n"] == 6


def test_length_mismatch_raises():
    import pytest
    with pytest.raises(ValueError):
        linear_weighted_kappa([1, 2], [1])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_kappa.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_kappa)

- [ ] **Step 3: Write `cgm/cgm_kappa.py`**

```python
"""Linear-weighted Cohen's kappa for 1-5 rubric scores, with the explicit
degeneracy rule from the design spec: zero expected disagreement (both raters
constant at the same category) makes kappa undefined -> return None; the caller
treats None + 100% raw agreement as a gate PASS reported 'N/A (degenerate)'."""

CATEGORIES = (1, 2, 3, 4, 5)


def linear_weighted_kappa(a, b, categories=CATEGORIES):
    if len(a) != len(b):
        raise ValueError(f"rater score lists differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    k = len(categories)
    idx = {c: i for i, c in enumerate(categories)}
    span = k - 1

    obs_dis = sum(abs(idx[x] - idx[y]) / span for x, y in zip(a, b)) / n

    count_a = {c: 0 for c in categories}
    count_b = {c: 0 for c in categories}
    for x in a:
        count_a[x] += 1
    for y in b:
        count_b[y] += 1
    exp_dis = sum(
        (abs(idx[ca] - idx[cb]) / span) * count_a[ca] * count_b[cb]
        for ca in categories for cb in categories
    ) / (n * n)

    if exp_dis == 0:
        return None  # degenerate: both raters constant at the same category
    return 1 - obs_dis / exp_dis


def agreement_stats(a, b):
    if len(a) != len(b):
        raise ValueError(f"rater score lists differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    return {
        "raw_agreement": sum(x == y for x, y in zip(a, b)) / n,
        "adjacent_agreement": sum(abs(x - y) <= 1 for x, y in zip(a, b)) / n,
        "n": n,
    }
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_kappa.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_kappa.py tests/test_kappa.py
git commit -m "feat: linear-weighted Cohen's kappa with explicit degeneracy rule"
```

---

### Task 5: LLM wrapper — `cgm_llm.py`

**Files:**
- Create: `cgm/cgm_llm.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: Write the failing test** (`tests/test_llm.py`):

```python
import json
from unittest.mock import MagicMock, patch

import pytest

from cgm_llm import call_llm, extract_json


def test_extract_json_plain():
    assert extract_json('{"score": 4}') == {"score": 4}


def test_extract_json_fenced():
    text = 'Here you go:\n```json\n{"score": 3, "evidence_ids": [1, 2]}\n```'
    assert extract_json(text) == {"score": 3, "evidence_ids": [1, 2]}


def test_extract_json_embedded_prose():
    text = 'Reasoning first. {"score": 5, "rationale": "strong"} done.'
    assert extract_json(text) == {"score": 5, "rationale": "strong"}


def test_extract_json_failure_raises():
    with pytest.raises(ValueError):
        extract_json("no json here")


@patch("cgm_llm.anthropic.Anthropic")
def test_call_llm_passes_temperature_zero(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"ok": true}')]
    )
    out = call_llm("claude-opus-4-5", "system prompt", "user prompt")
    assert out == '{"ok": true}'
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["temperature"] == 0
    assert kwargs["model"] == "claude-opus-4-5"


@patch("cgm_llm.time.sleep")
@patch("cgm_llm.anthropic.Anthropic")
def test_call_llm_retries_then_succeeds(mock_cls, _sleep):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        Exception("overloaded"),
        MagicMock(content=[MagicMock(text="ok")]),
    ]
    assert call_llm("m", "s", "u") == "ok"
    assert client.messages.create.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_llm.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_llm)

- [ ] **Step 3: Write `cgm/cgm_llm.py`**

```python
"""Thin Anthropic wrapper: deterministic calls (temperature=0), bounded retries,
robust JSON extraction. All CGM model calls go through call_llm."""
import json
import re
import time

import anthropic

MAX_RETRIES = 3
RETRY_SLEEP_S = 5


def call_llm(model, system, user, max_tokens=2000):
    client = anthropic.Anthropic()
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text
        except Exception as err:  # noqa: BLE001 - retry then surface
            last_err = err
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_SLEEP_S * (attempt + 1))
    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {last_err}")


def extract_json(text):
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        candidates.append(brace.group(0))
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no parseable JSON object in LLM output: {text[:200]!r}")
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_llm.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_llm.py tests/test_llm.py
git commit -m "feat: deterministic LLM wrapper with retries and JSON extraction"
```

---

### Task 6: Quantitative anchors — `cgm_anchors.py`

**Files:**
- Create: `cgm/cgm_anchors.py`
- Test: `tests/test_anchors.py`

- [ ] **Step 1: Write the failing test** (`tests/test_anchors.py`):

```python
from unittest.mock import MagicMock, patch

from cgm_anchors import WB_INDICATORS, fetch_indicator, parse_wb_response

WB_SAMPLE = [
    {"page": 1, "pages": 1},
    [{"indicator": {"id": "SE.ADT.LITR.ZS"}, "country": {"id": "BR"},
      "value": 94.0, "date": "2022"}],
]


def test_indicator_map_covers_workforce_and_gdp():
    metrics = {name for name, _unit in WB_INDICATORS.values()}
    assert "human_capital_index" in metrics
    assert "gdp_usd" in metrics
    assert len(WB_INDICATORS) >= 5


def test_parse_wb_response():
    parsed = parse_wb_response(WB_SAMPLE)
    assert parsed == {"value": 94.0, "year": 2022}


def test_parse_wb_response_empty_returns_none():
    assert parse_wb_response([{"page": 1}, []]) is None
    assert parse_wb_response([{"message": "err"}]) is None


@patch("cgm_anchors.requests.get")
def test_fetch_indicator_builds_url_and_parses(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200, json=MagicMock(return_value=WB_SAMPLE)
    )
    row = fetch_indicator("BR", "SE.ADT.LITR.ZS")
    assert row["value"] == 94.0 and row["year"] == 2022
    assert "BR" in row["source_url"] and "SE.ADT.LITR.ZS" in row["source_url"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_anchors.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_anchors)

- [ ] **Step 3: Write `cgm/cgm_anchors.py`**

```python
"""World Bank quantitative anchors (free API, no key). Most-recent non-empty
value per indicator; full provenance (URL, payload, access time) preserved."""
import json

import requests

import cgm_db
from cgm_rubrics import COUNTRIES

WB_INDICATORS = {
    "HD.HCI.OVRL":     ("human_capital_index", "index"),
    "SE.ADT.LITR.ZS":  ("adult_literacy_pct", "%"),
    "SE.TER.ENRR":     ("tertiary_enrollment_pct", "%"),
    "SP.POP.DPND":     ("age_dependency_ratio", "%"),
    "IT.NET.USER.ZS":  ("internet_users_pct", "%"),
    "NY.GDP.MKTP.CD":  ("gdp_usd", "USD"),
}
WB_URL = ("https://api.worldbank.org/v2/country/{iso}/indicator/{ind}"
          "?format=json&mrnev=1")


def parse_wb_response(payload):
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        return None
    row = payload[1][0]
    if row.get("value") is None:
        return None
    return {"value": float(row["value"]), "year": int(row["date"])}


def fetch_indicator(country_iso, indicator):
    url = WB_URL.format(iso=country_iso, ind=indicator)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    parsed = parse_wb_response(payload)
    if parsed is None:
        return None
    return {**parsed, "source_url": url, "raw_payload": payload}


def collect_anchors(conn, run_id):
    for country in COUNTRIES:
        for indicator, (metric, unit) in WB_INDICATORS.items():
            source = f"worldbank:{indicator}:{country}"
            try:
                row = fetch_indicator(country, indicator)
            except Exception as err:  # noqa: BLE001 - log, gap, continue
                cgm_db.log_collection(conn, run_id, source, "error", str(err))
                cgm_db.add_gap(conn, run_id, country, None,
                               f"anchor fetch failed: {metric}")
                continue
            if row is None:
                cgm_db.log_collection(conn, run_id, source, "skipped", "no value")
                cgm_db.add_gap(conn, run_id, country, None,
                               f"anchor missing: {metric}")
                continue
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO cgm_raw_anchors
                       (country_iso, metric, value, unit, year, source_url, raw_payload)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (country_iso, metric, year) DO UPDATE
                       SET value = EXCLUDED.value, accessed_at = now(),
                           raw_payload = EXCLUDED.raw_payload""",
                    (country, metric, row["value"], unit, row["year"],
                     row["source_url"], json.dumps(row["raw_payload"])),
                )
            conn.commit()
            cgm_db.log_collection(conn, run_id, source, "ok")
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_anchors.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_anchors.py tests/test_anchors.py
git commit -m "feat: World Bank quantitative anchors with provenance"
```

---

### Task 7: Evidence packs — `cgm_evidence.py`

**Files:**
- Create: `cgm/cgm_evidence.py`
- Test: `tests/test_evidence.py`

- [ ] **Step 1: Write the failing test** (`tests/test_evidence.py`):

```python
import json
from unittest.mock import MagicMock, patch

from cgm_evidence import (
    EXTRACT_SYSTEM, build_extract_prompt, coverage, parse_claims,
)

SEARCH_RESULTS = [
    {"title": "UAE National AI Strategy 2031", "url": "https://ai.gov.ae/strategy",
     "content": "The UAE launched its National AI Strategy 2031 with funding..."},
]

CLAIMS_JSON = json.dumps({"claims": [
    {"claim": "UAE has a funded national AI strategy (AI Strategy 2031)",
     "quote": "launched its National AI Strategy 2031 with funding",
     "source_url": "https://ai.gov.ae/strategy",
     "checklist_item": "national AI strategy document"},
]})


def test_build_extract_prompt_includes_sources_and_checklist():
    prompt = build_extract_prompt(
        "United Arab Emirates", "ai_policy",
        ["national AI strategy document"], SEARCH_RESULTS,
    )
    assert "https://ai.gov.ae/strategy" in prompt
    assert "national AI strategy document" in prompt
    assert "United Arab Emirates" in prompt


def test_parse_claims_validates_urls_against_sources():
    claims = parse_claims(CLAIMS_JSON, allowed_urls={"https://ai.gov.ae/strategy"})
    assert len(claims) == 1
    assert claims[0]["checklist_item"] == "national AI strategy document"


def test_parse_claims_drops_unknown_urls():
    bad = json.dumps({"claims": [{"claim": "x", "quote": "y",
                                  "source_url": "https://fabricated.example",
                                  "checklist_item": "item"}]})
    assert parse_claims(bad, allowed_urls={"https://ai.gov.ae/strategy"}) == []


def test_coverage():
    items = ["a", "b", "c", "d"]
    claims = [{"checklist_item": "a"}, {"checklist_item": "a"},
              {"checklist_item": "c"}]
    cov = coverage(items, claims)
    assert cov == {"covered": ["a", "c"], "missing": ["b", "d"], "ratio": 0.5}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_evidence.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_evidence)

- [ ] **Step 3: Write `cgm/cgm_evidence.py`**

```python
"""Evidence packs: Tavily search per checklist item, Claude claim extraction,
coverage measurement. Packs are immutable inputs to the raters - raters never
see the live web. Claims citing URLs not returned by search are dropped
(anti-fabrication guard)."""
import json
import os

import requests

import cgm_db
from cgm_llm import call_llm, extract_json
from cgm_rubrics import COUNTRIES, COUNTRY_NAMES, DIMENSIONS, checklist_for

TAVILY_URL = "https://api.tavily.com/search"

EXTRACT_SYSTEM = """You extract factual evidence claims from web search results
for sovereign governance scoring. Output STRICT JSON:
{"claims": [{"claim": "<one-sentence factual claim>",
             "quote": "<short verbatim supporting quote from the source content>",
             "source_url": "<url of the source the quote came from>",
             "checklist_item": "<the checklist item this claim addresses>"}]}
Rules: only claims directly supported by the provided source content; source_url
must be one of the provided URLs; checklist_item must be one of the provided
items verbatim; no opinions, no scores, no speculation. Empty list if nothing
is supported."""


def tavily_search(query, max_results=5):
    resp = requests.post(
        TAVILY_URL,
        json={"api_key": os.environ["TAVILY_API_KEY"], "query": query,
              "max_results": max_results},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def build_extract_prompt(country_name, dimension, checklist, results):
    src = "\n\n".join(
        f"URL: {r['url']}\nTITLE: {r['title']}\nCONTENT: {r['content'][:1500]}"
        for r in results
    )
    items = "\n".join(f"- {i}" for i in checklist)
    return (f"Country: {country_name}\nDimension: {dimension}\n"
            f"Checklist items:\n{items}\n\nSearch results:\n{src}")


def parse_claims(llm_text, allowed_urls):
    data = extract_json(llm_text)
    out = []
    for c in data.get("claims", []):
        if not all(k in c for k in ("claim", "quote", "source_url", "checklist_item")):
            continue
        if c["source_url"] not in allowed_urls:
            continue
        out.append(c)
    return out


def coverage(checklist, claims):
    have = {c["checklist_item"] for c in claims}
    covered = [i for i in checklist if i in have]
    missing = [i for i in checklist if i not in have]
    return {"covered": covered, "missing": missing,
            "ratio": len(covered) / len(checklist)}


def collect_evidence(conn, run_id, extract_model):
    for country in COUNTRIES:
        name = COUNTRY_NAMES[country]
        for dim in DIMENSIONS:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM cgm_evidence"
                    " WHERE country_iso=%s AND dimension=%s",
                    (country, dim),
                )
                if cur.fetchone()[0] > 0:
                    continue  # pack already collected (immutable per corpus)
            checklist = checklist_for(dim, country)
            results, claims = [], []
            try:
                for item in checklist:
                    results.extend(tavily_search(f"{name} {item}"))
                if results:
                    prompt = build_extract_prompt(name, dim, checklist, results)
                    text = call_llm(extract_model, EXTRACT_SYSTEM, prompt,
                                    max_tokens=4000)
                    claims = parse_claims(text, {r["url"] for r in results})
            except Exception as err:  # noqa: BLE001 - log, gap, continue
                cgm_db.log_collection(conn, run_id, f"evidence:{country}:{dim}",
                                      "error", str(err))
            for c in claims:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO cgm_evidence (run_id, country_iso, dimension,
                           checklist_item, claim, quote, source_url, source_type)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, 'web')""",
                        (run_id, country, dim, c["checklist_item"], c["claim"],
                         c["quote"], c["source_url"]),
                    )
            conn.commit()
            cov = coverage(checklist, claims)
            for item in cov["missing"]:
                cgm_db.add_gap(conn, run_id, country, dim,
                               f"evidence missing for checklist item: {item}")
            cgm_db.log_collection(
                conn, run_id, f"evidence:{country}:{dim}", "ok",
                f"claims={len(claims)} coverage={cov['ratio']:.2f}",
            )
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_evidence.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_evidence.py tests/test_evidence.py
git commit -m "feat: Tavily+Claude evidence packs with coverage and anti-fabrication guard"
```

---

### Task 8: Rater panel — `cgm_raters.py`

**Files:**
- Create: `cgm/cgm_raters.py`
- Test: `tests/test_raters.py`

- [ ] **Step 1: Write the failing test** (`tests/test_raters.py`):

```python
import json
from unittest.mock import patch

import pytest

from cgm_raters import (
    RATER_A_SYSTEM, RATER_B_SYSTEM, build_rater_prompt, validate_rating,
)

EVIDENCE_ROWS = [
    {"evidence_id": 11, "checklist_item": "national AI strategy document",
     "claim": "UAE has a funded national AI strategy", "quote": "q",
     "source_url": "https://ai.gov.ae/strategy"},
]
ANCHOR_ROWS = [
    {"metric": "gdp_usd", "value": 500000000000.0, "unit": "USD", "year": 2025},
]


def test_prompts_are_structurally_different():
    # decorrelation: A is rubric-clause-first, B is evidence-first
    assert "level 5 down" in RATER_A_SYSTEM
    assert "summarize what the evidence establishes" in RATER_B_SYSTEM
    assert RATER_A_SYSTEM != RATER_B_SYSTEM


def test_build_rater_prompt_contains_rubric_evidence_anchors():
    prompt = build_rater_prompt("AE", "ai_policy", EVIDENCE_ROWS, ANCHOR_ROWS)
    assert "[11]" in prompt                      # evidence cited by ID
    assert "National AI strategy" in prompt      # rubric level text
    assert "gdp_usd" in prompt                   # anchors present
    assert "United Arab Emirates" in prompt


def test_validate_rating_accepts_good():
    rating = {"score": 5, "rubric_clause": "National AI strategy with...",
              "evidence_ids": [11], "rationale": "r"}
    assert validate_rating(rating, allowed_ids={11}) is None


@pytest.mark.parametrize("bad,msg", [
    ({"score": 6, "rubric_clause": "x", "evidence_ids": [11], "rationale": "r"},
     "score"),
    ({"score": 4, "rubric_clause": "x", "evidence_ids": [], "rationale": "r"},
     "evidence"),
    ({"score": 4, "rubric_clause": "x", "evidence_ids": [99], "rationale": "r"},
     "evidence"),
    ({"rubric_clause": "x", "evidence_ids": [11], "rationale": "r"}, "score"),
])
def test_validate_rating_rejects_bad(bad, msg):
    err = validate_rating(bad, allowed_ids={11})
    assert err is not None and msg in err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_raters.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_raters)

- [ ] **Step 3: Write `cgm/cgm_raters.py`**

```python
"""Two blind LLM raters. Same evidence pack, structurally different prompts
(deliberate decorrelation - both models are Anthropic siblings). A score that
cites no valid evidence IDs is re-requested once with the validation error;
on second failure it is stored NULL and flagged as a blocker gap."""
import json
import os

import cgm_db
from cgm_llm import call_llm, extract_json
from cgm_rubrics import COUNTRIES, COUNTRY_NAMES, DIMENSIONS, rubric_for

RATER_A_SYSTEM = """You are Rater A, scoring sovereign governance on a 1-5 rubric.
Method - rubric-clause-first: walk the rubric from level 5 down to level 1 and
select the FIRST level whose clause the cited evidence fully supports. You may
only rely on the evidence and anchors provided. Output STRICT JSON:
{"score": <int 1-5>, "rubric_clause": "<verbatim text of the level you matched>",
 "evidence_ids": [<ints - the [N] ids of evidence you relied on>],
 "rationale": "<2-4 sentences>"}
A score with no evidence_ids is invalid. Do not invent evidence."""

RATER_B_SYSTEM = """You are Rater B, scoring sovereign governance on a 1-5 rubric.
Method - evidence-first: first summarize what the evidence establishes about this
country and dimension, then decide which rubric level that picture maps onto.
You may only rely on the evidence and anchors provided. Output STRICT JSON:
{"score": <int 1-5>, "rubric_clause": "<verbatim text of the level you matched>",
 "evidence_ids": [<ints - the [N] ids of evidence you relied on>],
 "rationale": "<2-4 sentences>"}
A score with no evidence_ids is invalid. Do not invent evidence."""


def build_rater_prompt(country_iso, dimension, evidence_rows, anchor_rows):
    rubric = rubric_for(dimension, country_iso)
    rubric_txt = "\n".join(f"{lvl}: {txt}" for lvl, txt in sorted(rubric.items(),
                                                                  reverse=True))
    ev_txt = "\n".join(
        f"[{r['evidence_id']}] ({r['checklist_item']}) {r['claim']}"
        f' — "{r["quote"]}" ({r["source_url"]})'
        for r in evidence_rows
    ) or "(no qualitative evidence collected)"
    an_txt = "\n".join(
        f"- {r['metric']} = {r['value']} {r['unit']} ({r['year']})"
        for r in anchor_rows
    ) or "(no anchors)"
    return (f"Country: {COUNTRY_NAMES[country_iso]}\nDimension: {dimension}\n\n"
            f"RUBRIC:\n{rubric_txt}\n\nEVIDENCE:\n{ev_txt}\n\n"
            f"QUANTITATIVE ANCHORS:\n{an_txt}")


def validate_rating(rating, allowed_ids):
    score = rating.get("score")
    if not isinstance(score, int) or not 1 <= score <= 5:
        return f"invalid score: {score!r} (must be int 1-5)"
    ids = rating.get("evidence_ids")
    if not ids or not isinstance(ids, list):
        return "no evidence_ids cited - evidence citation is mandatory"
    if not set(ids) <= allowed_ids:
        return f"unknown evidence ids cited: {sorted(set(ids) - allowed_ids)}"
    return None


def load_pack(conn, country_iso, dimension):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT evidence_id, checklist_item, claim, quote, source_url"
            " FROM cgm_evidence WHERE country_iso=%s AND dimension=%s"
            " ORDER BY evidence_id",
            (country_iso, dimension),
        )
        evidence = [dict(zip(("evidence_id", "checklist_item", "claim", "quote",
                              "source_url"), row)) for row in cur.fetchall()]
        cur.execute(
            "SELECT metric, value, unit, year FROM cgm_raw_anchors"
            " WHERE country_iso=%s ORDER BY metric",
            (country_iso,),
        )
        anchors = [dict(zip(("metric", "value", "unit", "year"), row))
                   for row in cur.fetchall()]
    return evidence, anchors


def rate_one(model, system, country_iso, dimension, evidence, anchors):
    """Returns (rating_dict | None, error_str | None). One retry with feedback."""
    prompt = build_rater_prompt(country_iso, dimension, evidence, anchors)
    allowed = {r["evidence_id"] for r in evidence}
    err = None
    for attempt in range(2):
        suffix = f"\n\nYour previous output was invalid: {err}. Fix it." if err else ""
        try:
            rating = extract_json(call_llm(model, system, prompt + suffix))
        except (ValueError, RuntimeError) as parse_err:
            err = str(parse_err)
            continue
        err = validate_rating(rating, allowed)
        if err is None:
            return rating, None
    return None, err


def run_raters(conn, run_id):
    force = os.environ.get("CGM_RATE_FORCE") == "1"
    raters = [
        (os.environ.get("CGM_RATER_A_MODEL", "claude-sonnet-4-6"), RATER_A_SYSTEM),
        (os.environ.get("CGM_RATER_B_MODEL", "claude-opus-4-5"), RATER_B_SYSTEM),
    ]
    for country in COUNTRIES:
        for dim in DIMENSIONS:
            evidence, anchors = load_pack(conn, country, dim)
            for model, system in raters:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT score FROM cgm_rater_scores WHERE country_iso=%s"
                        " AND dimension=%s AND rater_model=%s",
                        (country, dim, model),
                    )
                    row = cur.fetchone()
                if row is not None and row[0] is not None and not force:
                    continue  # cached
                rating, err = rate_one(model, system, country, dim,
                                       evidence, anchors)
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO cgm_rater_scores (country_iso, dimension,
                           rater_model, score, rubric_clause, evidence_ids,
                           rationale, scored_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                           ON CONFLICT (country_iso, dimension, rater_model)
                           DO UPDATE SET score=EXCLUDED.score,
                             rubric_clause=EXCLUDED.rubric_clause,
                             evidence_ids=EXCLUDED.evidence_ids,
                             rationale=EXCLUDED.rationale, scored_at=now()""",
                        (country, dim, model,
                         rating["score"] if rating else None,
                         rating.get("rubric_clause") if rating else None,
                         rating.get("evidence_ids") if rating else None,
                         rating.get("rationale") if rating else err),
                    )
                conn.commit()
                if rating is None:
                    cgm_db.add_gap(conn, run_id, country, dim,
                                   f"rater {model} produced no valid score: {err}",
                                   severity="blocker")
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_raters.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_raters.py tests/test_raters.py
git commit -m "feat: blind 2-model rater panel with citation enforcement and caching"
```

---

### Task 9: Arbiter — `cgm_arbiter.py`

**Files:**
- Create: `cgm/cgm_arbiter.py`
- Test: `tests/test_arbiter.py`

- [ ] **Step 1: Write the failing test** (`tests/test_arbiter.py`):

```python
import json
from unittest.mock import patch

from cgm_arbiter import build_arbiter_prompt, needs_arbitration, parse_resolution


def test_needs_arbitration():
    assert needs_arbitration(2, 4) is True
    assert needs_arbitration(5, 2) is True
    assert needs_arbitration(3, 4) is False
    assert needs_arbitration(4, 4) is False


def test_build_arbiter_prompt_shows_both_raters():
    prompt = build_arbiter_prompt(
        "AE", "ai_policy",
        {"score": 5, "rationale": "ra", "rubric_clause": "c5"},
        {"score": 3, "rationale": "rb", "rubric_clause": "c3"},
        evidence_rows=[{"evidence_id": 1, "checklist_item": "i", "claim": "c",
                        "quote": "q", "source_url": "u"}],
        anchor_rows=[],
    )
    assert "Rater A" in prompt and "Rater B" in prompt
    assert "5" in prompt and "3" in prompt and "[1]" in prompt


def test_parse_resolution():
    out = parse_resolution(json.dumps(
        {"resolved_score": 4, "reasoning": "Rater A overweighted ..."}
    ))
    assert out == (4, "Rater A overweighted ...")


def test_parse_resolution_rejects_out_of_range():
    import pytest
    with pytest.raises(ValueError):
        parse_resolution(json.dumps({"resolved_score": 7, "reasoning": "x"}))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_arbiter.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_arbiter)

- [ ] **Step 3: Write `cgm/cgm_arbiter.py`**

```python
"""Third-LLM arbitration for rater divergences > 1 point. The arbiter sees both
raters' scores and rationales plus the same evidence pack, and must produce a
resolved score with written reasoning (the spec's 'structured discussion')."""
import json
import os

from cgm_llm import call_llm, extract_json
from cgm_raters import build_rater_prompt, load_pack
from cgm_rubrics import COUNTRIES, DIMENSIONS

ARBITER_SYSTEM = """You are the arbiter for a 2-rater governance scoring panel.
The raters diverged by more than 1 point. Review the rubric, the shared evidence,
and both raters' scores and rationales. Decide the better-supported score (it may
be either rater's score or one between them). Output STRICT JSON:
{"resolved_score": <int 1-5>, "reasoning": "<3-6 sentences explaining which
rater's reading of the evidence is better supported and why>"}"""


def needs_arbitration(score_a, score_b):
    return abs(score_a - score_b) > 1


def build_arbiter_prompt(country_iso, dimension, rating_a, rating_b,
                         evidence_rows, anchor_rows):
    base = build_rater_prompt(country_iso, dimension, evidence_rows, anchor_rows)
    return (f"{base}\n\n"
            f"Rater A scored {rating_a['score']} "
            f"(clause: {rating_a['rubric_clause']}) — {rating_a['rationale']}\n"
            f"Rater B scored {rating_b['score']} "
            f"(clause: {rating_b['rubric_clause']}) — {rating_b['rationale']}")


def parse_resolution(llm_text):
    data = extract_json(llm_text)
    score = data.get("resolved_score")
    if not isinstance(score, int) or not 1 <= score <= 5:
        raise ValueError(f"arbiter resolved_score invalid: {score!r}")
    return score, data.get("reasoning", "")


def run_arbiter(conn, run_id):
    model = os.environ.get("CGM_ARBITER_MODEL", "claude-opus-4-5")
    for country in COUNTRIES:
        for dim in DIMENSIONS:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rater_model, score, rubric_clause, rationale"
                    " FROM cgm_rater_scores WHERE country_iso=%s AND dimension=%s"
                    " AND score IS NOT NULL ORDER BY rater_model",
                    (country, dim),
                )
                rows = cur.fetchall()
            if len(rows) != 2:
                continue  # missing rater score -> already a blocker gap
            a, b = (dict(zip(("rater_model", "score", "rubric_clause",
                              "rationale"), r)) for r in rows)
            if not needs_arbitration(a["score"], b["score"]):
                continue
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM cgm_arbitrations WHERE country_iso=%s"
                    " AND dimension=%s", (country, dim),
                )
                if cur.fetchone():
                    continue  # already arbitrated
            evidence, anchors = load_pack(conn, country, dim)
            prompt = build_arbiter_prompt(country, dim, a, b, evidence, anchors)
            score, reasoning = parse_resolution(
                call_llm(model, ARBITER_SYSTEM, prompt)
            )
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO cgm_arbitrations (country_iso, dimension,
                       rater_a_score, rater_b_score, resolved_score,
                       arbiter_model, reasoning)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (country, dim, a["score"], b["score"], score, model,
                     reasoning),
                )
            conn.commit()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_arbiter.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_arbiter.py tests/test_arbiter.py
git commit -m "feat: third-LLM arbiter for >1-point rater divergences"
```

---

### Task 10: Scoring + sensitivity — `cgm_scoring.py`

**Files:**
- Create: `cgm/cgm_scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write the failing test** (`tests/test_scoring.py`):

```python
import math

import pytest

from cgm_scoring import combine_scores, composite, perturb_weights, sensitivity
from cgm_rubrics import WEIGHTS


def test_combine_equal():
    assert combine_scores(4, 4, None) == 4.0


def test_combine_adjacent_means():
    assert combine_scores(3, 4, None) == 3.5


def test_combine_divergent_uses_arbiter():
    assert combine_scores(2, 5, 4) == 4.0


def test_combine_divergent_without_arbiter_raises():
    with pytest.raises(ValueError):
        combine_scores(2, 5, None)


def test_composite_weighted():
    dims = {"ai_policy": 5, "permitting": 4, "value_capture": 4,
            "tech_stack": 5, "workforce": 3}
    expected = 0.25 * 5 + 0.20 * 4 + 0.20 * 4 + 0.20 * 5 + 0.15 * 3
    assert math.isclose(composite(dims), expected)


def test_perturb_weights_renormalizes():
    w = perturb_weights(WEIGHTS, "ai_policy", +0.10)
    assert math.isclose(sum(w.values()), 1.0)
    assert w["ai_policy"] > WEIGHTS["ai_policy"]


def test_sensitivity_detects_rank_change():
    # two countries, one dimension dominant: shifting weight flips ranking
    scores = {
        "AA": {"ai_policy": 5, "permitting": 1, "value_capture": 3,
               "tech_stack": 3, "workforce": 3},
        "BB": {"ai_policy": 1, "permitting": 5, "value_capture": 3,
               "tech_stack": 3, "workforce": 3},
    }
    report = sensitivity(scores)
    assert any(item["ranking_changed"] for item in report)
    assert {i["dimension"] for i in report} == set(WEIGHTS)
    assert {i["delta"] for i in report} == {0.10, -0.10}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_scoring.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_scoring)

- [ ] **Step 3: Write `cgm/cgm_scoring.py`**

```python
"""Final-score combination, weighted composite, and ±10pp weight sensitivity.
Pure functions + one DB writer. Combination rule (spec): equal -> score;
differ by 1 -> mean (half-points allowed); differ by >1 -> arbiter ruling."""
import json

from cgm_rubrics import ARCHETYPE, COUNTRIES, DIMENSIONS, WEIGHTS


def combine_scores(score_a, score_b, arbiter_score):
    if score_a == score_b:
        return float(score_a)
    if abs(score_a - score_b) == 1:
        return (score_a + score_b) / 2
    if arbiter_score is None:
        raise ValueError(
            f"divergence >1 ({score_a} vs {score_b}) with no arbitration row"
        )
    return float(arbiter_score)


def composite(dim_scores, weights=WEIGHTS):
    return sum(weights[d] * dim_scores[d] for d in weights)


def perturb_weights(weights, dimension, delta):
    w = dict(weights)
    w[dimension] = max(0.0, w[dimension] + delta)
    total = sum(w.values())
    return {k: v / total for k, v in w.items()}


def _ranking(country_dim_scores, weights):
    return sorted(country_dim_scores,
                  key=lambda c: composite(country_dim_scores[c], weights),
                  reverse=True)


def sensitivity(country_dim_scores, deltas=(0.10, -0.10)):
    baseline = _ranking(country_dim_scores, WEIGHTS)
    report = []
    for dim in WEIGHTS:
        for delta in deltas:
            w = perturb_weights(WEIGHTS, dim, delta)
            ranking = _ranking(country_dim_scores, w)
            report.append({
                "dimension": dim, "delta": delta,
                "ranking": ranking, "ranking_changed": ranking != baseline,
            })
    return report


def compute_final_scores(conn, run_id, rater_models):
    country_dims = {}
    for country in COUNTRIES:
        dims = {}
        for dim in DIMENSIONS:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rater_model, score FROM cgm_rater_scores"
                    " WHERE country_iso=%s AND dimension=%s AND score IS NOT NULL"
                    " ORDER BY rater_model", (country, dim),
                )
                rows = cur.fetchall()
                cur.execute(
                    "SELECT resolved_score FROM cgm_arbitrations"
                    " WHERE country_iso=%s AND dimension=%s", (country, dim),
                )
                arb = cur.fetchone()
            if len(rows) != 2:
                raise SystemExit(
                    f"cannot score: missing rater score for {country}/{dim}"
                    " (see cgm_data_gaps)"
                )
            dims[dim] = combine_scores(rows[0][1], rows[1][1],
                                       arb[0] if arb else None)
        country_dims[country] = dims
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cgm_score_final (run_id, country_iso, archetype,
                   ai_policy, permitting, value_capture, tech_stack, workforce,
                   cgm_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (run_id, country_iso) DO UPDATE SET
                     ai_policy=EXCLUDED.ai_policy, permitting=EXCLUDED.permitting,
                     value_capture=EXCLUDED.value_capture,
                     tech_stack=EXCLUDED.tech_stack, workforce=EXCLUDED.workforce,
                     cgm_score=EXCLUDED.cgm_score, computed_at=now()""",
                (run_id, country, ARCHETYPE[country], dims["ai_policy"],
                 dims["permitting"], dims["value_capture"], dims["tech_stack"],
                 dims["workforce"], composite(dims)),
            )
        conn.commit()
    sens = sensitivity(country_dims)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO cgm_score_methodology (run_id, weights, rater_models,
               sensitivity) VALUES (%s, %s, %s, %s)""",
            (run_id, json.dumps(WEIGHTS), json.dumps(rater_models),
             json.dumps(sens)),
        )
    conn.commit()
    return country_dims
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_scoring.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_scoring.py tests/test_scoring.py
git commit -m "feat: score combination, weighted composite, +/-10pp sensitivity"
```

---

### Task 11: QA gate — `cgm_verify.py`

**Files:**
- Create: `cgm/cgm_verify.py`
- Test: `tests/test_verify.py`

- [ ] **Step 1: Write the failing test** (`tests/test_verify.py`) — gate logic is pure; it takes pre-fetched data, returns failure strings:

```python
from cgm_verify import (
    check_arbitrations, check_completeness, check_evidence_citations,
    check_kappa_gate, check_score_ranges,
)


def kappa_row(dim, kappa, raw, degenerate=False):
    return {"dimension": dim, "kappa_linear": kappa, "degenerate": degenerate,
            "raw_agreement": raw}


def test_kappa_gate_passes_at_07():
    rows = [kappa_row(d, 0.7, 0.8) for d in
            ("ai_policy", "permitting", "value_capture", "tech_stack", "workforce")]
    assert check_kappa_gate(rows) == []


def test_kappa_gate_fails_below_07():
    rows = [kappa_row("ai_policy", 0.69, 0.8)]
    fails = check_kappa_gate(rows)
    assert len(fails) == 1 and "ai_policy" in fails[0]


def test_kappa_gate_degenerate_perfect_agreement_passes():
    assert check_kappa_gate([kappa_row("permitting", None, 1.0,
                                       degenerate=True)]) == []


def test_kappa_gate_degenerate_imperfect_fails():
    fails = check_kappa_gate([kappa_row("permitting", None, 0.5,
                                        degenerate=True)])
    assert len(fails) == 1


def test_completeness():
    full = [(c, d) for c in ("US", "AE", "BR", "IN", "SG", "PH")
            for d in ("ai_policy", "permitting", "value_capture",
                      "tech_stack", "workforce")]
    assert check_completeness(full) == []
    fails = check_completeness(full[:-1])
    assert len(fails) == 1 and "PH" in fails[0] and "workforce" in fails[0]


def test_evidence_citations():
    assert check_evidence_citations([("US", "ai_policy", [1, 2])]) == []
    fails = check_evidence_citations([("US", "ai_policy", None)])
    assert len(fails) == 1


def test_score_ranges():
    assert check_score_ranges([("US", 4.5)]) == []
    assert len(check_score_ranges([("US", 5.5)])) == 1


def test_arbitrations():
    # divergence >1 must have an arbitration row
    assert check_arbitrations([("US", "ai_policy", 2, 4)],
                              arbitrated={("US", "ai_policy")}) == []
    fails = check_arbitrations([("US", "ai_policy", 2, 4)], arbitrated=set())
    assert len(fails) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_verify.py -v`
Expected: FAIL (ModuleNotFoundError: cgm_verify)

- [ ] **Step 3: Write `cgm/cgm_verify.py`**

```python
"""CGM QA gate. Pure check_* functions return lists of failure strings; main()
fetches from the DB, runs every check, computes+stores kappa, prints a report,
and exits 1 on any failure. The master orchestrator runs this read-only."""
import sys

import cgm_db
from cgm_kappa import agreement_stats, linear_weighted_kappa
from cgm_rubrics import COUNTRIES, DIMENSIONS

KAPPA_GATE = 0.7


def check_kappa_gate(kappa_rows):
    fails = []
    for row in kappa_rows:
        if row["dimension"] == "pooled":
            continue  # reported, not gated
        if row["degenerate"]:
            if row["raw_agreement"] == 1.0:
                continue  # N/A (degenerate - perfect agreement, no variance)
            fails.append(
                f"kappa degenerate with imperfect agreement on {row['dimension']}"
                f" (raw={row['raw_agreement']:.2f})")
        elif row["kappa_linear"] is None or row["kappa_linear"] < KAPPA_GATE:
            fails.append(
                f"kappa below gate on {row['dimension']}:"
                f" {row['kappa_linear']} < {KAPPA_GATE}")
    return fails


def check_completeness(country_dim_pairs):
    have = set(country_dim_pairs)
    return [f"missing final score: {c}/{d}"
            for c in COUNTRIES for d in DIMENSIONS if (c, d) not in have]


def check_evidence_citations(rater_rows):
    return [f"score without evidence citation: {c}/{d}"
            for c, d, ids in rater_rows if not ids]


def check_score_ranges(final_rows):
    return [f"cgm_score out of [1,5]: {c}={s}"
            for c, s in final_rows if not 1 <= float(s) <= 5]


def check_arbitrations(divergent_pairs, arbitrated):
    return [f"unresolved >1pt divergence: {c}/{d} ({a} vs {b})"
            for c, d, a, b in divergent_pairs if (c, d) not in arbitrated]


def compute_and_store_kappa(conn, run_id):
    """Per-dimension + pooled kappa over the two raters' scores."""
    rows_out = []
    pooled_a, pooled_b = [], []
    for dim in DIMENSIONS:
        a, b = [], []
        for country in COUNTRIES:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT score FROM cgm_rater_scores WHERE country_iso=%s"
                    " AND dimension=%s AND score IS NOT NULL ORDER BY rater_model",
                    (country, dim),
                )
                scores = [r[0] for r in cur.fetchall()]
            if len(scores) == 2:
                a.append(scores[0])
                b.append(scores[1])
        if not a:
            continue
        pooled_a += a
        pooled_b += b
        rows_out.append((dim, a, b))
    rows_out.append(("pooled", pooled_a, pooled_b))

    stored = []
    for dim, a, b in rows_out:
        kappa = linear_weighted_kappa(a, b)
        stats = agreement_stats(a, b)
        degenerate = kappa is None
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cgm_kappa_results (run_id, dimension, kappa_linear,
                   degenerate, raw_agreement, adjacent_agreement, n)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (run_id, dim, kappa, degenerate, stats["raw_agreement"],
                 stats["adjacent_agreement"], stats["n"]),
            )
        conn.commit()
        stored.append({"dimension": dim, "kappa_linear": kappa,
                       "degenerate": degenerate,
                       "raw_agreement": stats["raw_agreement"]})
    return stored


def main(run_id=None):
    conn = cgm_db.connect()
    if run_id is None:
        with conn.cursor() as cur:
            cur.execute("SELECT run_id FROM cgm_runs ORDER BY started_at DESC"
                        " LIMIT 1")
            row = cur.fetchone()
        if row is None:
            print("VERIFY FAIL: no runs found")
            sys.exit(1)
        run_id = row[0]

    kappa_rows = compute_and_store_kappa(conn, run_id)

    with conn.cursor() as cur:
        cur.execute("SELECT country_iso, dimension FROM cgm_rater_scores"
                    " WHERE score IS NOT NULL"
                    " GROUP BY country_iso, dimension HAVING count(*) = 2")
        pairs = cur.fetchall()
        cur.execute("SELECT country_iso, dimension, evidence_ids"
                    " FROM cgm_rater_scores WHERE score IS NOT NULL")
        rater_rows = cur.fetchall()
        cur.execute("SELECT country_iso, cgm_score FROM cgm_score_final"
                    " WHERE run_id=%s", (run_id,))
        final_rows = cur.fetchall()
        cur.execute(
            """SELECT a.country_iso, a.dimension, a.score, b.score
               FROM cgm_rater_scores a JOIN cgm_rater_scores b
                 ON a.country_iso=b.country_iso AND a.dimension=b.dimension
                AND a.rater_model < b.rater_model
               WHERE abs(a.score - b.score) > 1""")
        divergent = cur.fetchall()
        cur.execute("SELECT country_iso, dimension FROM cgm_arbitrations")
        arbitrated = set(cur.fetchall())

    failures = (
        check_kappa_gate(kappa_rows)
        + check_completeness(pairs)
        + check_evidence_citations(rater_rows)
        + check_score_ranges(final_rows)
        + check_arbitrations(divergent, arbitrated)
    )
    if not final_rows:
        failures.append("no final scores for latest run - scoring phase not run")

    print("=== CGM VERIFY ===")
    for row in kappa_rows:
        kappa_txt = ("N/A (degenerate - perfect agreement)"
                     if row["degenerate"] and row["raw_agreement"] == 1.0
                     else str(row["kappa_linear"]))
        print(f"kappa[{row['dimension']}] = {kappa_txt}"
              f" raw={row['raw_agreement']:.2f}")
    if failures:
        print(f"\nFAIL ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nPASS")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_verify.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add cgm/cgm_verify.py tests/test_verify.py
git commit -m "feat: QA gate - kappa/completeness/citations/ranges/arbitrations, exit 1 on fail"
```

---

### Task 12: Gap report — `cgm_gap_report.py`

**Files:**
- Create: `cgm/cgm_gap_report.py`

No unit test (pure presentation over SQL; covered by the live run in Task 13).

- [ ] **Step 1: Write `cgm/cgm_gap_report.py`**

```python
"""Print open data gaps and evidence-pack coverage. Informational - never exits 1."""
import cgm_db
from cgm_evidence import coverage
from cgm_rubrics import COUNTRIES, DIMENSIONS, checklist_for


def main():
    conn = cgm_db.connect()
    print("=== CGM GAP REPORT ===\n-- data gaps --")
    with conn.cursor() as cur:
        cur.execute("SELECT severity, country_iso, dimension, gap FROM"
                    " cgm_data_gaps ORDER BY severity DESC, country_iso")
        rows = cur.fetchall()
    for sev, country, dim, gap in rows:
        print(f"[{sev}] {country or '-'}/{dim or '-'}: {gap}")
    if not rows:
        print("(none)")

    print("\n-- evidence coverage --")
    for country in COUNTRIES:
        for dim in DIMENSIONS:
            with conn.cursor() as cur:
                cur.execute("SELECT checklist_item FROM cgm_evidence"
                            " WHERE country_iso=%s AND dimension=%s",
                            (country, dim))
                claims = [{"checklist_item": r[0]} for r in cur.fetchall()]
            cov = coverage(checklist_for(dim, country), claims)
            flag = "" if cov["ratio"] == 1 else f"  missing: {cov['missing']}"
            print(f"{country}/{dim}: {cov['ratio']:.0%}{flag}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-run against the provisioned (empty) DB**

Run: `cd cgm && ../.venv/bin/python cgm_gap_report.py`
Expected: `=== CGM GAP REPORT ===`, `(none)`, all coverage lines `0%` — no traceback

- [ ] **Step 3: Commit**

```bash
git add cgm/cgm_gap_report.py
git commit -m "feat: gap report - open gaps and evidence coverage"
```

---

### Task 13: Orchestrator — `run_cgm.py` + first live run

**Files:**
- Create: `cgm/run_cgm.py`

- [ ] **Step 1: Write `cgm/run_cgm.py`**

```python
"""CGM pipeline orchestrator.
Usage: python run_cgm.py [--only anchors|evidence|rate|arbitrate|score|verify|gap]
Phases run in order by default. verify exits 1 on gate failure."""
import argparse
import os

import cgm_db
import cgm_anchors
import cgm_arbiter
import cgm_evidence
import cgm_gap_report
import cgm_raters
import cgm_scoring
import cgm_verify

PHASES = ["anchors", "evidence", "rate", "arbitrate", "score", "verify", "gap"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=PHASES)
    args = parser.parse_args()
    phases = [args.only] if args.only else PHASES

    conn = cgm_db.connect()
    run_id = cgm_db.start_run(conn)
    print(f"run {run_id}: phases={phases}")

    rater_models = {
        "rater_a": os.environ.get("CGM_RATER_A_MODEL", "claude-sonnet-4-6"),
        "rater_b": os.environ.get("CGM_RATER_B_MODEL", "claude-opus-4-5"),
        "arbiter": os.environ.get("CGM_ARBITER_MODEL", "claude-opus-4-5"),
    }
    extract_model = rater_models["rater_a"]

    for phase in phases:
        print(f"--- phase: {phase}")
        cgm_db.log_phase(conn, run_id, phase)
        if phase == "anchors":
            cgm_anchors.collect_anchors(conn, run_id)
        elif phase == "evidence":
            cgm_evidence.collect_evidence(conn, run_id, extract_model)
        elif phase == "rate":
            cgm_raters.run_raters(conn, run_id)
        elif phase == "arbitrate":
            cgm_arbiter.run_arbiter(conn, run_id)
        elif phase == "score":
            cgm_scoring.compute_final_scores(conn, run_id, rater_models)
        elif phase == "verify":
            cgm_db.finish_run(conn, run_id)
            cgm_verify.main(run_id)  # may sys.exit(1)
        elif phase == "gap":
            cgm_gap_report.main()
    cgm_db.finish_run(conn, run_id)
    print("done")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Full test suite green before the live run**

Run: `.venv/bin/python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 3: Commit the orchestrator**

```bash
git add cgm/run_cgm.py
git commit -m "feat: run_cgm orchestrator with --only phase control"
```

- [ ] **Step 4: First live run** (requires `.env` filled; costs a few dollars of API)

Run: `cd cgm && ../.venv/bin/python run_cgm.py 2>&1 | tee cgm_run.log`
Expected: all phases run; `verify` prints per-dimension kappa and PASS/FAIL. A FAIL on the kappa gate is a **valid data-quality outcome, not a code bug** — record it, do not weaken the gate (WS3 precedent).

- [ ] **Step 5: Inspect outputs and record the result**

Run: `cd cgm && ../.venv/bin/python -c "import cgm_db; conn=cgm_db.connect(); cur=conn.cursor(); cur.execute('SELECT * FROM v_cgm_latest'); [print(r) for r in cur.fetchall()]"`
Expected: 6 rows, ranked, `cgm_score` in [1,5]. Note kappa values + any gate failures in the commit message.

- [ ] **Step 6: Commit run log**

```bash
git add cgm/cgm_run.log
git commit -m "data: first live CGM run - <PASS/FAIL summary, kappa per dimension>"
```

---

### Task 14: Methodology paper + CI + push

**Files:**
- Create: `docs/CGM_METHODOLOGY.md`, `.github/workflows/ci.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements.txt
      - run: python -m pytest -v
```

- [ ] **Step 2: Write `docs/CGM_METHODOLOGY.md`** — executable-spec standard. Required sections, each with real content drawn from the code and the first live run (no TBDs):

1. **Purpose & formula** — CGM definition, weights, role as multiplier in CSI.
2. **Rubrics** — all five, verbatim (copy from `cgm_rubrics.py`), archetype split for value_capture with the country assignment.
3. **Evidence methodology** — anchor indicator table (the 6 World Bank indicators with exact API URLs from `cgm_anchors.WB_URL`), Tavily search procedure, claim-extraction prompt (copy `EXTRACT_SYSTEM`), anti-fabrication URL guard, coverage measurement.
4. **Rater protocol** — both system prompts verbatim, models + temperature=0 rationale (Opus 4.5 accepts sampling params; 4.7/4.8 reject them), blindness, citation enforcement, caching/force semantics.
5. **Reliability** — linear-weighted kappa formula, the degeneracy rule and why N=6 makes it necessary, pooled kappa, arbiter protocol with prompt verbatim, combination rule.
6. **Results of first run** — kappa per dimension, arbitration count, final scores table (from `v_cgm_latest`), sensitivity table (from `cgm_score_methodology.sensitivity`).
7. **Decisions log** — for each: what/why/alternatives/sensitivity impact. Minimum entries: LLM raters replace human raters (agentic-by-design; never-run human protocol in WS3 as precedent); two Anthropic siblings + prompt decorrelation vs a non-Anthropic rater (no key available; correlation limitation); evidence packs frozen before rating; arbiter may not split ±1 divergences.
8. **Limitations** — N=6 kappa fragility; correlated raters; evidence recency (web search snapshot); coverage gaps (cite actual `cgm_data_gaps` rows); single-period (no CGM trajectory yet).

- [ ] **Step 3: Run full suite once more**

Run: `.venv/bin/python -m pytest -v`
Expected: all PASS

- [ ] **Step 4: Commit and push**

```bash
git add docs/CGM_METHODOLOGY.md .github/workflows/ci.yml
git commit -m "docs: CGM methodology paper; ci: pytest workflow"
git push -u origin main
```

Expected: push succeeds to `github.com/rsm-sdeenadayalan/gramercy-workstream-4`; CI green.

---

## Self-review (done at planning time)

- **Spec coverage:** rubrics/weights/archetypes (T3), anchors+evidence+coverage+anti-fabrication (T6–7), blind decorrelated raters + citation enforcement + caching (T8), arbiter (T9), combination+composite+sensitivity (T10), kappa with degeneracy rule + pooled (T4, T11), QA gate incl. all six spec checks (T11), gap report (T12), orchestrator phases (T13), provenance everywhere (T2 schema, T6–7 writers), methodology paper + CI + push (T14). `v_cgm_latest` matches the integration contract (country_iso, sub-scores, composite, computed_at, rank).
- **Type consistency:** dimension keys, `rubric_for`/`checklist_for` signatures, evidence-row dict shape (`evidence_id/checklist_item/claim/quote/source_url`), and `(rating, err)` tuple from `rate_one` are used consistently across Tasks 7–11.
- **Placeholder scan:** none; every code step has complete code. The methodology doc step lists exact sections with the concrete content source for each.
