"""
dashboard_app.py
----------------
Flask API server that connects to the PostgreSQL Data Warehouse
and serves live JSON data to the interactive BI dashboard.

Run: .\\venv\\Scripts\\python.exe dashboard_app.py
Then open: http://localhost:5000
"""

import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)


# ── DB Connection ──────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5433)),
        dbname=os.getenv("DB_NAME", "warehouse_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def query(sql, params=None):
    """Execute SQL and return list of dicts."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Serve Dashboard HTML ───────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "dashboard_live.html")


# ── API: KPIs ─────────────────────────────────────────────────
@app.route("/api/kpis")
def kpis():
    rows = query("""
        SELECT
            (SELECT COUNT(*) FROM fact_stock_prices)              AS total_rows,
            (SELECT COUNT(DISTINCT symbol) FROM dim_stock
             WHERE is_current = TRUE)                             AS total_symbols,
            EXTRACT(YEAR FROM MIN(d.full_date))::int              AS date_start_year,
            EXTRACT(YEAR FROM CURRENT_DATE)::int                  AS date_end_year,
            ROUND(AVG(f.daily_return_pct)::numeric, 4)           AS avg_daily_return,
            ROUND(AVG(f.close_price)::numeric, 2)                AS avg_close_price
        FROM fact_stock_prices f
        JOIN dim_date  d ON f.date_key  = d.date_key
    """)
    # Best performing stock
    best = query("""
        SELECT s.symbol,
               ROUND(((last_v.close - first_v.close) / NULLIF(first_v.close, 0) * 100)::numeric, 2) AS total_return
        FROM (
            SELECT DISTINCT ON (stock_key) stock_key, close_price AS close
            FROM fact_stock_prices ORDER BY stock_key, date_key ASC
        ) first_v
        JOIN (
            SELECT DISTINCT ON (stock_key) stock_key, close_price AS close
            FROM fact_stock_prices ORDER BY stock_key, date_key DESC
        ) last_v ON first_v.stock_key = last_v.stock_key
        JOIN dim_stock s ON s.stock_key = first_v.stock_key AND s.is_current = TRUE
        ORDER BY total_return DESC LIMIT 1
    """)
    result = rows[0] if rows else {}
    result["best_symbol"]     = best[0]["symbol"] if best else "N/A"
    result["best_return"]     = float(best[0]["total_return"]) if best else 0
    result["date_start_year"] = int(result.get("date_start_year", 2021))
    result["date_end_year"]   = int(result.get("date_end_year",   2026))
    result["year_span"]       = result["date_end_year"] - result["date_start_year"]
    return jsonify(result)


# ── API: Monthly Price Trend ───────────────────────────────────
@app.route("/api/price-trend")
def price_trend():
    rows = query("""
        SELECT
            TO_CHAR(d.full_date, 'YYYY-MM') AS month,
            ROUND(AVG(f.close_price)::numeric, 2) AS avg_close
        FROM fact_stock_prices f
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.full_date >= NOW() - INTERVAL '3 years'
        GROUP BY TO_CHAR(d.full_date, 'YYYY-MM')
        ORDER BY month
    """)
    return jsonify({
        "labels": [r["month"] for r in rows],
        "data":   [float(r["avg_close"]) for r in rows],
    })


# ── API: Top 10 Stocks by 5yr Return ──────────────────────────
@app.route("/api/top-stocks")
def top_stocks():
    rows = query("""
        SELECT s.symbol,
               ROUND(((last_v.close - first_v.close) / NULLIF(first_v.close,0) * 100)::numeric, 2) AS total_return
        FROM (
            SELECT DISTINCT ON (stock_key) stock_key, close_price AS close
            FROM fact_stock_prices ORDER BY stock_key, date_key ASC
        ) first_v
        JOIN (
            SELECT DISTINCT ON (stock_key) stock_key, close_price AS close
            FROM fact_stock_prices ORDER BY stock_key, date_key DESC
        ) last_v ON first_v.stock_key = last_v.stock_key
        JOIN dim_stock s ON s.stock_key = first_v.stock_key AND s.is_current = TRUE
        ORDER BY total_return DESC LIMIT 10
    """)
    return jsonify({
        "labels": [r["symbol"] for r in rows],
        "data":   [float(r["total_return"]) for r in rows],
    })


# ── API: Sector Average Daily Return ──────────────────────────
@app.route("/api/sector-return")
def sector_return():
    rows = query("""
        SELECT sec.sector_name,
               ROUND(AVG(f.daily_return_pct)::numeric, 4) AS avg_return
        FROM fact_stock_prices f
        JOIN dim_sector sec ON f.sector_key = sec.sector_key
        GROUP BY sec.sector_name
        ORDER BY avg_return DESC
    """)
    return jsonify({
        "labels": [r["sector_name"] for r in rows],
        "data":   [float(r["avg_return"]) for r in rows],
    })


# ── API: Sector Volatility ─────────────────────────────────────
@app.route("/api/sector-volatility")
def sector_volatility():
    rows = query("""
        SELECT sec.sector_name,
               ROUND(STDDEV(f.daily_return_pct)::numeric, 4) AS volatility
        FROM fact_stock_prices f
        JOIN dim_sector sec ON f.sector_key = sec.sector_key
        GROUP BY sec.sector_name
        ORDER BY volatility DESC
    """)
    return jsonify({
        "labels": [r["sector_name"] for r in rows],
        "data":   [float(r["volatility"]) for r in rows],
    })


# ── API: Top 10 Stocks by Volume ──────────────────────────────
@app.route("/api/volume")
def volume():
    rows = query("""
        SELECT s.symbol,
               ROUND(SUM(f.volume) / 1000000000.0, 2) AS total_vol_billions
        FROM fact_stock_prices f
        JOIN dim_stock s ON f.stock_key = s.stock_key AND s.is_current = TRUE
        GROUP BY s.symbol
        ORDER BY total_vol_billions DESC LIMIT 10
    """)
    return jsonify({
        "labels": [r["symbol"] for r in rows],
        "data":   [float(r["total_vol_billions"]) for r in rows],
    })


# ── API: Risk vs Return Scatter ────────────────────────────────
@app.route("/api/risk-return")
def risk_return():
    rows = query("""
        SELECT sec.sector_name,
               ROUND(AVG(f.daily_return_pct)::numeric, 4) AS avg_return,
               ROUND(STDDEV(f.daily_return_pct)::numeric, 4) AS volatility
        FROM fact_stock_prices f
        JOIN dim_sector sec ON f.sector_key = sec.sector_key
        GROUP BY sec.sector_name
        ORDER BY volatility DESC
    """)
    return jsonify([{
        "sector":     r["sector_name"],
        "return":     float(r["avg_return"]),
        "volatility": float(r["volatility"]),
    } for r in rows])


# ── API: Price Trend (Filtered) ────────────────────────────────
# Supports ?start=YYYY&end=YYYY&sector=name for interactive filtering
@app.route("/api/price-trend-filtered")
def price_trend_filtered():
    start_year = request.args.get("start", "2021")
    end_year   = request.args.get("end",   "2026")
    sector     = request.args.get("sector", "")
    try:
        start_year = int(start_year)
        end_year   = int(end_year)
    except ValueError:
        start_year, end_year = 2021, 2026

    if sector and sector != "":
        rows = query("""
            SELECT TO_CHAR(d.full_date, 'YYYY-MM') AS month,
                   ROUND(AVG(f.close_price)::numeric, 2) AS avg_close
            FROM fact_stock_prices f
            JOIN dim_date   d   ON f.date_key   = d.date_key
            JOIN dim_sector sec ON f.sector_key = sec.sector_key
            WHERE d.year BETWEEN %s AND %s
              AND sec.sector_name = %s
            GROUP BY TO_CHAR(d.full_date, 'YYYY-MM')
            ORDER BY month
        """, (start_year, end_year, sector))
    else:
        rows = query("""
            SELECT TO_CHAR(d.full_date, 'YYYY-MM') AS month,
                   ROUND(AVG(f.close_price)::numeric, 2) AS avg_close
            FROM fact_stock_prices f
            JOIN dim_date d ON f.date_key = d.date_key
            WHERE d.year BETWEEN %s AND %s
            GROUP BY TO_CHAR(d.full_date, 'YYYY-MM')
            ORDER BY month
        """, (start_year, end_year))
    return jsonify({
        "labels": [r["month"] for r in rows],
        "data":   [float(r["avg_close"]) for r in rows],
    })


# ── API: Geographic — Exchange Breakdown ────────────────────
# Uses dim_exchange as the geographic dimension (actually populated)
@app.route("/api/exchange-breakdown")
def exchange_breakdown():
    rows = query("""
        SELECT e.exchange_code,
               e.exchange_name,
               e.country,
               COUNT(*)                                        AS total_rows,
               COUNT(DISTINCT f.stock_key)                     AS stock_count,
               ROUND(AVG(f.daily_return_pct)::numeric, 4)     AS avg_return,
               ROUND(STDDEV(f.daily_return_pct)::numeric, 4)  AS volatility,
               ROUND(SUM(f.volume) / 1000000000.0, 2)         AS total_vol_b
        FROM fact_stock_prices f
        JOIN dim_exchange e ON f.exchange_key = e.exchange_key
        GROUP BY e.exchange_code, e.exchange_name, e.country
        ORDER BY avg_return DESC
    """)
    return jsonify([{
        "exchange_code": r["exchange_code"],
        "exchange_name": r["exchange_name"],
        "country":       r["country"],
        "total_rows":    int(r["total_rows"]),
        "stock_count":   int(r["stock_count"]),
        "avg_return":    float(r["avg_return"]),
        "volatility":    float(r["volatility"]),
        "volume_b":      float(r["total_vol_b"]),
    } for r in rows])


# ── API: Market Cap Tier Breakdown ────────────────────────────
@app.route("/api/cap-tier-breakdown")
def cap_tier_breakdown():
    rows = query("""
        SELECT t.tier_name,
               COUNT(*)                                        AS total_rows,
               COUNT(DISTINCT f.stock_key)                     AS stock_count,
               ROUND(AVG(f.daily_return_pct)::numeric, 4)     AS avg_return,
               ROUND(STDDEV(f.daily_return_pct)::numeric, 4)  AS volatility,
               ROUND(SUM(f.volume) / 1000000000.0, 2)         AS total_vol_b
        FROM fact_stock_prices f
        JOIN dim_market_cap_tier t ON f.cap_tier_key = t.cap_tier_key
        GROUP BY t.tier_name
        ORDER BY avg_return DESC
    """)
    return jsonify([{
        "tier_name":   r["tier_name"],
        "total_rows":  int(r["total_rows"]),
        "stock_count": int(r["stock_count"]),
        "avg_return":  float(r["avg_return"]),
        "volatility":  float(r["volatility"]),
        "volume_b":    float(r["total_vol_b"]),
    } for r in rows])


# ── API: Sector List (for drill-down filter dropdown) ──────────
@app.route("/api/sector-list")
def sector_list():
    rows = query("SELECT sector_name FROM dim_sector ORDER BY sector_name")
    return jsonify([r["sector_name"] for r in rows])



# ── API: Quality Checks Summary ────────────────────────────────
@app.route("/api/quality")
def quality():
    checks = query("""
        SELECT
            COUNT(*)                         AS total_rows,
            SUM(CASE WHEN open_price <= 0 OR close_price <= 0 THEN 1 ELSE 0 END) AS bad_prices,
            SUM(CASE WHEN high_price < low_price THEN 1 ELSE 0 END)              AS bad_hl,
            SUM(CASE WHEN close_price IS NULL OR open_price IS NULL THEN 1 ELSE 0 END) AS nulls,
            SUM(CASE WHEN daily_return_pct IS NULL THEN 1 ELSE 0 END)            AS null_returns
        FROM fact_stock_prices
    """)
    return jsonify(checks[0] if checks else {})


# ── API: Storage Monitor ───────────────────────────────────────
@app.route("/api/storage")
def storage():
    # DB size
    size = query("""
        SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size,
               ROUND(pg_database_size(current_database()) / 1048576.0, 1) AS size_mb
    """)

    # ETL run log
    runs = query("""
        SELECT COUNT(*)                                      AS total_runs,
               COUNT(*) FILTER (WHERE cleanup_ran = TRUE)   AS cleanup_runs,
               MAX(run_at)                                   AS last_run
        FROM etl_run_log
    """)

    total_runs = int(runs[0]["total_runs"]) if runs else 0
    runs_until_cleanup = 4 - (total_runs % 4) if total_runs % 4 != 0 else 0

    dead = query("""
        SELECT SUM(n_dead_tup) AS dead_rows
        FROM pg_stat_user_tables
        WHERE relname = 'fact_stock_prices'
    """)

    return jsonify({
        "db_size":            size[0]["db_size"] if size else "N/A",
        "size_mb":            float(size[0]["size_mb"]) if size else 0,
        "total_runs":         total_runs,
        "cleanup_runs":       int(runs[0]["cleanup_runs"]) if runs else 0,
        "last_run":           str(runs[0]["last_run"]) if runs and runs[0]["last_run"] else "Never",
        "runs_until_cleanup": runs_until_cleanup,
        "dead_rows":          int(dead[0]["dead_rows"] or 0) if dead else 0,
    })


# ── API: Executive Insights (filter-aware) ─────────────────────
@app.route("/api/insights")
def insights():
    from flask import request
    start  = request.args.get("start", "")
    end    = request.args.get("end", "")
    sector = request.args.get("sector", "")

    # Build optional WHERE clauses (filters use year values, e.g. 2022)
    date_filter   = ""
    sector_filter = ""
    if start and end:
        date_filter = f"AND d.year BETWEEN {int(start)} AND {int(end)}"
    if sector:
        safe_sector = sector.replace("'", "''")  # basic SQL escape
        sector_filter = f"AND sec.sector_name = '{safe_sector}'"

    # Top 3 stocks by total return within filtered period
    top_stocks = query(f"""
        SELECT s.symbol, s.company_name, sec.sector_name AS sector,
               ROUND(((last_v.close - first_v.close) / NULLIF(first_v.close, 0) * 100)::numeric, 2) AS total_return
        FROM (
            SELECT DISTINCT ON (stock_key) stock_key, close_price AS close
            FROM fact_stock_prices ORDER BY stock_key, date_key ASC
        ) first_v
        JOIN (
            SELECT DISTINCT ON (stock_key) stock_key, close_price AS close
            FROM fact_stock_prices ORDER BY stock_key, date_key DESC
        ) last_v ON first_v.stock_key = last_v.stock_key
        JOIN dim_stock  s   ON s.stock_key   = first_v.stock_key AND s.is_current = TRUE
        JOIN dim_sector sec ON sec.sector_key = s.sector_key
        WHERE 1=1 {sector_filter}
        ORDER BY total_return DESC LIMIT 3
    """)

    # Sectors ranked by avg daily return (filtered by date + sector)
    sector_perf = query(f"""
        SELECT sec.sector_name AS sector,
               ROUND(AVG(f.daily_return_pct)::numeric, 4) AS avg_return
        FROM fact_stock_prices f
        JOIN dim_date   d   ON d.date_key    = f.date_key
        JOIN dim_stock  s   ON f.stock_key   = s.stock_key AND s.is_current = TRUE
        JOIN dim_sector sec ON sec.sector_key = s.sector_key
        WHERE 1=1 {date_filter} {sector_filter}
        GROUP BY sec.sector_name
        ORDER BY avg_return DESC
    """)

    # Top 3 market cap tiers by Sharpe proxy (filtered)
    tier_perf = query(f"""
        SELECT t.tier_name,
               ROUND((AVG(f.daily_return_pct) / NULLIF(STDDEV(f.daily_return_pct), 0))::numeric, 4) AS sharpe_proxy
        FROM fact_stock_prices f
        JOIN dim_date            d ON d.date_key     = f.date_key
        JOIN dim_stock           s ON f.stock_key    = s.stock_key AND s.is_current = TRUE
        JOIN dim_market_cap_tier t ON t.cap_tier_key = s.cap_tier_key
        JOIN dim_sector        sec ON sec.sector_key = s.sector_key
        WHERE 1=1 {date_filter} {sector_filter}
        GROUP BY t.tier_name
        ORDER BY sharpe_proxy DESC
        LIMIT 3
    """)

    # Year trend (filtered by date + sector)
    year_trend = query(f"""
        SELECT d.year, sec.sector_name AS sector,
               ROUND(AVG(f.daily_return_pct)::numeric, 4) AS avg_return
        FROM fact_stock_prices f
        JOIN dim_date   d   ON d.date_key    = f.date_key
        JOIN dim_stock  s   ON f.stock_key   = s.stock_key AND s.is_current = TRUE
        JOIN dim_sector sec ON sec.sector_key = s.sector_key
        WHERE 1=1 {date_filter} {sector_filter}
        GROUP BY d.year, sec.sector_name
        ORDER BY d.year
    """)

    return jsonify({
        "top_stocks":  top_stocks,
        "sector_perf": sector_perf,
        "tier_perf":   tier_perf,
        "year_trend":  year_trend
    })

if __name__ == "__main__":
    print("=" * 55)
    print("  Stock Market Dashboard — Live API Server")
    print("  URL: http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)
