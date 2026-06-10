"""Shared DB access for the CGM pipeline. All modules get connections from here."""
import os
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SCHEMA_PATH = Path(__file__).resolve().parent / "cgm_schema.sql"


def connect(dbname=None):
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=dbname or os.environ.get("CGM_DB", "cgm"),
    )


def start_run(conn):
    run_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("INSERT INTO cgm_runs (run_id) VALUES (%s)", (run_id,))
    conn.commit()
    return run_id


def log_phase(conn, run_id, phase):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cgm_runs SET phases = phases || %s::text WHERE run_id = %s",
            (phase, run_id),
        )
    conn.commit()


def finish_run(conn, run_id):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cgm_runs SET finished_at = now() WHERE run_id = %s", (run_id,)
        )
    conn.commit()


def log_collection(conn, run_id, source, status, detail=""):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO cgm_collection_log (run_id, source, status, detail)"
            " VALUES (%s, %s, %s, %s)",
            (run_id, source, status, detail[:2000]),
        )
    conn.commit()


def add_gap(conn, run_id, country_iso, dimension, gap, severity="warn"):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO cgm_data_gaps (run_id, country_iso, dimension, gap, severity)"
            " VALUES (%s, %s, %s, %s, %s)",
            (run_id, country_iso, dimension, gap, severity),
        )
    conn.commit()
