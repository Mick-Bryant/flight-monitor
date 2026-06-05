#!/usr/bin/env python3
"""
Migration: fix price_history.route_id NOT NULL constraint

The original production schema had route_id NOT NULL with a FK to the
legacy routes table. The global_routes architecture made route_id
optional, but the constraint was never relaxed, causing price checks
to fail with IntegrityError on every run.

This migration recreates price_history without the NOT NULL constraint
and without the legacy FK, preserving all existing rows.

Run once if upgrading a database that still has the original schema:
  DB_PATH=/path/to/flight_monitor.db python migrate_fix_route_id_notnull.py
"""
import os
import sqlite3

DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "instance", "flight_monitor.db"),
)


def run():
    print(f"Database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("PRAGMA table_info(price_history)")
    cols = {row[1]: row[3] for row in cur.fetchall()}  # name: notnull

    if cols.get("route_id") != 1:
        print("  price_history.route_id — already nullable, nothing to do")
        conn.close()
        return

    cur.execute("PRAGMA foreign_keys = OFF")
    cur.execute("BEGIN")
    try:
        cur.execute("""
            CREATE TABLE price_history_new (
                id               INTEGER NOT NULL PRIMARY KEY,
                route_id         INTEGER,
                price            FLOAT   NOT NULL,
                currency         VARCHAR(3) NOT NULL,
                airline          VARCHAR(100),
                checked_at       DATETIME,
                stops            INTEGER,
                is_cheapest      BOOLEAN DEFAULT 0,
                checked_date     VARCHAR(10),
                global_route_id  INTEGER,
                duration_minutes INTEGER
            )
        """)
        cur.execute("""
            INSERT INTO price_history_new
            SELECT id, route_id, price, currency, airline, checked_at,
                   stops, is_cheapest, checked_date, global_route_id, duration_minutes
            FROM price_history
        """)
        rows = cur.execute(
            "SELECT COUNT(*) FROM price_history_new"
        ).fetchone()[0]
        cur.execute("DROP TABLE price_history")
        cur.execute("ALTER TABLE price_history_new RENAME TO price_history")
        conn.commit()
        print(f"  price_history.route_id — NOT NULL removed ({rows} rows preserved)")
    except Exception as e:
        conn.rollback()
        print(f"  FAILED: {e}")
        raise
    finally:
        cur.execute("PRAGMA foreign_keys = ON")
        conn.close()

    print("Migration complete.")


if __name__ == "__main__":
    run()
