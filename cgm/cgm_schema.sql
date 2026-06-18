-- CGM (Chessboard Governance Multiplier) schema. Idempotent.
CREATE TABLE IF NOT EXISTS cgm_runs (
    run_id      UUID PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    phases      TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cgm_collection_log (
    id      SERIAL PRIMARY KEY,
    run_id  UUID NOT NULL REFERENCES cgm_runs(run_id),
    source  TEXT NOT NULL,
    status  TEXT NOT NULL CHECK (status IN ('ok','error','skipped')),
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
    run_id         UUID NOT NULL REFERENCES cgm_runs(run_id),
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
    rater_a_score  INT NOT NULL CHECK (rater_a_score BETWEEN 1 AND 5),
    rater_b_score  INT NOT NULL CHECK (rater_b_score BETWEEN 1 AND 5),
    resolved_score INT NOT NULL CHECK (resolved_score BETWEEN 1 AND 5),
    arbiter_model  TEXT NOT NULL,
    reasoning      TEXT NOT NULL,
    ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (country_iso, dimension)
);

CREATE TABLE IF NOT EXISTS cgm_kappa_results (
    id                 SERIAL PRIMARY KEY,
    run_id             UUID NOT NULL REFERENCES cgm_runs(run_id),
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
    run_id        UUID NOT NULL REFERENCES cgm_runs(run_id),
    country_iso   TEXT NOT NULL,
    archetype     TEXT NOT NULL CHECK (archetype IN ('substrate','processor')),
    ai_policy            NUMERIC NOT NULL,
    permitting_standard  NUMERIC NOT NULL,   -- headline permitting (weight 0.20)
    permitting_fasttrack NUMERIC NOT NULL,   -- context only (weight 0.00)
    value_capture        NUMERIC NOT NULL,
    tech_stack           NUMERIC NOT NULL,
    workforce            NUMERIC NOT NULL,
    cgm_score     NUMERIC NOT NULL,          -- 0-5 scale
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, country_iso)
);

CREATE TABLE IF NOT EXISTS cgm_score_methodology (
    id           SERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES cgm_runs(run_id),
    weights      JSONB NOT NULL,
    rater_models JSONB NOT NULL,
    sensitivity  JSONB,
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cgm_data_gaps (
    id          SERIAL PRIMARY KEY,
    run_id      UUID NOT NULL REFERENCES cgm_runs(run_id),
    country_iso TEXT,
    dimension   TEXT,
    gap         TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'warn' CHECK (severity IN ('warn','blocker')),
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE VIEW v_cgm_latest AS
SELECT f.country_iso, f.archetype,
       f.ai_policy, f.permitting_standard, f.permitting_fasttrack,
       f.value_capture, f.tech_stack, f.workforce,
       f.cgm_score,
       RANK() OVER (ORDER BY f.cgm_score DESC) AS rank,
       f.computed_at
FROM cgm_score_final f
WHERE f.run_id = (SELECT f2.run_id FROM cgm_score_final f2
                  JOIN cgm_runs r ON r.run_id = f2.run_id
                  WHERE r.finished_at IS NOT NULL
                  ORDER BY f2.computed_at DESC LIMIT 1);
