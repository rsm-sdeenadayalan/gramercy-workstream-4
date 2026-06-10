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
