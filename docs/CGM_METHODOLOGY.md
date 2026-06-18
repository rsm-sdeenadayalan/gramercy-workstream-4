# CGM Methodology — Chessboard Governance Multiplier

**Workstream 4, Chessboard Sovereign Index (CSI) project.**
**Status of first run (2026-06-09): QA gate FAIL — CGM is PROVISIONAL (see §7).**

This document is the methodology paper for the CGM index, written to the
executable-specification standard: an agent with no prior exposure to this
repository must be able to reproduce the index from this document alone. All
prompts, rubrics, formulas, and URLs below are quoted verbatim from the code,
which is the source of truth (`cgm/*.py`, `cgm/cgm_schema.sql`).

---

## 1. Purpose & formula

CGM (Chessboard Governance Multiplier) is the multiplicative governance term in
the unified index:

```
CSI = (SDI + CII − CLDV) × CGM
```

SDI, CII, CLDV are produced by workstreams 1–3 (each 0–100, normalized ÷20 to
0–5 at integration). CGM scores how well a country's governance converts its
sovereign endowment into AI-era position; it scales the whole bracket, so a
weak CGM discounts strong fundamentals and a strong CGM amplifies them.

Six countries: **US, AE, BR, IN, SG, PH** (ISO-3166 alpha-2). Five dimensions,
each scored on a 1–5 rubric; the composite is the weighted sum, reported on a
0–5 scale (the composite of 1–5 scores lies in [1,5] ⊂ [0,5]; no rescaling):

```
CGM = 0.25×ai_policy + 0.20×permitting_standard + 0.00×permitting_fasttrack
    + 0.20×value_capture + 0.20×tech_stack + 0.15×workforce
```

| dimension | weight | name |
|---|---|---|
| `ai_policy` | 0.25 | AI Policy Posture |
| `permitting_standard` | 0.20 | Infrastructure Permitting Speed — default path |
| `permitting_fasttrack` | 0.00 | Fast-track / SEZ availability (context only) |
| `value_capture` | 0.20 | Resource Value Capture Capacity |
| `tech_stack` | 0.20 | Technology Stack Alignment |
| `workforce` | 0.15 | Workforce Adaptability |

`permitting_fasttrack` is scored and stored for transparency but carries **zero
headline weight** (sponsor decision, 2026-06-18). Rationale: CII (WS2) already
measures whether fast builds actually happen (installed capacity, growth
velocity, pipeline-to-grid ratio), so a delivering fast-track already shows up
there as realized compute. CGM's role in the multiplier is to measure
institutional/systemic capacity, not realized output. Folding fast-track into
the permitting headline would re-import the same real-world fact and pay for it
twice. Keeping the headline on the default path preserves a clean division of
labor: CII answers "did they build it," CGM answers "how good is the system that
has to build it." See §2.3 for why permitting was split.

Weights are defined once, in `cgm/cgm_rubrics.py` (`WEIGHTS`), and verified to
sum to 1.0 by the QA gate (§6). Half-point final scores (e.g. 4.5) arise from
the adjacent-mean combination rule (§5.4); raters themselves emit integers only.

Design principles inherited from the project spec: agentic by design (no human
in the loop), no trained models (rubrics + formulas + LLM prompts only), full
data provenance, hard quality gates.

---

## 2. Rubrics

Rubric text is verbatim from the sponsor scope document, encoded in
`cgm/cgm_rubrics.py` (`RUBRICS`). Raters receive the rubric levels 5→1 exactly
as written here.

### 2.1 Country archetypes

`value_capture` uses an archetype-split rubric. Assignment (per the spec's own
examples) is fixed in `ARCHETYPE` and stored on every final-score row:

| archetype | countries |
|---|---|
| `substrate` (resource endowment) | US, AE, BR |
| `processor` (services/talent) | SG, IN, PH |

`rubric_for(dimension, country_iso)` returns the archetype-specific rubric for
`value_capture` and the shared rubric otherwise; `checklist_for` does the same
for evidence checklists.

### 2.2 D1 — `ai_policy`: AI Policy Posture (25%)

- **5:** National AI strategy with dedicated funding, minimal regulatory friction, explicit goal of AI leadership
- **4:** Active strategy, moderate funding, generally permissive regulation, proactive investment incentives
- **3:** Strategy exists but implementation uneven, mixed regulatory signals, moderate compliance burden
- **2:** Heavy regulatory framework creating significant compliance costs and deployment delays
- **1:** Restrictive or punitive regulation, no coherent strategy, active barriers to deployment

Evidence checklist (`EVIDENCE_CHECKLIST["ai_policy"]`):
- national AI strategy document
- dedicated AI budget (USD and % of GDP)
- estimated time from AI system development to legal deployment
- tax incentives/disincentives
- regulatory sandbox count and scope
- national AI coordinating body existence and mandate

### 2.3 D2 — Infrastructure Permitting Speed (20%), split into two sub-indicators

**Why split.** The original single `permitting` scale conflated two distinct
questions — how fast is the *default* approval path, and does a *fast-track*
exist — on one 1–5 axis. For dual-track countries (BR/IN/PH/SG), which run a
slow ordinary process alongside an SEZ fast-lane, this is genuinely ambiguous:
one rater grades the fast lane and another the slow lane, both reading the
evidence correctly. The result was a persistent inter-rater split that kept
`permitting` below the 0.70 kappa gate, isolated (richer evidence reproduced the
same split, ruling out thin evidence). Splitting the dimension into two
single-axis sub-indicators removes the ambiguity.

#### 2.3a `permitting_standard` — default approval path (headline, weight 0.20)

- **5:** Default (non-carve-out) approval in weeks-to-months; government actively facilitates the standard path
- **4:** Standard path streamlined, 3-12 months, clear pathway, limited opposition mechanisms
- **3:** Standard path 12-24 months, multiple agencies, some community opposition
- **2:** Standard path slow, 24-48 months, complex multi-stakeholder, frequent legal challenges
- **1:** Standard path gridlock, 48+ months, unpredictable, regulatory capture by incumbents

Evidence checklist:
- average permitting timeline for data centers and power via the DEFAULT (non-carve-out) path
- announced vs. completed projects on the standard path (3-year completion ratio)
- documented delays or cancellations on standard-path projects

#### 2.3b `permitting_fasttrack` — fast-track / SEZ availability (context, weight 0.00)

Graded on documented expedited *outcomes* and breadth of access, not the mere
existence of an instrument. Published for transparency; **not** weighted into
the headline (see §1 rationale — avoids double-counting CII's realized-build
measures).

- **5:** Operating fast-track instrument with documented expedited outcomes, broadly accessible (not zone-/sector-restricted), weeks-to-months
- **4:** Operating fast-track/SEZ instrument with documented expedited outcomes, but access conditional on zone, sector, or investment threshold
- **3:** Fast-track instrument exists in limited zones; expedited outcomes only partially documented or uneven
- **2:** Fast-track announced but no documented expedited outcomes, or available only to a narrow set of incumbents
- **1:** No fast-track instrument; no expedited pathway available

Evidence checklist:
- existence and legal basis of SEZ / fast-track instrument
- documented expedited timelines actually achieved (not statutory targets)
- eligibility conditions and accessibility (zone, sector, investment threshold)
- share of projects routed through the fast-track vs. the standard path

### 2.4 D3 — `value_capture`: Resource Value Capture Capacity (20%)

**Substrate rubric (US, AE, BR):**

- **5:** Stable resource taxation; sovereign wealth fund; active conversion of resource revenue into compute; strong anti-corruption checks
- **4:** Generally stable regime; some safeguards; growing but uneven compute conversion
- **3:** Unstable regime; resource nationalism risk; corruption siphons value; compute conversion throttled by governance
- **2:** High corruption, opaque contracts, weak controls, minimal compute conversion despite endowment
- **1:** Conflict-affected extraction, kleptocratic governance, zero value capture

Substrate evidence checklist:
- resource taxation regime stability
- sovereign wealth fund existence and mandate
- conversion of resource revenue into compute infrastructure
- anti-corruption controls in extractive sector

**Processor rubric (SG, IN, PH):**

- **5:** Large fiscal reserves; active retraining at scale; demonstrated history of economic pivots; actively building compute to offset services decline
- **4:** Adequate fiscal position; some retraining; moderate diversification; some compute investment
- **3:** Limited fiscal buffer; unproven retraining; high services dependence; minimal compute
- **2:** Weak fiscal position; no transition strategy; very high concentration in vulnerable services
- **1:** No buffer, no plan, total dependence on single vulnerable sector

Processor evidence checklist:
- fiscal reserves and budget position
- workforce retraining programs at scale
- history of economic pivots and diversification
- compute investment to offset services decline

### 2.5 D4 — `tech_stack`: Technology Stack Alignment (20%)

- **5:** Deep integration with leading stack; secure advanced chip access; hosting critical AI infrastructure
- **4:** Good access; some chip dependency but manageable; growing hyperscaler presence
- **3:** Dual-alignment with long-term uncertainty; or moderate access to one stack with limited depth
- **2:** Peripheral to both stacks; limited chip access; no hyperscaler presence
- **1:** Technology-denied or self-isolated; sanctioned; no AI infrastructure

Evidence checklist:
- chip import access by generation
- hyperscaler commitments (list and USD)
- technology alliance participation
- bilateral tech agreements
- domestic AI model capability

### 2.6 D5 — `workforce`: Workforce Adaptability (15%)

- **5:** World-class education, high digital literacy, extensive retraining, young demographics, English proficiency, strong STEM pipeline
- **4:** Good education, above-average digital literacy, functioning retraining, favorable demographics
- **3:** Average education, moderate digital literacy, limited retraining, mixed demographics
- **2:** Weak education, low digital literacy, minimal retraining, unfavorable demographics
- **1:** Education in crisis, very low digital literacy, no retraining, demographic headwinds

Evidence checklist:
- education quality (PISA or equivalent)
- digital literacy and ICT development
- retraining program scale
- demographic projections
- STEM pipeline and English proficiency

---

## 3. Evidence methodology

Two evidence layers, both with full provenance (source URL, accessed-at
timestamp, raw payload where applicable). Raters see only the stored evidence —
never the live web (§8, decision 3).

### 3.1 Quantitative anchors (`cgm/cgm_anchors.py`)

Six World Bank indicators per country (36 cells), free API, no key:

| WB indicator code | stored metric | unit |
|---|---|---|
| `HD.HCI.OVRL` | `human_capital_index` | index |
| `SE.ADT.LITR.ZS` | `adult_literacy_pct` | % |
| `SE.TER.ENRR` | `tertiary_enrollment_pct` | % |
| `SP.POP.DPND` | `age_dependency_ratio` | % |
| `IT.NET.USER.ZS` | `internet_users_pct` | % |
| `NY.GDP.MKTP.CD` | `gdp_usd` | USD |

Exact URL pattern (`WB_URL`):

```
https://api.worldbank.org/v2/country/{iso}/indicator/{ind}?format=json&mrnev=1
```

`mrnev=1` requests the **most recent non-empty value**, so the anchor is always
the latest year with data, country by country. Retry rule: 2 attempts per
fetch with a 2-second sleep between them (`fetch_indicator`); a request that
fails twice raises, is logged to `cgm_collection_log` with status `error`, and
is recorded in `cgm_data_gaps` as `anchor fetch failed: <metric>` — the run
continues. A response whose value is null is logged `skipped` and recorded as
`anchor missing: <metric>`. Successful rows are upserted into
`cgm_raw_anchors` keyed on `(country_iso, metric, year)`, preserving the
request URL and the full raw JSON payload.

First-run outcome: the initial anchors pass logged 8 missing cells as `warn`
gaps. Seven of those 8 failures were transient network errors that self-healed
on resume runs (the anchors phase upserts idempotently, so re-running it fills
any gaps that were transient). The final corpus has **35 of 36** cells; the
only genuinely unreported cell is **US adult literacy (`SE.ADT.LITR.ZS`)**,
which the World Bank does not report for the United States.

### 3.2 Qualitative evidence packs (`cgm/cgm_evidence.py`)

One pack per country×dimension = 30 packs. Procedure per pack:

1. **Tavily search per checklist item.** For each item in
   `checklist_for(dimension, country)`, POST to `https://api.tavily.com/search`
   with body `{"api_key": $TAVILY_API_KEY, "query": "<country name> <checklist item>",
   "max_results": 5}` (timeout 60 s). Results from all items are concatenated.
2. **Claude claim extraction.** One LLM call per pack
   (`extract_model` = the Rater A model, default `claude-sonnet-4-6`,
   temperature 0, `max_tokens=8000`). The user prompt lists the country,
   dimension, checklist items, and every search result as
   `URL / TITLE / CONTENT` with content truncated to 1,500 characters per
   result. The system prompt (`EXTRACT_SYSTEM`), verbatim:

```
You extract factual evidence claims from web search results
for sovereign governance scoring. Output STRICT JSON:
{"claims": [{"claim": "<one-sentence factual claim>",
             "quote": "<short verbatim supporting quote from the source content>",
             "source_url": "<url of the source the quote came from>",
             "checklist_item": "<the checklist item this claim addresses>"}]}
Rules: only claims directly supported by the provided source content; source_url
must be one of the provided URLs; checklist_item must be one of the provided
items verbatim; no opinions, no scores, no speculation. Empty list if nothing
is supported. At most 2 claims per checklist item; keep each quote under 25 words.
```

3. **Anti-fabrication URL guard** (`parse_claims`): any claim whose
   `source_url` is not in the set of URLs actually returned by the Tavily
   searches is silently dropped, as is any claim missing one of the four
   required keys. The LLM cannot inject sources the search did not surface.
4. **Claim bounds.** At most 2 claims per checklist item and quotes under 25
   words (enforced in the prompt). These bounds exist to keep extraction
   output well inside `max_tokens` — see the truncation incident in §9.7.
   The shared LLM wrapper (`cgm/cgm_llm.py`) raises a hard error whenever
   `stop_reason == "max_tokens"`, so a truncated extraction can never be
   half-parsed into a partial pack.
5. **Storage and coverage.** Accepted claims are inserted into `cgm_evidence`
   (`checklist_item`, `claim`, `quote`, `source_url`, `source_type='web'`,
   `accessed_at`). Coverage = covered checklist items ÷ checklist length
   (`coverage()`); every missing item is recorded in `cgm_data_gaps` as
   `evidence missing for checklist item: <item>` (severity `warn`), and the
   collection log records `claims=<n> coverage=<ratio>`.

**Pack immutability:** `collect_evidence` skips any country×dimension that
already has rows in `cgm_evidence`. Once collected, a pack is an immutable
corpus; re-running the evidence phase only fills packs that errored out
(logged `error`, zero rows). This makes the rater inputs stable across resume
runs and is what makes kappa interpretable (§8, decision 3).

**Coverage is measured independently of agreement** (design rationale): both
raters score from the same pack, so a hole in the pack produces correlated
error that agreement statistics cannot see — if both raters score from the
same hole, they agree and are wrong. The gap report (`cgm_gap_report.py`)
prints per-pack coverage with missing items; coverage is informational in v1,
not gated (§6, check 6 note).

### 3.3 Data model & provenance (`cgm/cgm_schema.sql`)

All state lives in the `cgm` Postgres database (idempotent schema):

| table / view | contents |
|---|---|
| `cgm_runs` | run_id (UUID), started/finished timestamps, ordered phase log |
| `cgm_collection_log` | every collector action: source, status (`ok`/`error`/`skipped`), detail |
| `cgm_raw_anchors` | country, metric, value, unit, year, **source_url, accessed_at, raw JSONB payload**; unique (country, metric, year) |
| `cgm_evidence` | evidence_id, run_id, country, dimension, checklist_item, claim, quote, **source_url, accessed_at** |
| `cgm_rater_scores` | country, dimension, rater_model, score (1–5 or NULL), rubric_clause, **evidence_ids INT[]**, rationale; unique (country, dimension, rater_model) |
| `cgm_arbitrations` | country, dimension, both rater scores, resolved_score, arbiter_model, written reasoning; unique (country, dimension) |
| `cgm_kappa_results` | per run: dimension (5 dims + `pooled`), kappa_linear (NULL when degenerate), degenerate flag, raw/adjacent agreement, n |
| `cgm_score_final` | per run: country, archetype, five dimension finals, cgm_score; unique (run_id, country) |
| `cgm_score_methodology` | per run: weights JSON, rater model ids, full sensitivity JSON |
| `cgm_data_gaps` | country, dimension, gap text, severity `warn`/`blocker` |
| `v_cgm_latest` | **the integration API**: country_iso, archetype, five dimensions, cgm_score, rank, computed_at — for the latest *finished* run |

Every score is traceable: final score → two rater rows → `evidence_ids[]` →
`cgm_evidence.source_url` + `accessed_at` → original web source. Anchors carry
their raw API payloads.

---

## 4. Rater protocol (`cgm/cgm_raters.py`)

### 4.1 Panel composition

Two LLM raters replace the sponsor spec's human 2-rater protocol (§8,
decision 1). Both run at `temperature=0` through the shared wrapper
(`cgm_llm.call_llm`: 3 attempts, linear backoff 5 s/10 s, hard error on
`max_tokens` truncation, robust JSON extraction).

| persona | model (env override) | prompt strategy |
|---|---|---|
| Rater A | `claude-sonnet-4-6` (`CGM_RATER_A_MODEL`) | rubric-clause-first |
| Rater B | `claude-opus-4-5` (`CGM_RATER_B_MODEL`) | evidence-first |

**Model choice rationale:** Opus 4.5 accepts explicit sampling parameters;
Opus/Sonnet 4.7 and 4.8 reject `temperature` in the API. Determinism
(temperature 0 everywhere) was prioritized over model recency — the same
rationale as WS3's judge. Both raters are Anthropic siblings; the resulting
correlation is a stated first-order limitation (§9.2).

**Prompt decorrelation rationale:** because the models share training lineage,
the two system prompts are made *structurally* different to decorrelate the
reasoning paths — one anchors on the rubric text and searches the evidence for
the first satisfied clause; the other builds a picture from the evidence first
and then maps it onto the rubric. This mitigates, but does not remove, the
correlated-rater problem.

`RATER_A_SYSTEM`, verbatim:

```
You are Rater A, scoring sovereign governance on a 1-5 rubric.
Method - rubric-clause-first: walk the rubric from level 5 down to level 1 and
select the FIRST level whose clause the cited evidence fully supports. You may
only rely on the evidence and anchors provided. Output STRICT JSON:
{"score": <int 1-5>, "rubric_clause": "<verbatim text of the level you matched>",
 "evidence_ids": [<ints - the [N] ids of evidence you relied on>],
 "rationale": "<2-4 sentences>"}
A score with no evidence_ids is invalid. Do not invent evidence.
```

`RATER_B_SYSTEM`, verbatim:

```
You are Rater B, scoring sovereign governance on a 1-5 rubric.
Method - evidence-first: first summarize what the evidence establishes about this
country and dimension, then decide which rubric level that picture maps onto.
You may only rely on the evidence and anchors provided. Output STRICT JSON:
{"score": <int 1-5>, "rubric_clause": "<verbatim text of the level you matched>",
 "evidence_ids": [<ints - the [N] ids of evidence you relied on>],
 "rationale": "<2-4 sentences>"}
A score with no evidence_ids is invalid. Do not invent evidence.
```

### 4.2 Blindness and the shared pack

Each rater independently scores all 30 country×dimension cells from the
identical frozen pack (qualitative claims rendered as
`[evidence_id] (checklist_item) claim — "quote" (source_url)` plus all
country anchors as `- metric = value unit (year)`), with the archetype-correct
rubric printed 5→1. Raters never see each other's outputs, the live web, or
any prior scores. The user prompt is built by `build_rater_prompt` and is
byte-identical for both raters.

### 4.3 Validation and citation enforcement

`validate_rating` rejects a rating when:
- `score` is not an int in 1–5 (booleans explicitly rejected), or
- `evidence_ids` is missing/empty/not a list (*"no evidence_ids cited -
  evidence citation is mandatory"*), or
- any cited id is not in the pack (*"unknown evidence ids cited: [...]"*).

On rejection (or unparseable JSON), exactly **one retry** is issued with the
validation error appended to the prompt:
`"Your previous output was invalid: {err}. Fix it."`. On second failure the
score is stored as **NULL** with the error in `rationale`, and a
**severity=`blocker`** gap is recorded
(`rater <model> produced no valid score: <err>`). A NULL score later trips the
completeness check in verify and aborts scoring (`compute_final_scores` exits:
`cannot score: missing rater score for <country>/<dim>`).

Special case: an **empty evidence pack** can never pass validation, so the
rater phase stores NULL immediately without burning LLM calls
(`no evidence pack - cannot rate`, severity `blocker`).

### 4.4 Caching semantics

A (country, dimension, rater_model) cell with an existing **non-NULL** score is
skipped — only NULL cells are (re-)rated. `CGM_RATE_FORCE=1` overrides the
cache and re-rates everything. This is the self-heal mechanism: a halted run
resumes by re-running `rate`, touching only the missing cells against the
immutable packs (demonstrated in the first run, §7.4). After a forced
re-rate, stale arbitration snapshots must be deleted (§5.5).

---

## 5. Reliability & arbitration

### 5.1 Linear-weighted Cohen's kappa (`cgm/cgm_kappa.py`)

For two raters scoring N items on the ordered categories 1–5, with category
indices i, j and span 4, the disagreement weight is

```
w(i, j) = |i − j| / 4          (0 for agreement, 1 for a 1-vs-5 split)
```

Observed disagreement (mean weight over the N pairs):

```
D_obs = (1/N) Σₙ w(aₙ, bₙ)
```

Expected disagreement under independence (from the raters' marginal counts):

```
D_exp = (1/N²) Σᵢ Σⱼ w(i, j) · countₐ(i) · count_b(j)
```

```
κ_linear = 1 − D_obs / D_exp
```

Raw agreement (= exact-match fraction) and adjacent agreement (|a−b| ≤ 1
fraction) are reported alongside (`agreement_stats`).

### 5.2 Degeneracy rule

When `D_exp = 0` — both raters constant at the same category — kappa is
undefined (division by zero); the function returns `None`. The gate treats
`None` + raw agreement = 100% as a **PASS**, reported
`N/A (degenerate - perfect agreement)`; `None` with imperfect agreement is a
FAIL. This rule is necessary because **N=6** on a 5-point scale makes kappa
pathological: with six items, zero observed variance under perfect agreement
is a live possibility, and chance-corrected agreement is then meaningless —
penalizing perfect agreement for lacking variance would be wrong. (Neither
degenerate case occurred in the first run; `value_capture` and `workforce`
reached κ = 1.000 *with* variance.)

### 5.3 Pooled kappa

A pooled linear-weighted kappa over all 30 country×dimension pairs is computed
and stored under dimension `pooled`. It is **reported, not gated** (the spec's
gate is per-dimension); at N=30 it is the statistically meaningful headline
reliability number (§8, decision 5).

### 5.4 Arbitration trigger and combination rules

Trigger (`cgm_arbiter.needs_arbitration`): **|score_A − score_B| > 1**.
Combination of the two rater scores into a final dimension score
(`cgm_scoring.combine_scores`):

| condition | final score |
|---|---|
| equal | that score |
| differ by exactly 1 | mean (half-points allowed) |
| differ by >1 | arbiter's resolved score (missing arbitration row ⇒ hard error) |

The arbiter is a third LLM call (default `claude-opus-4-5`,
`CGM_ARBITER_MODEL`, temperature 0) that sees the full rater prompt (rubric +
pack + anchors) plus both raters' scores, matched clauses, and rationales, and
must issue a resolved integer score with written reasoning — the spec's
"divergences documented with evidence and resolved through structured
discussion". Stored in `cgm_arbitrations`. `ARBITER_SYSTEM`, verbatim:

```
You are the arbiter for a 2-rater governance scoring panel.
The raters diverged by more than 1 point. Review the rubric, the shared evidence,
and both raters' scores and rationales. Decide the better-supported score (it may
be either rater's score or one between them). Output STRICT JSON:
{"resolved_score": <int 1-5>, "reasoning": "<3-6 sentences explaining which
rater's reading of the evidence is better supported and why>"}
```

Ordering note: inside the arbitration/scoring/kappa code, "rater a / rater b"
follow **lexicographic `rater_model` order** (`claude-opus-4-5` <
`claude-sonnet-4-6`), not the panel personas — so in stored arbitration rows
and in §7.3, a = Opus, b = Sonnet.

### 5.5 Stale-arbitration guard

An arbitration row snapshots the two rater scores it resolved. At scoring time
`resolve_arbitration` raises if the stored snapshot no longer matches the
current rater scores (possible after a `CGM_RATE_FORCE=1` re-rate):
`stale arbitration: stored rater scores (a, b) != current (a', b') - delete
the cgm_arbitrations row and re-run --only arbitrate`. The arbitrate phase
itself skips cells that already have an arbitration row, so re-arbitration
requires explicitly deleting the affected rows.

---

## 6. QA gate (`cgm/cgm_verify.py`)

`cgm_verify.main()` computes and stores kappa for the run (idempotently —
prior kappa rows for the run are deleted first), then runs six checks. Any
failure prints `FAIL (<n>)` with every failure line and **exits 1**; the
orchestrator propagates the exit code, so a red gate fails the whole pipeline
run. The exit-1 contract is what the master CSI orchestrator consumes: it runs
each workstream's verify before integrating and marks the CSI output
PROVISIONAL if any upstream gate is red.

1. **Kappa gate** (`check_kappa_gate`): per-dimension linear-weighted
   κ ≥ **0.7**, subject to the degeneracy rule (degenerate + 100% raw
   agreement passes as N/A; degenerate + imperfect agreement fails). The
   `pooled` row is reported, never gated.
2. **Completeness** (`check_completeness`): all 6 countries × 5 dimensions
   have **both** rater scores non-NULL.
3. **Evidence citations** (`check_evidence_citations`): every stored non-NULL
   rater score cites ≥1 evidence id.
4. **Score ranges** (`check_score_ranges`): every final `cgm_score` ∈ [1, 5].
5. **Arbitration completeness** (`check_arbitrations`): every >1-point rater
   divergence has a matching `cgm_arbitrations` row.
6. **Weights** (`check_weights`): the dimension weights sum to exactly 1.0
   (`math.isclose`).

Additionally, verify fails if the run has no final-score rows at all
(`no final scores for latest run - scoring phase not run`). Evidence-pack
coverage is reported per pack by the gap report (`run_cgm.py --only gap`) and
recorded in `cgm_data_gaps`; it is informational in v1 — gating on coverage
would block on genuinely unavailable evidence.

---

## 7. Results of the first run (2026-06-09)

### 7.1 Final scores (`v_cgm_latest`, 0–5 scale)

| rank | country | archetype | ai_policy | permitting | value_capture | tech_stack | workforce | **CGM** |
|---|---|---|---|---|---|---|---|---|
| 1 | SG | processor | 5.0 | 4.5 | 5.0 | 4.0 | 5.0 | **4.70** |
| 2 | AE | substrate | 5.0 | 5.0 | 4.0 | 5.0 | 4.0 | **4.65** |
| 3 | US | substrate | 5.0 | 3.0 | 4.0 | 5.0 | 3.0 | **4.10** |
| 4 | IN | processor | 4.0 | 3.5 | 3.0 | 4.5 | 3.0 | **3.65** |
| 5 | BR | substrate | 3.5 | 2.5 | 3.0 | 4.0 | 3.0 | **3.225** |
| 6 | PH | processor | 3.5 | 2.5 | 3.0 | 3.5 | 2.0 | **2.975** |

Raters: `claude-sonnet-4-6` (Rater A persona) and `claude-opus-4-5` (Rater B
persona), both temperature 0, scoring from identical frozen packs.

### 7.2 Inter-rater reliability (linear-weighted kappa, N=6 per dimension)

| dimension | κ_linear | raw agreement | adjacent (±1) | gate (≥0.7) |
|---|---|---|---|---|
| ai_policy | 0.571 | 4/6 | 6/6 | **FAIL** |
| permitting | 0.455 | 2/6 | 6/6 | **FAIL** |
| value_capture | 1.000 | 6/6 | 6/6 | PASS |
| tech_stack | 0.500 | 4/6 | 6/6 | **FAIL** |
| workforce | 1.000 | 6/6 | 6/6 | PASS |
| **pooled (30 pairs)** | **0.741** | 22/30 | 30/30 | reported, not gated |

**GATE VERDICT: FAIL** — 3 of 5 dimensions below the 0.7 per-dimension gate
(ai_policy, permitting, tech_stack). `cgm_verify` exits 1. CGM is therefore
**not publishable** and feeds CSI integration only as **PROVISIONAL** — the
same posture as the WS3 SI1 precedent (SI1 fails its own 80% concordance gate
at 66.2% and is consumed as-is with the limitation documented). Rater
calibration (sharper rubric operationalization for the three failing
dimensions, and/or richer permitting evidence) is required before publication.

### 7.3 Disagreements

8 of 30 cells disagreed; **all 8 by exactly 1 point**, so **zero
arbitrations** were triggered — every disagreement was resolved by the
adjacent-mean rule. The cells (score order: Opus 4.5 vs Sonnet 4.6, i.e.
lexicographic `rater_model` order):

| dimension | country | opus | sonnet | final (mean) |
|---|---|---|---|---|
| ai_policy | BR | 4 | 3 | 3.5 |
| ai_policy | PH | 3 | 4 | 3.5 |
| permitting | BR | 3 | 2 | 2.5 |
| permitting | IN | 3 | 4 | 3.5 |
| permitting | PH | 3 | 2 | 2.5 |
| permitting | SG | 5 | 4 | 4.5 |
| tech_stack | IN | 4 | 5 | 4.5 |
| tech_stack | PH | 3 | 4 | 3.5 |

### 7.4 Sensitivity (±10pp per dimension weight, renormalized; 10 perturbations)

Baseline ranking: **SG, AE, US, IN, BR, PH**. 4 of 10 perturbations flip the
top pair to **AE, SG**: permitting +10pp, value_capture −10pp, tech_stack
+10pp, workforce −10pp. SG and AE are separated by only **0.05** composite
points, so the #1 position is weight-fragile; **positions 3–6 never change**
under any perturbation.

### 7.5 Run history (operational record)

- World Bank anchors: initial pass logged 8 gaps as `warn`; 7 were transient
  and self-healed on resume runs (upsert). Final state: **35/36** cells loaded;
  only **US adult literacy (`SE.ADT.LITR.ZS`)** is a genuine data gap.
- The first full run halted at scoring because the US/tech_stack evidence pack
  was empty: the extraction LLM output exceeded `max_tokens=4000` and
  truncated mid-JSON — deterministically, at temperature 0, on every retry.
  Fix (commit `880e358`): bound extraction output (≤2 claims per checklist
  item, quotes <25 words), raise extraction `max_tokens` to 8000, and surface
  `stop_reason == "max_tokens"` as a hard error instead of silently parsing a
  truncated payload.
- The resume run then completed end-to-end, exercising the cache/self-heal
  design as intended: packs are immutable, and only NULL rater scores were
  re-rated.
- Evidence coverage is reported per pack by the gap report; missing checklist
  items are recorded as `warn` gaps.

---

## 8. Decisions log

**1. LLM raters replace the spec's human 2-rater protocol.**
*What:* two LLM raters + LLM arbiter; no human scores anywhere.
*Why:* the project is agentic by design (no human in the loop), and WS3 set
the precedent by replacing human SI1 validation with an LLM-judge ensemble.
Human raters would also be unreproducible — this paper could not be an
executable spec.
*Alternatives:* human raters (spec's original protocol — rejected: violates
the agentic principle, not reproducible); single LLM rater (rejected: no
reliability measurement at all).
*Sensitivity impact:* kappa becomes measurable and reproducible at
temperature 0, but measures model agreement, not human expert agreement; the
0.7 gate inherits its meaning from human-rater practice and may need
recalibration for LLM panels.

**2. Two Anthropic sibling models + structural prompt decorrelation, vs a
non-Anthropic second rater.**
*What:* Sonnet 4.6 and Opus 4.5 with deliberately different prompt strategies
(rubric-clause-first vs evidence-first).
*Why:* no second-provider API key is available in this environment; prompt
decorrelation is the strongest independence lever available within one
provider.
*Alternatives:* GPT/Gemini second rater (preferred in principle, blocked on
credentials); same model twice with different prompts (rejected: even more
correlated); different temperature seeds (rejected: sacrifices determinism for
trivial decorrelation).
*Sensitivity impact:* kappa overstates true inter-rater reliability —
correlated training pulls the raters toward agreement. Stated prominently in
§9.2. Notably the panel still failed the gate on 3 dimensions, so the
correlation does not mask the rubrics' looseness.

**3. Frozen evidence packs vs live-web raters.**
*What:* raters score only from immutable `cgm_evidence` + `cgm_raw_anchors`
rows; they never search.
*Why:* kappa must measure **rubric agreement**, not search variance. Two
agents searching live would disagree partly because they found different
pages; that disagreement is noise with respect to the rubric. Frozen packs
also give exact provenance and make re-rating cheap.
*Alternatives:* live-search raters (rejected: confounds kappa, unreproducible,
2× search cost); one rater searches and shares (rejected: asymmetric
information).
*Sensitivity impact:* introduces the shared-hole failure mode — both raters
agreeing from the same missing evidence — which is why coverage is measured
and reported independently of agreement (§3.2).

**4. Adjacent-mean for 1-point disagreements vs arbitrating every
disagreement.**
*What:* arbiter triggers only on >1-point divergence; 1-point splits resolve
to the mean (half-points allowed).
*Why:* the spec mandates structured resolution only for material divergences;
adjacent scores on a 5-point ordinal rubric are normal calibration noise, and
arbitrating all of them would roughly double LLM cost for no information gain
(the arbiter would mostly split the difference anyway).
*Alternatives:* arbitrate everything (rejected: cost, and it launders the
disagreement signal out of the kappa statistics); always take the lower/more
conservative score (rejected: introduces systematic bias).
*Sensitivity impact:* half-point finals (8 of 30 dimension finals in the
first run are X.5: SG/permitting 4.5, IN/permitting 3.5, IN/tech_stack 4.5,
BR/ai_policy 3.5, BR/permitting 2.5, PH/ai_policy 3.5, PH/permitting 2.5,
PH/tech_stack 3.5). In the first run the rule resolved all 8 disagreements;
the arbiter path executed zero times live (it is covered by tests).

**5. Per-dimension kappa gate kept at 0.7 despite N=6 fragility; pooled kappa
reported as the headline.**
*What:* the gate applies per dimension at κ ≥ 0.7 exactly as the spec demands,
with the degeneracy carve-out (§5.2); a pooled κ over 30 pairs is reported but
not gated.
*Why:* the spec mandates the per-dimension gate; weakening it unilaterally
would be self-grading. But at N=6 a single 1-point disagreement can swing κ
below the gate (permitting: raw 2/6 yet 100% adjacent ⇒ κ 0.455), so the
pooled statistic is published alongside as the statistically meaningful
reliability number.
*Alternatives:* gate on pooled kappa only (rejected: not what the spec says);
gate on adjacent agreement (rejected: too lenient — 100% adjacent is
compatible with systematic 1-point bias).
*Sensitivity impact:* the gate verdict (FAIL) is driven by the strict reading;
under a pooled-only gate the run would pass (0.741 ≥ 0.7). Publishing both
numbers makes the trade-off auditable.

---

## 9. Limitations

1. **N=6 kappa fragility.** Six items per dimension on a 5-point scale make κ
   hypersensitive: `permitting` shows κ = 0.455 from raw agreement of 2/6 even
   though 100% of pairs are within 1 point. Single-cell changes move κ by
   tenths. The degeneracy rule (§5.2) handles the limiting case, and the
   pooled κ (0.741, N=30) is the more stable statistic — but the gated numbers
   are fragile by construction.
2. **Correlated raters.** Both raters are Anthropic models with shared
   training lineage; agreement statistics overstate true independence. Prompt
   decorrelation (§4.1) mitigates but does not remove this. A second-provider
   rater is the correct fix when credentials allow.
3. **Evidence recency.** Each pack is a web snapshot at its collection date
   (`accessed_at` on every row, 2026-06-09 for this run). Governance facts
   drift; packs are immutable by design, so refreshing requires a new
   collection (delete pack rows or use a fresh database) and constitutes a new
   scoring period.
4. **Missing anchor cells.** The initial anchors pass logged 8 gaps; 7 were
   transient failures that self-healed across resume runs. Final state: 35 of
   36 World Bank indicator×country cells are present. The one genuine gap is
   **US adult literacy (`SE.ADT.LITR.ZS`)**, which the World Bank does not
   report for the United States. Raters scored the US/workforce cell from
   qualitative evidence plus the remaining anchors.
5. **Top-rank weight fragility.** SG (4.70) leads AE (4.65) by 0.05; 4 of 10
   ±10pp weight perturbations flip the pair. The #1/#2 ordering should be
   treated as a tie within methodological error. Positions 3–6 are stable
   under all perturbations.
6. **Single period.** One scoring period exists; CGM trajectory (and the CSI
   spec's trajectory term) requires ≥2 periods. This run establishes the
   baseline.
7. **Determinism trade-off (worked example).** Temperature-0 determinism means
   failures are also deterministic: the US/tech_stack extraction truncated at
   `max_tokens=4000` identically on every retry — retry loops cannot fix a
   deterministic overflow. The fix had to change the input/output contract
   (claim bounds + larger budget + truncation surfaced as a hard error,
   commit `880e358`). Deterministic pipelines need hard failure surfacing
   precisely because they cannot luck their way past an error.
8. **Coverage not gated.** Evidence-pack coverage below 100% is reported, not
   failed (gating would block on genuinely unavailable evidence), so the
   shared-hole risk in §8 decision 3 is monitored rather than eliminated.

---

## 10. Reproduction

From a fresh clone, with access to a Postgres server, an Anthropic API key,
and a Tavily API key:

```bash
git clone https://github.com/rsm-sdeenadayalan/gramercy-workstream-4
cd gramercy-workstream-4
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env   # then fill in:
# POSTGRES_HOST=            (required)
# POSTGRES_PORT=5432
# POSTGRES_USER=            (required)
# POSTGRES_PASSWORD=        (required)
# POSTGRES_BOOTSTRAP_DB=postgres
# CGM_DB=cgm
# ANTHROPIC_API_KEY=        (required - raters, arbiter, extraction)
# TAVILY_API_KEY=           (required - evidence search)
# CGM_RATER_A_MODEL=claude-sonnet-4-6
# CGM_RATER_B_MODEL=claude-opus-4-5
# CGM_ARBITER_MODEL=claude-opus-4-5
# CGM_RATE_FORCE=0

# 1. Create the cgm database and apply the schema (idempotent)
.venv/bin/python cgm/setup_cgm.py

# 2. Regression guard - no live APIs touched (expect: 67 passed)
.venv/bin/python -m pytest -q

# 3. Full pipeline: anchors -> evidence -> rate -> arbitrate -> score -> verify -> gap
.venv/bin/python cgm/run_cgm.py

# Or phase by phase:
.venv/bin/python cgm/run_cgm.py --only anchors     # World Bank, free, ~1 min
.venv/bin/python cgm/run_cgm.py --only evidence    # 30 packs: Tavily + extraction
.venv/bin/python cgm/run_cgm.py --only rate        # 60 rater calls
.venv/bin/python cgm/run_cgm.py --only arbitrate   # only >1pt divergences
.venv/bin/python cgm/run_cgm.py --only score       # combination + composite + sensitivity
.venv/bin/python cgm/run_cgm.py --only verify      # QA gate - exits 1 on failure
.venv/bin/python cgm/run_cgm.py --only gap         # gaps + per-pack coverage (informational)
```

> **Phase-by-phase caveat:** every `run_cgm.py` invocation creates a **new
> run_id**. When running phases as separate commands (e.g. `--only score`
> followed by `--only verify` in a second invocation), verify's final-score
> check is scoped to the *latest* run — which has no final-score rows yet —
> and will report a **fourth failure line** (`no final scores for latest run -
> scoring phase not run`) in addition to the three kappa failures. The three
> kappa failures are the figures to compare against §7.2; the spurious
> fourth line is an artifact of split invocations. The full single-command
> pipeline (`run_cgm.py` with no `--only`) reproduces exactly **FAIL (3)**.

Expected cost and duration for a full run: **~$3–5** in LLM + Tavily usage
(30 extraction calls, 60 rater calls, arbitrations as needed) and **~45
minutes** wall clock, dominated by the evidence phase.

Exit-code contract: `run_cgm.py` exits 0 on success; the verify phase calls
`sys.exit(1)` on any gate failure, which propagates as the pipeline exit code.
**Against the 2026-06-09 evidence corpus, expect verify to exit 1** with the
three kappa failures of §7.2 — that is the documented, correct behavior of a
red gate, not a reproduction error. A halted or interrupted run is resumed by
re-running the same command: anchors upsert, evidence packs are skipped once
collected, and only NULL rater scores are re-rated (set `CGM_RATE_FORCE=1` to
force a full re-rate; then delete affected `cgm_arbitrations` rows per §5.5).

Results land in the `cgm` database; the canonical output is:

```sql
SELECT * FROM v_cgm_latest ORDER BY rank;
```

---

## Appendix: file map

| file | role |
|---|---|
| `cgm/cgm_rubrics.py` | rubrics, weights, checklists, archetypes (data only) |
| `cgm/cgm_anchors.py` | World Bank anchor collector |
| `cgm/cgm_evidence.py` | Tavily search + Claude claim extraction + coverage |
| `cgm/cgm_raters.py` | 2-rater blind panel, validation, caching |
| `cgm/cgm_arbiter.py` | >1pt divergence arbitration |
| `cgm/cgm_kappa.py` | linear-weighted kappa + degeneracy rule |
| `cgm/cgm_scoring.py` | combination rules, composite, ±10pp sensitivity |
| `cgm/cgm_verify.py` | six-check QA gate, exit 1 on failure |
| `cgm/cgm_gap_report.py` | gaps + per-pack coverage (informational) |
| `cgm/cgm_llm.py` | deterministic LLM wrapper (temperature 0, truncation = hard error) |
| `cgm/cgm_db.py` | connections, run log, collection log, gap writer |
| `cgm/cgm_schema.sql` | data model (§3.3) |
| `cgm/setup_cgm.py` | idempotent DB + schema bootstrap |
| `cgm/run_cgm.py` | orchestrator (`--only <phase>`) |
