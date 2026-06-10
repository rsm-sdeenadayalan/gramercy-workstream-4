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
