"""Two blind LLM raters. Same evidence pack, structurally different prompts
(deliberate decorrelation - both models are Anthropic siblings). A score that
cites no valid evidence IDs is re-requested once with the validation error;
on second failure it is stored NULL and flagged as a blocker gap."""
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
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
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
                if not evidence:
                    # No evidence pack — validation can never pass; skip LLM calls
                    if row is not None and row[0] is not None:
                        continue  # already has a cached non-NULL score
                    err = "no evidence pack - cannot rate"
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
                            (country, dim, model, None, None, None, err),
                        )
                    conn.commit()
                    cgm_db.add_gap(conn, run_id, country, dim,
                                   f"rater {model} produced no valid score: {err}",
                                   severity="blocker")
                    continue
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
