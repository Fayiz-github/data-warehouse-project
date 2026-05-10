"""
load_dimensions.py
------------------
Populates dimension tables from raw CSV data:
  - dim_sector         : unique sectors from company_metadata.csv
  - dim_exchange       : unique exchanges (merges with seeded rows)
  - dim_country        : countries where companies are headquartered
  - dim_market_cap_tier: already seeded in SQL, just build lookup
  - dim_stock          : one row per company (with SCD Type 2 logic)

Run: .\\venv\\Scripts\\python.exe etl\\load_dimensions.py
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
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


# ── Helper: derive market cap tier ───────────────────────────────────────────
def market_cap_tier(cap):
    try:
        cap = float(cap)
        if cap >= 200_000_000_000:  return "Mega-cap"
        if cap >= 10_000_000_000:   return "Large-cap"
        if cap >= 2_000_000_000:    return "Mid-cap"
        if cap >= 300_000_000:      return "Small-cap"
        return "Micro-cap"
    except (TypeError, ValueError):
        return "Unknown"


# ── LOAD DIM_SECTOR ───────────────────────────────────────────────────────────
def load_dim_sector(cur, meta_df):
    print("\n[INFO] Loading dim_sector...")

    # Get unique sectors from metadata
    sectors = meta_df[["sector", "industry"]].dropna(subset=["sector"])
    sectors = sectors[sectors["sector"].str.strip() != ""]
    unique_sectors = sectors.drop_duplicates(subset=["sector"])

    rows = []
    for _, row in unique_sectors.iterrows():
        rows.append((
            row["sector"].strip(),
            row["industry"].strip() if pd.notna(row["industry"]) else None,
        ))

    execute_values(cur, """
        INSERT INTO dim_sector (sector_name, industry_group)
        VALUES %s
        ON CONFLICT DO NOTHING
    """, rows)

    cur.execute("SELECT COUNT(*) FROM dim_sector")
    count = cur.fetchone()[0]
    print(f"  [OK] dim_sector: {count} rows")


# ── LOAD DIM_EXCHANGE ─────────────────────────────────────────────────────────
def load_dim_exchange(cur, meta_df):
    print("\n[INFO] Loading dim_exchange...")

    # Add any new exchanges found in metadata (some may not be in seed data)
    exchanges = meta_df[["exchange"]].dropna()
    exchanges = exchanges[exchanges["exchange"].str.strip() != ""]
    unique_exchanges = exchanges["exchange"].str.strip().unique()

    rows = []
    for ex in unique_exchanges:
        rows.append((ex, f"{ex} Exchange", "USA", "America/New_York", "USD"))

    execute_values(cur, """
        INSERT INTO dim_exchange (exchange_code, exchange_name, country, timezone, currency)
        VALUES %s
        ON CONFLICT (exchange_code) DO NOTHING
    """, rows)

    cur.execute("SELECT COUNT(*) FROM dim_exchange")
    count = cur.fetchone()[0]
    print(f"  [OK] dim_exchange: {count} rows")


# ── LOAD DIM_COUNTRY ─────────────────────────────────────────────────────────
def load_dim_country(cur, meta_df):
    print("\n[INFO] Loading dim_country...")

    # Map country names from metadata to standard codes
    country_name_to_code = {
        "United States": "USA", "US": "USA",
        "United Kingdom": "GBR", "UK": "GBR",
        "China": "CHN", "Japan": "JPN",
        "Germany": "DEU", "France": "FRA",
        "Canada": "CAN", "Australia": "AUS", "India": "IND",
    }

    countries = meta_df[["country"]].dropna()
    countries = countries[countries["country"].str.strip() != ""]
    unique_countries = countries["country"].str.strip().unique()

    rows = []
    for c in unique_countries:
        code = country_name_to_code.get(c, "OTHER")
        if code == "OTHER":
            rows.append((c[:10], c, "Unknown", "Unknown", "USD", "Unknown"))

    if rows:
        execute_values(cur, """
            INSERT INTO dim_country (country_code, country_name, region, sub_region, currency, market_type)
            VALUES %s
            ON CONFLICT (country_code) DO NOTHING
        """, rows)

    cur.execute("SELECT COUNT(*) FROM dim_country")
    count = cur.fetchone()[0]
    print(f"  [OK] dim_country: {count} rows")


# ── LOAD DIM_STOCK (SCD Type 2) ───────────────────────────────────────────────
def load_dim_stock(cur, meta_df):
    print("\n[INFO] Loading dim_stock (SCD Type 2)...")

    # Build lookup dicts for FK resolution
    cur.execute("SELECT sector_name, sector_key FROM dim_sector")
    sector_lookup = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute("SELECT exchange_code, exchange_key FROM dim_exchange")
    exchange_lookup = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute("SELECT country_code, country_key FROM dim_country")
    country_lookup = {row[0]: row[1] for row in cur.fetchall()}
    # also map full country names
    country_name_to_code = {
        "United States": "USA", "US": "USA",
        "United Kingdom": "GBR", "China": "CHN",
        "Japan": "JPN", "Germany": "DEU", "France": "FRA",
        "Canada": "CAN", "Australia": "AUS", "India": "IND",
    }

    cur.execute("SELECT tier_name, cap_tier_key FROM dim_market_cap_tier")
    cap_tier_lookup = {row[0]: row[1] for row in cur.fetchall()}

    # Check which symbols already exist as current records
    cur.execute("SELECT symbol FROM dim_stock WHERE is_current = TRUE")
    existing_symbols = {row[0] for row in cur.fetchall()}

    new_rows    = []
    update_syms = []

    for _, row in meta_df.iterrows():
        symbol       = str(row.get("symbol", "")).strip()
        company_name = str(row.get("company_name", "")).strip() or symbol
        sector_name  = str(row.get("sector", "")).strip()
        exchange_code= str(row.get("exchange", "")).strip()
        industry     = str(row.get("industry", "")).strip() or None
        country      = str(row.get("country", "USA")).strip() or "USA"
        currency     = str(row.get("currency", "USD")).strip() or "USD"
        description  = str(row.get("description", "")).strip()[:300] or None
        website      = str(row.get("website", "")).strip() or None

        try:
            market_cap = int(float(row.get("market_cap", 0))) if row.get("market_cap") else None
        except (ValueError, TypeError):
            market_cap = None

        try:
            employees = int(float(row.get("employees", 0))) if row.get("employees") else None
        except (ValueError, TypeError):
            employees = None

        sector_key   = sector_lookup.get(sector_name)
        exchange_key = exchange_lookup.get(exchange_code, exchange_lookup.get("OTHER"))
        cap_tier     = market_cap_tier(market_cap)
        cap_tier_key = cap_tier_lookup.get(cap_tier, cap_tier_lookup.get("Unknown"))
        country_code = country_name_to_code.get(country, country[:10] if country else "OTHER")
        country_key  = country_lookup.get(country_code, country_lookup.get("OTHER"))

        if not symbol:
            continue

        if symbol in existing_symbols:
            # Symbol already loaded — check if anything has changed (SCD Type 2)
            cur.execute("""
                SELECT company_name, sector_key, industry, market_cap_tier
                FROM dim_stock
                WHERE symbol = %s AND is_current = TRUE
            """, (symbol,))
            existing = cur.fetchone()

            if existing and (
                existing[0] != company_name or
                existing[1] != sector_key   or
                existing[2] != industry     or
                existing[3] != cap_tier
            ):
                # Close the old record
                cur.execute("""
                    UPDATE dim_stock
                    SET effective_to = CURRENT_DATE - 1,
                        is_current   = FALSE,
                        updated_at   = NOW()
                    WHERE symbol = %s AND is_current = TRUE
                """, (symbol,))

                # Get new version number
                cur.execute("SELECT MAX(version) FROM dim_stock WHERE symbol = %s", (symbol,))
                max_ver = cur.fetchone()[0] or 0

                new_rows.append((
                    symbol, company_name, sector_key, exchange_key,
                    country_key, cap_tier_key,
                    industry, cap_tier, country, currency,
                    market_cap, employees, website, description,
                    "2026-01-01", "9999-12-31", True, max_ver + 1,
                ))
                update_syms.append(symbol)
        else:
            # Brand new symbol
            new_rows.append((
                symbol, company_name, sector_key, exchange_key,
                country_key, cap_tier_key,
                industry, cap_tier, country, currency,
                market_cap, employees, website, description,
                "2021-05-06", "9999-12-31", True, 1,
            ))

    if new_rows:
        execute_values(cur, """
            INSERT INTO dim_stock (
                symbol, company_name, sector_key, exchange_key,
                country_key, cap_tier_key,
                industry, market_cap_tier, country, currency,
                market_cap, employees, website, description,
                effective_from, effective_to, is_current, version
            ) VALUES %s
        """, new_rows)

    cur.execute("SELECT COUNT(*) FROM dim_stock")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM dim_stock WHERE is_current = TRUE")
    current = cur.fetchone()[0]
    print(f"  [OK] dim_stock: {total} total rows, {current} current")
    if update_syms:
        print(f"  [SCD2] Updated symbols: {update_syms}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  LOAD DIMENSIONS")
    print("=" * 50)

    meta_df = pd.read_csv("data/company_metadata.csv")
    print(f"\n[INFO] Loaded company_metadata.csv: {len(meta_df)} companies")

    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            load_dim_sector(cur, meta_df)
            load_dim_exchange(cur, meta_df)
            load_dim_country(cur, meta_df)
            load_dim_stock(cur, meta_df)

    conn.close()

    print("\n" + "=" * 50)
    print("  [DONE] All dimensions loaded successfully.")
    print("  Next step: run etl/load_facts.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
