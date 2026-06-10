"""Create the `cgm` database (if missing) and apply the schema. Idempotent."""
import os

from psycopg2 import sql

import cgm_db


def main():
    target = os.environ.get("CGM_DB", "cgm")
    bootstrap = os.environ.get("POSTGRES_BOOTSTRAP_DB", "postgres")
    conn = cgm_db.connect(dbname=bootstrap)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,))
        if not cur.fetchone():
            cur.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target)))
            print(f"created database {target}")
    conn.close()

    conn = cgm_db.connect()
    with conn.cursor() as cur:
        cur.execute(cgm_db.SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()
    print(f"schema applied to {target}")


if __name__ == "__main__":
    main()
