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
