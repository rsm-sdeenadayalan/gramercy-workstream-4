"""Evidence packs: Tavily search per checklist item, Claude claim extraction,
coverage measurement. Packs are immutable inputs to the raters - raters never
see the live web. Claims citing URLs not returned by search are dropped
(anti-fabrication guard)."""
import json
import os

import requests

import cgm_db
from cgm_llm import call_llm, extract_json
from cgm_rubrics import COUNTRIES, COUNTRY_NAMES, DIMENSIONS, checklist_for

TAVILY_URL = "https://api.tavily.com/search"

EXTRACT_SYSTEM = """You extract factual evidence claims from web search results
for sovereign governance scoring. Output STRICT JSON:
{"claims": [{"claim": "<one-sentence factual claim>",
             "quote": "<short verbatim supporting quote from the source content>",
             "source_url": "<url of the source the quote came from>",
             "checklist_item": "<the checklist item this claim addresses>"}]}
Rules: only claims directly supported by the provided source content; source_url
must be one of the provided URLs; checklist_item must be one of the provided
items verbatim; no opinions, no scores, no speculation. Empty list if nothing
is supported. At most 2 claims per checklist item; keep each quote under 25 words."""


def tavily_search(query, max_results=5):
    resp = requests.post(
        TAVILY_URL,
        json={"api_key": os.environ["TAVILY_API_KEY"], "query": query,
              "max_results": max_results},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def build_extract_prompt(country_name, dimension, checklist, results):
    src = "\n\n".join(
        f"URL: {r['url']}\nTITLE: {r['title']}\nCONTENT: {r['content'][:1500]}"
        for r in results
    )
    items = "\n".join(f"- {i}" for i in checklist)
    return (f"Country: {country_name}\nDimension: {dimension}\n"
            f"Checklist items:\n{items}\n\nSearch results:\n{src}")


def parse_claims(llm_text, allowed_urls):
    data = extract_json(llm_text)
    out = []
    for c in data.get("claims", []):
        if not all(k in c for k in ("claim", "quote", "source_url", "checklist_item")):
            continue
        if c["source_url"] not in allowed_urls:
            continue
        out.append(c)
    return out


def coverage(checklist, claims):
    have = {c["checklist_item"] for c in claims}
    covered = [i for i in checklist if i in have]
    missing = [i for i in checklist if i not in have]
    return {"covered": covered, "missing": missing,
            "ratio": len(covered) / len(checklist)}


def collect_evidence(conn, run_id, extract_model):
    for country in COUNTRIES:
        name = COUNTRY_NAMES[country]
        for dim in DIMENSIONS:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM cgm_evidence"
                    " WHERE country_iso=%s AND dimension=%s",
                    (country, dim),
                )
                if cur.fetchone()[0] > 0:
                    continue  # pack already collected (immutable per corpus)
            checklist = checklist_for(dim, country)
            results, claims = [], []
            try:
                for item in checklist:
                    results.extend(tavily_search(f"{name} {item}"))
                if results:
                    prompt = build_extract_prompt(name, dim, checklist, results)
                    text = call_llm(extract_model, EXTRACT_SYSTEM, prompt,
                                    max_tokens=8000)
                    claims = parse_claims(text, {r["url"] for r in results})
            except Exception as err:  # noqa: BLE001 - log and skip; retry next run
                cgm_db.log_collection(conn, run_id, f"evidence:{country}:{dim}",
                                      "error", str(err))
                continue
            for c in claims:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO cgm_evidence (run_id, country_iso, dimension,
                           checklist_item, claim, quote, source_url, source_type)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, 'web')""",
                        (run_id, country, dim, c["checklist_item"], c["claim"],
                         c["quote"], c["source_url"]),
                    )
            conn.commit()
            cov = coverage(checklist, claims)
            for item in cov["missing"]:
                cgm_db.add_gap(conn, run_id, country, dim,
                               f"evidence missing for checklist item: {item}")
            cgm_db.log_collection(
                conn, run_id, f"evidence:{country}:{dim}", "ok",
                f"claims={len(claims)} coverage={cov['ratio']:.2f}",
            )
