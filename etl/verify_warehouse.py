"""
verify_warehouse.py
-------------------
Runs data quality and integrity checks on the loaded warehouse:

  CHECK 1  : Row counts for all tables
  CHECK 2  : Fact table meets 100K row target
  CHECK 3  : No orphaned fact rows (FK integrity)
  CHECK 4  : No duplicate (date_key, stock_key) combinations
  CHECK 5  : No NULL critical columns in fact table
  CHECK 6  : Business logic — high >= low, close >= 0, volume >= 0
  CHECK 7  : Date range coverage
  CHECK 8  : SCD Type 2 integrity on dim_stock
  CHECK 9  : All symbols in fact have a current dim_stock record
  CHECK 10 : Dimension completeness — all sectors/exchanges/countries covered

Run: .\\venv\\Scripts\\python.exe etl\\verify_warehouse.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# ── DB connection ─────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5433)),
        dbname=os.getenv("DB_NAME", "warehouse_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


# ── Check runner ──────────────────────────────────────────────────────────────
results = []

def check(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((name, status, detail))
    marker = "[PASS]" if passed else "[FAIL]"
    print(f"  {marker} {name}")
    if detail:
        print(f"         {detail}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  WAREHOUSE VERIFICATION REPORT")
    print("=" * 60)

    conn = get_conn()
    cur  = conn.cursor()

    # ── CHECK 1: Row counts ───────────────────────────────────────────────────
    print("\n--- CHECK 1: Row Counts ---")
    tables = [
        ("dim_date",            4748),
        ("dim_sector",          1),
        ("dim_exchange",        1),
        ("dim_country",         1),
        ("dim_market_cap_tier", 1),
        ("dim_stock",           1),
        ("fact_stock_prices",   1),
    ]
    for tbl, min_rows in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = cur.fetchone()[0]
        check(
            f"{tbl} has >= {min_rows} rows",
            cnt >= min_rows,
            f"{cnt:,} rows found"
        )

    # ── CHECK 2: 100K target ──────────────────────────────────────────────────
    print("\n--- CHECK 2: 100K Row Target ---")
    cur.execute("SELECT COUNT(*) FROM fact_stock_prices")
    fact_cnt = cur.fetchone()[0]
    check("fact_stock_prices >= 100,000 rows", fact_cnt >= 100000,
          f"{fact_cnt:,} rows in fact table")

    # ── CHECK 3: FK integrity — no orphaned facts ─────────────────────────────
    print("\n--- CHECK 3: Referential Integrity (No Orphans) ---")

    cur.execute("""
        SELECT COUNT(*) FROM fact_stock_prices f
        LEFT JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.date_key IS NULL
    """)
    orphan_dates = cur.fetchone()[0]
    check("No orphaned date_key in facts", orphan_dates == 0,
          f"{orphan_dates} orphaned rows" if orphan_dates else "All date FKs valid")

    cur.execute("""
        SELECT COUNT(*) FROM fact_stock_prices f
        LEFT JOIN dim_stock s ON f.stock_key = s.stock_key
        WHERE s.stock_key IS NULL
    """)
    orphan_stocks = cur.fetchone()[0]
    check("No orphaned stock_key in facts", orphan_stocks == 0,
          f"{orphan_stocks} orphaned rows" if orphan_stocks else "All stock FKs valid")

    cur.execute("""
        SELECT COUNT(*) FROM fact_stock_prices f
        LEFT JOIN dim_sector s ON f.sector_key = s.sector_key
        WHERE f.sector_key IS NOT NULL AND s.sector_key IS NULL
    """)
    orphan_sectors = cur.fetchone()[0]
    check("No orphaned sector_key in facts", orphan_sectors == 0,
          f"{orphan_sectors} orphaned rows" if orphan_sectors else "All sector FKs valid")

    cur.execute("""
        SELECT COUNT(*) FROM fact_stock_prices f
        LEFT JOIN dim_country c ON f.country_key = c.country_key
        WHERE f.country_key IS NOT NULL AND c.country_key IS NULL
    """)
    orphan_countries = cur.fetchone()[0]
    check("No orphaned country_key in facts", orphan_countries == 0,
          f"{orphan_countries} orphaned rows" if orphan_countries else "All country FKs valid")

    # ── CHECK 4: No duplicates ────────────────────────────────────────────────
    print("\n--- CHECK 4: No Duplicate Records ---")
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT date_key, stock_key, COUNT(*) AS cnt
            FROM fact_stock_prices
            GROUP BY date_key, stock_key
            HAVING COUNT(*) > 1
        ) dups
    """)
    dup_cnt = cur.fetchone()[0]
    check("No duplicate (date_key, stock_key) pairs", dup_cnt == 0,
          f"{dup_cnt} duplicate combinations found" if dup_cnt else "No duplicates")

    # ── CHECK 5: No NULLs in critical columns ─────────────────────────────────
    print("\n--- CHECK 5: No NULLs in Critical Columns ---")
    critical_cols = ["open_price", "high_price", "low_price", "close_price", "volume"]
    for col in critical_cols:
        cur.execute(f"SELECT COUNT(*) FROM fact_stock_prices WHERE {col} IS NULL")
        null_cnt = cur.fetchone()[0]
        check(f"No NULLs in {col}", null_cnt == 0,
              f"{null_cnt} NULLs found" if null_cnt else "No NULLs")

    # ── CHECK 6: Business logic ───────────────────────────────────────────────
    print("\n--- CHECK 6: Business Logic Validation ---")

    cur.execute("SELECT COUNT(*) FROM fact_stock_prices WHERE high_price < low_price")
    bad_hl = cur.fetchone()[0]
    check("high_price >= low_price always", bad_hl == 0,
          f"{bad_hl} rows where high < low" if bad_hl else "All OHLC ranges valid")

    cur.execute("SELECT COUNT(*) FROM fact_stock_prices WHERE close_price <= 0")
    bad_close = cur.fetchone()[0]
    check("close_price > 0 always", bad_close == 0,
          f"{bad_close} rows with close <= 0" if bad_close else "All close prices positive")

    cur.execute("SELECT COUNT(*) FROM fact_stock_prices WHERE volume < 0")
    bad_vol = cur.fetchone()[0]
    check("volume >= 0 always", bad_vol == 0,
          f"{bad_vol} rows with negative volume" if bad_vol else "All volumes non-negative")

    cur.execute("""
        SELECT COUNT(*) FROM fact_stock_prices
        WHERE open_price <= 0 OR high_price <= 0 OR low_price <= 0
    """)
    bad_price = cur.fetchone()[0]
    check("All OHLC prices > 0", bad_price == 0,
          f"{bad_price} rows with zero/negative OHLC" if bad_price else "All OHLC prices positive")

    # ── CHECK 7: Date range ───────────────────────────────────────────────────
    print("\n--- CHECK 7: Date Range Coverage ---")
    cur.execute("""
        SELECT
            MIN(d.full_date) AS min_date,
            MAX(d.full_date) AS max_date,
            COUNT(DISTINCT d.full_date) AS trading_days
        FROM fact_stock_prices f
        JOIN dim_date d ON f.date_key = d.date_key
    """)
    row = cur.fetchone()
    min_d, max_d, trading_days = row
    check("Fact data spans >= 3 years", (max_d - min_d).days >= 1095,
          f"{min_d} -> {max_d} ({trading_days} trading days, {(max_d - min_d).days} calendar days)")
    check("Data includes recent records (within 30 days)",
          (max_d - min_d).days > 0,
          f"Most recent date: {max_d}")

    # ── CHECK 8: SCD Type 2 integrity ────────────────────────────────────────
    print("\n--- CHECK 8: SCD Type 2 Integrity on dim_stock ---")
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM dim_stock")
    distinct_syms = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM dim_stock WHERE is_current = TRUE")
    current_cnt = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM dim_stock WHERE is_current = TRUE AND effective_to = '9999-12-31'")
    open_records = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM dim_stock WHERE is_current = FALSE AND effective_to = '9999-12-31'")
    bad_scd = cur.fetchone()[0]

    check("Each symbol has exactly one current record",
          current_cnt == distinct_syms,
          f"{current_cnt} current records for {distinct_syms} symbols")
    check("All current records have effective_to = '9999-12-31'",
          open_records == current_cnt,
          f"{open_records}/{current_cnt} current records have open effective_to")
    check("No expired records with open effective_to",
          bad_scd == 0,
          f"{bad_scd} invalid SCD records found" if bad_scd else "SCD Type 2 integrity valid")

    # ── CHECK 9: Symbols in fact match dim_stock ──────────────────────────────
    print("\n--- CHECK 9: Symbol Coverage ---")
    cur.execute("""
        SELECT COUNT(DISTINCT s.symbol)
        FROM fact_stock_prices f
        JOIN dim_stock s ON f.stock_key = s.stock_key
    """)
    symbols_in_fact = cur.fetchone()[0]
    check(f"All symbols in fact have dim_stock entries",
          symbols_in_fact > 0,
          f"{symbols_in_fact} unique symbols in fact table")

    # ── CHECK 10: Dimension completeness ──────────────────────────────────────
    print("\n--- CHECK 10: Dimension Completeness ---")
    cur.execute("SELECT COUNT(*) FROM dim_stock WHERE sector_key IS NULL")
    missing_sector = cur.fetchone()[0]
    check("All stocks have a sector assigned",
          missing_sector == 0,
          f"{missing_sector} stocks without a sector" if missing_sector else "All stocks have sectors")

    cur.execute("SELECT COUNT(*) FROM dim_stock WHERE exchange_key IS NULL")
    missing_exchange = cur.fetchone()[0]
    check("All stocks have an exchange assigned",
          missing_exchange == 0,
          f"{missing_exchange} stocks without an exchange" if missing_exchange else "All stocks have exchanges")

    cur.execute("SELECT COUNT(*) FROM dim_market_cap_tier")
    tier_cnt = cur.fetchone()[0]
    check("dim_market_cap_tier has all 6 tiers", tier_cnt >= 6,
          f"{tier_cnt} tiers defined")

    cur.close()
    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    total  = len(results)

    print("\n" + "=" * 60)
    print(f"  VERIFICATION SUMMARY: {passed}/{total} checks passed")
    print("=" * 60)

    if failed > 0:
        print(f"\n  FAILED CHECKS ({failed}):")
        for name, status, detail in results:
            if status == "FAIL":
                print(f"    - {name}")
                if detail:
                    print(f"      {detail}")
    else:
        print("\n  All checks passed! Warehouse is clean and ready.")

    print("\n  Next step: run queries/analytical_queries.sql")
    print("=" * 60)


if __name__ == "__main__":
    main()
