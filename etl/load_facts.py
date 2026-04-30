"""
load_facts.py
-------------
Loads 100,400 rows into fact_stock_prices by:
  1. Building surrogate key lookup dicts from all dimension tables
  2. Mapping each raw price row's natural keys -> surrogate keys
  3. Batch-inserting into fact_stock_prices using execute_values()

Run: .\\venv\\Scripts\\python.exe etl\\load_facts.py
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 5000  # rows per INSERT batch


# ── DB connection ─────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5433)),
        dbname=os.getenv("DB_NAME", "warehouse_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


# ── Build all lookup dicts from dimension tables ──────────────────────────────
def build_lookups(cur):
    print("\n[INFO] Building dimension lookup dictionaries...")

    # date: full_date string -> date_key integer
    cur.execute("SELECT TO_CHAR(full_date, 'YYYY-MM-DD'), date_key FROM dim_date")
    date_lookup = {row[0]: row[1] for row in cur.fetchall()}
    print(f"  date_lookup      : {len(date_lookup):,} entries")

    # stock: symbol -> (stock_key, exchange_key, sector_key, country_key, cap_tier_key)
    cur.execute("""
        SELECT symbol, stock_key, exchange_key, sector_key, country_key, cap_tier_key
        FROM dim_stock
        WHERE is_current = TRUE
    """)
    stock_lookup = {
        row[0]: {
            "stock_key":    row[1],
            "exchange_key": row[2],
            "sector_key":   row[3],
            "country_key":  row[4],
            "cap_tier_key": row[5],
        }
        for row in cur.fetchall()
    }
    print(f"  stock_lookup     : {len(stock_lookup):,} entries")

    return date_lookup, stock_lookup


# ── Insert fact rows in batches ───────────────────────────────────────────────
def insert_batch(cur, batch):
    execute_values(cur, """
        INSERT INTO fact_stock_prices (
            date_key, stock_key, exchange_key, sector_key, country_key, cap_tier_key,
            open_price, high_price, low_price, close_price, adj_close_price, volume,
            price_change, daily_return_pct, high_low_spread
        ) VALUES %s
    """, batch)


# ── Main load logic ───────────────────────────────────────────────────────────
def load_facts():
    print("=" * 55)
    print("  LOAD FACTS — fact_stock_prices")
    print("=" * 55)

    # Read raw data
    print("\n[INFO] Reading raw_stock_prices.csv...")
    price_df = pd.read_csv("data/raw_stock_prices.csv", parse_dates=["date"])
    print(f"  Rows loaded  : {len(price_df):,}")
    print(f"  Symbols      : {price_df['symbol'].nunique()}")
    print(f"  Date range   : {price_df['date'].min().date()} -> {price_df['date'].max().date()}")

    conn = get_conn()

    with conn:
        with conn.cursor() as cur:

            # Check if fact table already has data
            cur.execute("SELECT COUNT(*) FROM fact_stock_prices")
            existing = cur.fetchone()[0]
            if existing > 0:
                print(f"\n[WARN] fact_stock_prices already has {existing:,} rows.")
                print("  Truncating before reload...")
                cur.execute("TRUNCATE TABLE fact_stock_prices RESTART IDENTITY;")
                print("  [OK] Table truncated.")

            # Build lookups
            date_lookup, stock_lookup = build_lookups(cur)

            # Process rows
            print("\n[INFO] Mapping and inserting fact rows...")
            batch        = []
            inserted     = 0
            skipped      = 0
            skipped_syms = set()
            skipped_dates= set()

            for _, row in price_df.iterrows():
                symbol   = str(row["symbol"]).strip()
                date_str = row["date"].strftime("%Y-%m-%d")

                # Resolve dimension keys
                date_key  = date_lookup.get(date_str)
                stock_info = stock_lookup.get(symbol)

                if date_key is None:
                    skipped_dates.add(date_str)
                    skipped += 1
                    continue

                if stock_info is None:
                    skipped_syms.add(symbol)
                    skipped += 1
                    continue

                # Safe numeric conversion
                def safe_float(v):
                    try:
                        return round(float(v), 4) if v is not None and str(v) != "nan" else None
                    except (ValueError, TypeError):
                        return None

                def safe_int(v):
                    try:
                        return int(float(v)) if v is not None and str(v) != "nan" else None
                    except (ValueError, TypeError):
                        return None

                batch.append((
                    date_key,
                    stock_info["stock_key"],
                    stock_info["exchange_key"],
                    stock_info["sector_key"],
                    stock_info["country_key"],
                    stock_info["cap_tier_key"],
                    safe_float(row["open"]),
                    safe_float(row["high"]),
                    safe_float(row["low"]),
                    safe_float(row["close"]),
                    safe_float(row.get("adj_close")),
                    safe_int(row["volume"]),
                    safe_float(row.get("price_change")),
                    safe_float(row.get("daily_return_pct")),
                    safe_float(row.get("high_low_spread")),
                ))

                # Flush batch
                if len(batch) >= BATCH_SIZE:
                    insert_batch(cur, batch)
                    inserted += len(batch)
                    batch = []
                    print(f"  Inserted {inserted:,} rows so far...")

            # Final batch
            if batch:
                insert_batch(cur, batch)
                inserted += len(batch)

            # Final stats
            cur.execute("SELECT COUNT(*) FROM fact_stock_prices")
            total_in_db = cur.fetchone()[0]

    conn.close()

    print("\n" + "=" * 55)
    print("  LOAD FACTS — COMPLETE")
    print("=" * 55)
    print(f"  Rows inserted  : {inserted:,}")
    print(f"  Rows in DB     : {total_in_db:,}")
    print(f"  Rows skipped   : {skipped}")
    if skipped_syms:
        print(f"  Unknown symbols: {skipped_syms}")
    if skipped_dates:
        print(f"  Unknown dates  : {len(skipped_dates)} dates skipped")
    if total_in_db >= 100000:
        print("  [TARGET MET] 100,000+ rows in fact table!")
    print("\n  Next step: run etl/verify_warehouse.py")
    print("=" * 55)


if __name__ == "__main__":
    load_facts()
