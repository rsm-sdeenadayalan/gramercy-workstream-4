"""CGM QA gate. Pure check_* functions return lists of failure strings; main()
fetches from the DB, runs every check, computes+stores kappa, prints a report,
and exits 1 on any failure. Re-runnable: kappa rows for the run are replaced,
never duplicated."""
import math
import sys

import cgm_db
from cgm_kappa import agreement_stats, linear_weighted_kappa
from cgm_rubrics import COUNTRIES, DIMENSIONS, WEIGHTS

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


def check_weights(weights):
    total = sum(weights.values())
    if not math.isclose(total, 1.0):
        return [f"dimension weights sum to {total}, not 1.0"]
    return []


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

    # Guard: only append pooled row if there is paired data; otherwise
    # agreement_stats would divide by zero and kappa would be meaningless.
    if pooled_a:
        rows_out.append(("pooled", pooled_a, pooled_b))

    with conn.cursor() as cur:
        cur.execute("DELETE FROM cgm_kappa_results WHERE run_id = %s", (run_id,))
    conn.commit()

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
        + check_weights(WEIGHTS)
    )
    if not final_rows:
        failures.append("no final scores for latest run - scoring phase not run")

    print("=== CGM VERIFY ===")
    for row in kappa_rows:
        if row["degenerate"]:
            if row["raw_agreement"] == 1.0:
                kappa_txt = "N/A (degenerate - perfect agreement)"
            else:
                kappa_txt = "N/A (degenerate)"
        else:
            kappa_txt = f"{row['kappa_linear']:.3f}"
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
