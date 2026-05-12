"""
scd_demo.py
-----------
Demonstrates Slowly Changing Dimension (SCD) Type 2 logic by simulating 
a company change (e.g., Apple changing its industry or sector).

This script:
1.  Connects to the database.
2.  Identifies the current record for 'AAPL'.
3.  Simulates a change by closing the old record and opening a new one.
4.  Shows the results in both dim_stock and how it affects fact table lookups.
"""

import os
import psycopg2
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5433)),
        dbname=os.getenv("DB_NAME", "warehouse_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

def run_demo():
    print("=" * 60)
    print("  SCD TYPE 2 LIVE DEMO: Apple (AAPL) Sector Change")
    print("=" * 60)

    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            # 1. Check current state of AAPL
            print("\n[STEP 1] Checking current AAPL record...")
            cur.execute("""
                SELECT stock_key, symbol, company_name, industry, version, is_current, effective_from, effective_to
                FROM dim_stock
                WHERE symbol = 'AAPL' AND is_current = TRUE
            """)
            current_aapl = cur.fetchone()
            
            if not current_aapl:
                print("  [ERROR] AAPL not found in dim_stock. Please run ETL first.")
                return

            stock_key, symbol, name, industry, version, is_current, eff_from, eff_to = current_aapl
            print(f"  Current Key     : {stock_key}")
            print(f"  Current Industry: {industry}")
            print(f"  Version         : {version}")
            print(f"  Effective From  : {eff_from}")

            # 2. Simulate a change: AAPL moves from 'Consumer Electronics' to 'AI & Personal Computing'
            print("\n[STEP 2] Simulating Industry Change: 'AI & Personal Computing'...")
            new_industry = "AI & Personal Computing"
            change_date = date.today()
            yesterday = change_date - timedelta(days=1)

            # Close old record
            cur.execute("""
                UPDATE dim_stock
                SET effective_to = %s,
                    is_current   = FALSE,
                    updated_at   = NOW()
                WHERE stock_key = %s
            """, (yesterday, stock_key))

            # Insert new record
            cur.execute("""
                INSERT INTO dim_stock (
                    symbol, company_name, sector_key, exchange_key,
                    country_key, cap_tier_key, industry, market_cap_tier,
                    country, currency, market_cap, employees, website, description,
                    effective_from, effective_to, is_current, version
                )
                SELECT 
                    symbol, company_name, sector_key, exchange_key,
                    country_key, cap_tier_key, %s, market_cap_tier,
                    country, currency, market_cap, employees, website, description,
                    %s, '9999-12-31', TRUE, %s
                FROM dim_stock
                WHERE stock_key = %s
                RETURNING stock_key
            """, (new_industry, change_date, version + 1, stock_key))
            
            new_stock_key = cur.fetchone()[0]
            print(f"  [OK] Old record closed (effective_to: {yesterday})")
            print(f"  [OK] New record created (stock_key: {new_stock_key}, version: {version+1})")

            # 3. Show historical preservation
            print("\n[STEP 3] Verifying Historical Preservation...")
            cur.execute("""
                SELECT stock_key, industry, version, is_current, effective_from, effective_to
                FROM dim_stock
                WHERE symbol = 'AAPL'
                ORDER BY version ASC
            """)
            print("\n  Historical Records for AAPL:")
            print("  KEY | INDUSTRY                 | VER | CURR  | FROM       | TO")
            print("  ----|--------------------------|-----|-------|------------|-----------")
            for row in cur.fetchall():
                k, ind, v, curr, f, t = row
                print(f"  {k:<3} | {ind:<24} | {v:<3} | {str(curr):<5} | {f} | {t}")

            print("\n[SUCCESS] SCD Type 2 Demo Complete!")
            print("  Notice how the old stock_key remains valid for old fact rows,")
            print("  preserving the history of what AAPL's industry WAS at that time.")

    conn.close()

if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Make sure your PostgreSQL server is running and .env is configured.")
