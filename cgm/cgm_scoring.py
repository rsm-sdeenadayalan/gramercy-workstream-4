"""Final-score combination, weighted composite, and ±10pp weight sensitivity.
Pure functions + one DB writer. Combination rule (spec): equal -> score;
differ by 1 -> mean (half-points allowed); differ by >1 -> arbiter ruling."""
import json

from cgm_rubrics import ARCHETYPE, COUNTRIES, DIMENSIONS, WEIGHTS


def resolve_arbitration(rater_scores, arb_row):
    """arb_row = (rater_a_score, rater_b_score, resolved_score) or None.
    Returns resolved_score or None, raising if the snapshot is stale."""
    if arb_row is None:
        return None
    stored = (arb_row[0], arb_row[1])
    if stored != tuple(rater_scores):
        raise ValueError(
            f"stale arbitration: stored rater scores {stored} != current "
            f"{tuple(rater_scores)} - delete the cgm_arbitrations row and re-run"
            " --only arbitrate"
        )
    return arb_row[2]


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
                    "SELECT rater_a_score, rater_b_score, resolved_score"
                    " FROM cgm_arbitrations"
                    " WHERE country_iso=%s AND dimension=%s", (country, dim),
                )
                arb = cur.fetchone()
            if len(rows) != 2:
                raise SystemExit(
                    f"cannot score: missing rater score for {country}/{dim}"
                    " (see cgm_data_gaps)"
                )
            dims[dim] = combine_scores(rows[0][1], rows[1][1],
                                       resolve_arbitration([rows[0][1], rows[1][1]], arb))
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
