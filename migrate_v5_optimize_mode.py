#!/usr/bin/env python3
"""
Migration: v5 — flight-time optimization mode

New columns:
  price_history.duration_minutes  — total journey duration in minutes
  users.optimize_for              — user's default mode (cheapest/fastest/best_value)
  user_routes.optimize_for        — per-route override (NULL = inherit from user)

New table:
  app_config — admin-editable key/value params (seeds effective-cost coefficients)

Run once against the production database:
  DB_PATH=/home/flightmonitor/instance/flight_monitor.db python migrate_v5_optimize_mode.py
"""
import os
import sqlite3

DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "instance", "flight_monitor.db"),
)


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def run():
    print(f"Database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── New columns ──────────────────────────────────────────────────────────

    column_migrations = [
        (
            "price_history",
            "duration_minutes",
            "ALTER TABLE price_history ADD COLUMN duration_minutes INTEGER",
        ),
        (
            "users",
            "optimize_for",
            "ALTER TABLE users ADD COLUMN optimize_for VARCHAR(15) DEFAULT 'cheapest'",
        ),
        (
            "user_routes",
            "optimize_for",
            "ALTER TABLE user_routes ADD COLUMN optimize_for VARCHAR(15)",
        ),
    ]

    for table, col, stmt in column_migrations:
        if column_exists(cur, table, col):
            print(f"  {table}.{col} — already exists, skipped")
        else:
            cur.execute(stmt)
            print(f"  {table}.{col} — added")

    # ── app_config table ─────────────────────────────────────────────────────

    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_config (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            key        TEXT UNIQUE NOT NULL,
            value      TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  app_config table — ready")

    # Seed default effective-cost coefficients (AUD).
    # These drive 'best_value' mode only; adjust via admin UI once built.
    #   time_value_aud_per_hour: what an hour of journey time is worth in AUD
    #   stop_penalty_aud:        cost premium applied per stop
    defaults = [
        ("time_value_aud_per_hour", "12.0"),
        ("stop_penalty_aud",        "40.0"),
    ]
    for key, value in defaults:
        cur.execute(
            "INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)",
            (key, value),
        )
        print(f"  app_config {key} = {value} (seeded if new)")

    conn.commit()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    run()
