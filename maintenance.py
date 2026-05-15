"""
maintenance.py
--------------
Storage optimization and maintenance script for the
Stock Market Data Warehouse.

Features:
  - Monitor DB size and table sizes
  - Apply configurable data retention policy
  - VACUUM & ANALYZE all tables
  - Refresh materialized views
  - Remove duplicate fact rows
  - Log all actions with timestamps

Run: .\\venv\\Scripts\\python.exe maintenance.py
Run with cleanup: .\\venv\\Scripts\\python.exe maintenance.py --clean --retain-years 5
"""

import os
import sys
import argparse
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────
DEFAULT_RETAIN_YEARS = 5     # Keep last N years of fact data
WARN_SIZE_MB         = 500   # Warn if DB exceeds this size (MB)
CRITICAL_SIZE_MB     = 1000  # Critical if DB exceeds this (MB)


# ── Logging ────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": "\033[36m", "WARN": "\033[33m",
              "OK": "\033[32m",   "ERR": "\033[31m", "HEAD": "\033[35m"}
    reset = "\033[0m"
    c = colors.get(level, "")
    print(f"  {c}[{level}]{reset} {ts}  {msg}")


# ── DB Connection ───────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5433)),
        dbname=os.getenv("DB_NAME", "warehouse_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def query(conn, sql, params=None, fetch=True):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        if fetch:
            return [dict(r) for r in cur.fetchall()]
        conn.commit()
        return cur.rowcount


# ── 1. STORAGE REPORT ───────────────────────────────────────────
def report_storage(conn):
    print()
    log("=" * 52, "HEAD")
    log("  STORAGE REPORT", "HEAD")
    log("=" * 52, "HEAD")

    # DB size
    rows = query(conn, """
        SELECT pg_size_pretty(pg_database_size(current_database())) AS size,
               pg_database_size(current_database()) / 1048576.0 AS size_mb
    """)
    size_mb = float(rows[0]["size_mb"])
    size_str = rows[0]["size"]

    if size_mb >= CRITICAL_SIZE_MB:
        log(f"Database size: {size_str}  ⚠️  CRITICAL — run cleanup!", "ERR")
    elif size_mb >= WARN_SIZE_MB:
        log(f"Database size: {size_str}  ⚠️  WARNING", "WARN")
    else:
        log(f"Database size: {size_str}  ✅ Healthy", "OK")

    # Table breakdown
    tables = query(conn, """
        SELECT relname AS tbl,
               pg_size_pretty(pg_total_relation_size(relid)) AS total,
               n_live_tup AS live,
               n_dead_tup AS dead
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
    """)

    print()
    print(f"  {'Table':<35} {'Size':>10} {'Live Rows':>12} {'Dead Rows':>10}")
    print(f"  {'-'*35} {'-'*10} {'-'*12} {'-'*10}")
    for t in tables:
        dead_flag = " ⚠️" if int(t["dead"] or 0) > 10000 else ""
        print(f"  {t['tbl']:<35} {t['total']:>10} {str(t['live'] or 0):>12} {str(t['dead'] or 0):>10}{dead_flag}")

    # Fact date range
    dates = query(conn, """
        SELECT MIN(d.full_date) AS oldest, MAX(d.full_date) AS newest, COUNT(*) AS rows
        FROM fact_stock_prices f
        JOIN dim_date d ON f.date_key = d.date_key
    """)
    if dates:
        d = dates[0]
        print()
        log(f"Fact rows: {int(d['rows']):,}  |  Range: {d['oldest']} → {d['newest']}", "INFO")

    return size_mb


# ── 2. CHECK DUPLICATES ─────────────────────────────────────────
def check_duplicates(conn):
    print()
    log("Checking for duplicate fact rows...", "INFO")
    rows = query(conn, """
        SELECT COUNT(*) AS dup_groups
        FROM (
            SELECT stock_key, date_key
            FROM fact_stock_prices
            GROUP BY stock_key, date_key
            HAVING COUNT(*) > 1
        ) x
    """)
    dup = int(rows[0]["dup_groups"])
    if dup > 0:
        log(f"Found {dup} duplicate groups — run with --clean to fix", "WARN")
    else:
        log("No duplicate rows found ✅", "OK")
    return dup


# ── 3. RETENTION POLICY ─────────────────────────────────────────
def apply_retention(conn, retain_years, dry_run=True):
    print()
    log(f"Retention policy: keep last {retain_years} years", "INFO")

    preview = query(conn, f"""
        SELECT COUNT(*) AS cnt
        FROM fact_stock_prices f
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.full_date < NOW() - INTERVAL '{retain_years} years'
    """)
    old_rows = int(preview[0]["cnt"])

    if old_rows == 0:
        log(f"No rows older than {retain_years} years — nothing to delete ✅", "OK")
        return 0

    if dry_run:
        log(f"DRY RUN: Would delete {old_rows:,} rows older than {retain_years} years", "WARN")
        log("Run with --clean to apply the deletion", "WARN")
    else:
        log(f"Deleting {old_rows:,} rows older than {retain_years} years...", "WARN")
        query(conn, f"""
            DELETE FROM fact_stock_prices f
            USING dim_date d
            WHERE f.date_key = d.date_key
              AND d.full_date < NOW() - INTERVAL '{retain_years} years'
        """, fetch=False)
        log(f"Deleted {old_rows:,} old rows ✅", "OK")

    return old_rows


# ── 4. REMOVE DUPLICATES ────────────────────────────────────────
def remove_duplicates(conn, dry_run=True):
    if dry_run:
        return
    log("Removing duplicate fact rows...", "INFO")
    deleted = query(conn, """
        DELETE FROM fact_stock_prices
        WHERE ctid NOT IN (
            SELECT MIN(ctid)
            FROM fact_stock_prices
            GROUP BY stock_key, date_key
        )
    """, fetch=False)
    log(f"Removed {deleted} duplicate rows ✅", "OK")


# ── 5. VACUUM & ANALYZE ─────────────────────────────────────────
def vacuum_tables(conn):
    print()
    log("Running VACUUM ANALYZE on all tables...", "INFO")
    tables = [
        "fact_stock_prices", "dim_stock", "dim_date",
        "dim_sector", "dim_country", "dim_exchange", "dim_market_cap_tier"
    ]
    # VACUUM needs its own autocommit connection
    vconn = psycopg2.connect(
        host=os.getenv("DB_HOST","127.0.0.1"), port=int(os.getenv("DB_PORT",5433)),
        dbname=os.getenv("DB_NAME","warehouse_db"),
        user=os.getenv("DB_USER","postgres"), password=os.getenv("DB_PASSWORD")
    )
    vconn.autocommit = True
    try:
        with vconn.cursor() as cur:
            for tbl in tables:
                cur.execute(f"VACUUM ANALYZE {tbl}")
                log(f"  VACUUM ANALYZE {tbl} OK", "OK")
    finally:
        vconn.close()


# ── 6. REFRESH VIEWS ────────────────────────────────────────────
def refresh_views(conn):
    print()
    log("Refreshing materialized views...", "INFO")
    views = [
        "mv_sector_performance_daily",
        "mv_stock_monthly_summary",
        "mv_market_cap_tier_quarterly",
    ]
    vconn = psycopg2.connect(
        host=os.getenv("DB_HOST","127.0.0.1"), port=int(os.getenv("DB_PORT",5433)),
        dbname=os.getenv("DB_NAME","warehouse_db"),
        user=os.getenv("DB_USER","postgres"), password=os.getenv("DB_PASSWORD")
    )
    vconn.autocommit = True
    try:
        with vconn.cursor() as cur:
            for v in views:
                try:
                    cur.execute(f"REFRESH MATERIALIZED VIEW {v}")
                    log(f"  Refreshed {v} OK", "OK")
                except Exception as e:
                    log(f"  Skipped {v}: {e}", "WARN")
    finally:
        vconn.close()


# ── MAIN ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Data Warehouse Maintenance Script")
    parser.add_argument("--clean",        action="store_true", help="Apply deletions (default: dry run)")
    parser.add_argument("--retain-years", type=int, default=DEFAULT_RETAIN_YEARS,
                        help=f"Years of data to keep (default: {DEFAULT_RETAIN_YEARS})")
    parser.add_argument("--skip-vacuum",  action="store_true", help="Skip VACUUM step")
    parser.add_argument("--skip-views",   action="store_true", help="Skip view refresh")
    args = parser.parse_args()

    dry_run = not args.clean

    sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
    print()
    print("  +==================================================+")
    print("  |   Stock Market Data Warehouse -- Maintenance     |")
    print("  +==================================================+")
    if dry_run:
        print()
        log("Running in DRY RUN mode (no data will be deleted)", "WARN")
        log("Use --clean flag to apply changes", "WARN")

    conn = get_conn()
    try:
        report_storage(conn)
        check_duplicates(conn)
        apply_retention(conn, args.retain_years, dry_run=dry_run)
        if args.clean:
            remove_duplicates(conn, dry_run=False)
        if not args.skip_vacuum:
            vacuum_tables(conn)
        if not args.skip_views:
            refresh_views(conn)
        print()
        log("Maintenance complete ✅", "OK")
        print()
    except Exception as e:
        log(f"Error: {e}", "ERR")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
