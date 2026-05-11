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
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="docs")
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
    return send_from_directory("docs", "dashboard_live.html")


# ── API: KPIs ─────────────────────────────────────────────────
@app.route("/api/kpis")
def kpis():
    rows = query("""
        SELECT
            COUNT(*)                              AS total_rows,
            COUNT(DISTINCT s.symbol)              AS total_symbols,
            MIN(d.full_date)                      AS date_start,
            MAX(d.full_date)                      AS date_end,
            ROUND(AVG(f.daily_return_pct)::numeric, 4) AS avg_daily_return,
            ROUND(AVG(f.close_price)::numeric, 2)       AS avg_close_price
        FROM fact_stock_prices f
        JOIN dim_date  d ON f.date_key  = d.date_key
        JOIN dim_stock s ON f.stock_key = s.stock_key AND s.is_current = TRUE
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
    result["best_symbol"] = best[0]["symbol"] if best else "N/A"
    result["best_return"] = float(best[0]["total_return"]) if best else 0
    result["date_start"] = str(result.get("date_start", ""))
    result["date_end"]   = str(result.get("date_end",   ""))
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


if __name__ == "__main__":
    print("=" * 55)
    print("  Stock Market Dashboard — Live API Server")
    print("  URL: http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)
