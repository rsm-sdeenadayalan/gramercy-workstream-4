"""Third-LLM arbitration for rater divergences > 1 point. The arbiter sees both
raters' scores and rationales plus the same evidence pack, and must produce a
resolved score with written reasoning (the spec's 'structured discussion')."""
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
    if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
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
            # "Rater A"/"Rater B" here follow lexicographic rater_model order
            # (same ordering as scoring and verify), NOT the panel personas in
            # cgm_raters: a = claude-opus-4-5, b = claude-sonnet-4-6.
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
                    # Already arbitrated. Note: after a CGM_RATE_FORCE re-rate,
                    # this row may snapshot stale rater scores; delete the
                    # affected cgm_arbitrations rows to force re-arbitration.
                    continue
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
                    (country, dim, a["score"], b["score"], score, model, reasoning),
                )
            conn.commit()
