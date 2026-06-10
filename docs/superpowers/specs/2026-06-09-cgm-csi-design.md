# WS4 (CGM) + Master CSI Deployment — Design

**Date:** 2026-06-09
**Status:** Approved (user, 2026-06-09)
**Source spec:** "UCSD Capstone CSI Project" scope document (sponsor PDF), Workstream 4
section + Integration section.

## Goal

Build the fourth and final index of the Chessboard Sovereign Index (CSI):

1. **CGM — Chessboard Governance Multiplier** (`gramercy-workstream-4` repo): score
   6 countries (US, AE, BR, IN, SG, PH) on 5 governance dimensions using structured
   1–5 rubrics, an LLM rater panel replacing the spec's human 2-rater protocol, a
   Cohen's-kappa QA gate, and evidence-cited scores stored in a new `cgm` Postgres DB.
2. **CSI integration** (`gramercy-csi` repo): a master deployment repo that
   bootstraps/runs all four workstream pipelines and computes the unified index
   **CSI = (SDI + CII − CLDV) × CGM** with the sensitivity analysis the spec requires.

Both repos follow the project's design principles: agentic by design (no human in the
loop), no trained models (rubrics + formulas + LLM prompts only), full data
provenance, methodology written as executable specification.

## Decisions made (with user)

| Decision | Choice |
|---|---|
| WS4 location | New repo `github.com/rsm-sdeenadayalan/gramercy-workstream-4` |
| Rater design | **LLM rater panel**: 2 independent models score blind from a shared evidence pack; Cohen's kappa ≥ 0.7 gate per dimension |
| Evidence | **APIs + agentic research**: quantitative anchors from free structured APIs; qualitative evidence packs via Claude+Tavily research agent; every claim has source URL + collection date |
| Scope | CGM **and** CSI integration |
| Deployment | Master repo `gramercy-csi` orchestrates WS1–WS4 + integration; workstream repos cloned as siblings, pinned via `versions.lock` (no submodules) |
| Divergence resolution | **Third-LLM arbiter** with documented reasoning |

## Context: upstream state (verified 2026-06-09)

Shared Postgres server hosts all workstream DBs. Final-score views, joinable on
`country_iso`, all six countries present:

- `gramercy_workstream1.v_sdi_ranked` — SDI 0–100 (energy/water/minerals/food).
  **Known gap:** minerals sub-index is 0.00 for every country; inherited and
  documented, not fixed here.
- `cii.v_cii_latest_scores` — CII 0–100 (capacity/velocity/quality).
- `cldv.v_cldv_latest_scores` — CLDV 0–100 (corporate/labor/services).
  **Known gap:** WS3 SI1 scorer-vs-judge concordance is 66.2% vs its 80% gate;
  CLDV is consumed as-is and the limitation is documented in the CSI paper.
- `cgm.v_cgm_latest` — to be created by this project (CGM 0–5).

Workstream entry points the master orchestrator invokes:
WS1 `run_all.py`, WS2 `cii/run_cii.py`, WS3 `cldv/run_cldv.py`, WS4 `cgm/run_cgm.py`.

GitHub repos: `gramercy-workstream-1`, `gramercy-workstream-2`,
`gramercy-workstream-3`, `gramercy-workstream-4` (empty), `gramercy-csi` (to create),
all under `rsm-sdeenadayalan`.

---

# Part 1 — CGM (`gramercy-workstream-4`)

## Layout (mirrors WS3 conventions)

```
cgm/
  setup_cgm.py        # create `cgm` DB on shared server + apply schema
  cgm_schema.sql      # tables + views (below)
  cgm_anchors.py      # quantitative anchors from free structured APIs
  cgm_evidence.py     # agentic evidence packs (Claude + Tavily)
  cgm_raters.py       # 2-model blind rater panel
  cgm_arbiter.py      # third-LLM divergence resolution
  cgm_kappa.py        # Cohen's kappa + agreement stats
  cgm_scoring.py      # weighted CGM composite + sensitivity
  cgm_verify.py       # QA gate (exit 1 on failure)
  cgm_gap_report.py   # open-gaps report
  run_cgm.py          # orchestrator: --only anchors|evidence|rate|arbitrate|score|verify|gap
tests/                # pytest
docs/CGM_METHODOLOGY.md
.env.example          # POSTGRES_*, ANTHROPIC_API_KEY, TAVILY_API_KEY, CGM_* knobs
requirements.txt
```

## Dimensions, weights, and rubrics

**CGM = 0.25×D1 + 0.20×D2 + 0.20×D3 + 0.20×D4 + 0.15×D5**, each dimension scored
1–5, composite reported on 0–5 scale (1–5 rubric output used directly; no further
rescaling — "normalized to 0–5" in the spec is satisfied because the composite of
1–5 scores lies in [1,5] ⊂ [0,5]).

Rubrics are encoded **verbatim from the sponsor PDF** as structured decision rules
in both the rater prompts and `docs/CGM_METHODOLOGY.md`:

### D1 — AI Policy Posture (25%)
- 5: National AI strategy with dedicated funding, minimal regulatory friction, explicit goal of AI leadership
- 4: Active strategy, moderate funding, generally permissive regulation, proactive investment incentives
- 3: Strategy exists but implementation uneven, mixed regulatory signals, moderate compliance burden
- 2: Heavy regulatory framework creating significant compliance costs and deployment delays
- 1: Restrictive or punitive regulation, no coherent strategy, active barriers to deployment

Evidence required: national AI strategy document; dedicated AI budget (USD and % of
GDP); estimated time from AI system development to legal deployment; tax
incentives/disincentives; regulatory sandbox count and scope; national AI
coordinating body existence and mandate.

### D2 — Infrastructure Permitting Speed (20%)
- 5: Fast-track permitting, weeks-to-months cycles, government actively facilitates
- 4: Streamlined, 3–12 months, clear pathway, limited opposition mechanisms
- 3: Standard, 12–24 months, multiple agencies, some community opposition
- 2: Slow, 24–48 months, complex multi-stakeholder, frequent legal challenges
- 1: Gridlock, 48+ months, unpredictable, regulatory capture by incumbents

Evidence required: average permitting timeline for data centers and power generation;
announced vs. completed projects (3-year completion ratio); special economic zones or
fast-track frameworks; documented delays or cancellations.

### D3 — Resource Value Capture Capacity (20%) — archetype-split rubric

For **substrate nations (US, AE, BR)**:
- 5: Stable resource taxation; sovereign wealth fund; active conversion of resource revenue into compute; strong anti-corruption checks
- 4: Generally stable regime; some safeguards; growing but uneven compute conversion
- 3: Unstable regime; resource nationalism risk; corruption siphons value; compute conversion throttled by governance
- 2: High corruption, opaque contracts, weak controls, minimal compute conversion despite endowment
- 1: Conflict-affected extraction, kleptocratic governance, zero value capture

For **processor nations (SG, IN, PH)**:
- 5: Large fiscal reserves; active retraining at scale; demonstrated history of economic pivots; actively building compute to offset services decline
- 4: Adequate fiscal position; some retraining; moderate diversification; some compute investment
- 3: Limited fiscal buffer; unproven retraining; high services dependence; minimal compute
- 2: Weak fiscal position; no transition strategy; very high concentration in vulnerable services
- 1: No buffer, no plan, total dependence on single vulnerable sector

(Archetype assignment per the spec's own examples: substrate = US, UAE, Brazil;
processor = Singapore, India, Philippines. Stored on the score row.)

### D4 — Technology Stack Alignment (20%)
- 5: Deep integration with leading stack; secure advanced chip access; hosting critical AI infrastructure
- 4: Good access; some chip dependency but manageable; growing hyperscaler presence
- 3: Dual-alignment with long-term uncertainty; or moderate access to one stack with limited depth
- 2: Peripheral to both stacks; limited chip access; no hyperscaler presence
- 1: Technology-denied or self-isolated; sanctioned; no AI infrastructure

Evidence required: chip import access by generation; hyperscaler commitments (list
and USD); technology alliance participation; bilateral tech agreements; domestic AI
model capability.

### D5 — Workforce Adaptability (15%)
- 5: World-class education, high digital literacy, extensive retraining, young demographics, English proficiency, strong STEM pipeline
- 4: Good education, above-average digital literacy, functioning retraining, favorable demographics
- 3: Average education, moderate digital literacy, limited retraining, mixed demographics
- 2: Weak education, low digital literacy, minimal retraining, unfavorable demographics
- 1: Education in crisis, very low digital literacy, no retraining, demographic headwinds

Evidence (anchors): OECD PISA scores, ITU digital-literacy/ICT development metrics,
World Bank Human Capital Index, UN Population demographic projections, plus
qualitative retraining-program evidence.

## Evidence pipeline

Two layers, both with full provenance (source URL, accessed-at date, raw payload
preserved):

1. **Quantitative anchors** (`cgm_anchors.py`) from free structured sources into
   `cgm_raw_anchors`: World Bank API (Human Capital Index, education, demographics,
   GDP for budget-%-of-GDP), UNESCO/PISA education statistics, ITU ICT indicators,
   UN population projections, OECD AI Policy Observatory (policy counts/links).
   Collector failures are logged to `cgm_collection_log`, recorded in
   `cgm_data_gaps`, and never crash the run.
2. **Qualitative evidence packs** (`cgm_evidence.py`): one pack per
   country×dimension (30 packs). A Claude+Tavily research agent (same pattern as the
   WS1/WS3 research agents) searches for the spec's "Evidence required" items
   (strategy docs, permitting cases, completion ratios, chip-access status,
   hyperscaler commitments, retraining programs), and stores each claim as a row in
   `cgm_evidence` with quote/summary, source URL, source type, and access date.
   Packs are immutable per run; raters see the pack, not the live web.

## Rater panel

- **Rater A:** `claude-sonnet-4-6`, `temperature=0`.
- **Rater B:** `claude-opus-4-5`, `temperature=0` (Opus 4.5 accepts sampling params;
  4.7/4.8 reject `temperature` — same determinism rationale as WS3's judge).
- Each rater independently scores all 6 countries × 5 dimensions from the identical
  evidence pack (anchors + qualitative claims), blind to the other rater.
- Output per (country, dimension): integer score 1–5, the rubric clause matched,
  and the IDs of the specific `cgm_evidence` / `cgm_raw_anchors` rows relied on.
  **A score citing no evidence rows is rejected and re-requested; on second failure
  it is stored as NULL and flagged in `cgm_data_gaps` (verify will fail).**
- Caching: only (country, dimension, rater) rows with NULL scores are re-rated
  unless `CGM_RATE_FORCE=1`. Estimated one-time cost: 30 evidence packs + 60 rater
  calls + arbitrations — a few dollars.

## Agreement, arbitration, final scores

- `cgm_kappa.py` computes **linear-weighted Cohen's kappa per dimension** across the
  6 countries, plus raw agreement and adjacent (±1) agreement. Kappa at N=6 is
  statistically fragile — reported with that caveat; the gate still applies as the
  spec demands.
- **Divergence > 1 point** → `cgm_arbiter.py`: a third LLM call (Opus 4.5, distinct
  arbiter prompt) sees both raters' scores + rationales + the evidence pack and
  issues a resolved score with written reasoning → `cgm_arbitrations` (the spec's
  "divergences documented with evidence and resolved through structured discussion").
- **Final dimension score:** raters equal → that score; differ by 1 → mean (half
  points allowed); differ by >1 → arbiter's ruling.
- `cgm_scoring.py` computes the weighted composite per country, runs ±10pp weight
  sensitivity (does the country ranking change when any dimension weight shifts
  ±10pp, renormalized?), and writes `cgm_score_final` + methodology row.

## QA gate (`cgm_verify.py`, exit 1 on any failure)

1. Linear-weighted kappa ≥ 0.7 for **each** of the 5 dimensions.
2. Every final score has ≥1 evidence citation.
3. All 6 countries × 5 dimensions have final scores.
4. Dimension weights sum to 1.0; every final score within [1, 5].
5. Every divergence >1 point has an arbitration row.

## Schema (`cgm` database)

```
cgm_runs                (run_id, started_at, phase log)
cgm_collection_log      (source, status, detail, ts)
cgm_raw_anchors         (country_iso, metric, value, unit, source_url, accessed_at, raw_payload)
cgm_evidence            (evidence_id, country_iso, dimension, claim, quote, source_url,
                         source_type, accessed_at, run_id)
cgm_rater_scores        (country_iso, dimension, rater_model, score, rubric_clause,
                         evidence_ids[], rationale, scored_at)
cgm_arbitrations        (country_iso, dimension, rater_a_score, rater_b_score,
                         resolved_score, arbiter_model, reasoning, ts)
cgm_kappa_results       (dimension, kappa_linear, raw_agreement, adjacent_agreement, n)
cgm_score_final         (country_iso, archetype, d1..d5 final scores, cgm_score 0–5,
                         run_id, computed_at)
cgm_score_methodology   (weights, model ids, prompt versions, sensitivity results)
cgm_data_gaps           (country_iso, dimension, gap description, severity)
v_cgm_latest            (country_iso, d1..d5, cgm, rank)  -- the integration interface
```

## Testing (pytest, WS3 conventions)

- Rubric encoding: every dimension exposes 5 reachable levels; archetype routing
  correct for all 6 countries.
- Kappa math vs hand-computed fixtures (perfect agreement → 1.0; known table →
  known value; weighted vs unweighted distinction).
- Arbiter trigger logic (≤1 no, >1 yes), final-score combination rules.
- Scoring formula, weight normalization, sensitivity reshuffle detection.
- Verify gate: each failure mode trips exit 1 on synthetic fixtures.
- Evidence-citation rejection path.
- No live-API calls in tests; collectors and LLM clients mocked.

## CGM methodology paper (`docs/CGM_METHODOLOGY.md`)

Executable-spec standard: every decision documented as (what / why / alternatives /
sensitivity impact); exact source URLs and API endpoints; rubrics verbatim; rater
and arbiter prompts included; limitations section (N=6 kappa fragility, LLM raters
replacing humans and why, evidence-pack recency, anchor gaps).

---

# Part 2 — Master deployment (`gramercy-csi`)

## Layout

```
bootstrap.sh          # clone/update 4 workstream repos as siblings at pinned SHAs,
                      # create merged venv, run each setup_*.py (idempotent)
versions.lock         # repo -> commit SHA pins
run_csi.py            # master orchestrator
csi/
  csi_schema.sql      # csi DB: csi_runs, csi_inputs (snapshot of 4 indices),
                      #   csi_scores, csi_sensitivity, v_csi_ranked
  csi_integrate.py    # read the 4 views -> normalize -> CSI per country
  csi_sensitivity.py  # weight perturbation + structure tests
  csi_verify.py       # gate: 6 countries, all 4 inputs present, math reproducible
docs/CSI_INTEGRATION.md
.env.example, requirements.txt
tests/
```

## Orchestration

`run_csi.py` runs, in order: WS1 `run_all.py` → WS2 `cii/run_cii.py` → WS3
`cldv/run_cldv.py` → WS4 `cgm/run_cgm.py` → `csi_integrate` → `csi_verify`.
Each workstream is skippable (`--skip ws1`) or runnable alone (`--only ws4`,
`--only integrate`); `--collect-only` style flags pass through where the underlying
pipeline supports them. A workstream failure halts before integration unless
`--keep-going`, in which case integration runs on the latest existing DB state and
flags staleness. Each phase's exit code and duration are logged to `csi_runs`.

## Integration math

1. Snapshot the four views into `csi_inputs` (provenance: source DB, view,
   `computed_at`).
2. Normalize: SDI, CII, CLDV ÷ 20 → 0–5; CGM already 0–5.
3. **CSI = (SDI + CII − CLDV) × CGM** per country; rank.
4. Also emit: S-C Gap (SDI − CII, 0–5 scale, matching WS2's definition);
   CLDV-acceleration and CGM-trajectory marked "requires ≥2 scoring periods —
   single-period baseline established here".
5. Compare sign/ordering against the spec's Expected Positioning table
   (US strong-positive, AE strong-positive, BR positive-discounted, IN near-zero,
   SG negative-buffered, PH strong-negative) and report agreements/divergences —
   a sanity check, not a gate (the data decides, not the prior).

## Sensitivity analysis (spec Integration Requirements)

- Within-workstream: shift each sub-index weight ±10pp (renormalize), recompute CSI,
  report any ranking changes.
- Structural: additive `SDI + CII` vs multiplicative `SDI × CII` variant — do
  rankings differ?
- CGM influence: CSI with CGM exponent/weight doubled and halved
  (`(S+C−L) × CGM^k`, k ∈ {0.5, 1, 2}) — ranking stability.
- All results stored in `csi_sensitivity` and tabulated in the integration doc.

## CSI integration doc (`docs/CSI_INTEGRATION.md`)

Methodology, normalization choices and why, full sensitivity tables, validation
against expected positioning, limitations (WS1 minerals gap = 0.00 uniformly;
WS3 SI1 concordance 66.2% pending calibration; CGM single-period; N=6).

---

# Cross-cutting

- **Secrets:** `.env` per repo (`POSTGRES_*`, `ANTHROPIC_API_KEY`,
  `TAVILY_API_KEY`); `.env.example` committed, `.env` git-ignored.
- **CI:** GitHub Actions pytest workflow in both repos (mirrors WS3 `ci.yml`).
- **Git:** WS4 and gramercy-csi each a clean repo pushed to the confirmed GitHub
  remotes; feature-branch + merge to main, following WS3 history conventions.

# Deliverables checklist (maps to sponsor spec)

1. **CGM Database** — all dimension scores, evidence citations, composite multiplier
   for 6 countries (`cgm` DB).
2. **CGM Methodology Paper** — `docs/CGM_METHODOLOGY.md`.
3. **Unified CSI** — ranking + sensitivity + integration methodology
   (`csi` DB + `docs/CSI_INTEGRATION.md`), per Integration Requirements 1–4.
4. **Complete deployment** — `gramercy-csi` bootstrap + master orchestrator running
   WS1→WS4→integration end-to-end.

# Out of scope

- Fixing WS1's minerals sub-index or WS3's SI1 calibration (documented as inherited
  limitations; SI1 calibration remains the next WS3 task).
- Time-series CGM trajectory / CLDV acceleration (needs a second scoring period).
- Any human rating workflow.
