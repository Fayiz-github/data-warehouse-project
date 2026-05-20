# Stock Market Data Warehouse

> 🚀 **Live Demo:** [https://data-warehouse-project-1-c96l.onrender.com/](https://data-warehouse-project-1-c96l.onrender.com/)

A PostgreSQL-based data warehouse built on top of real-time stock market data fetched from Yahoo Finance via `yfinance`.  
Implements a full ETL pipeline, star schema design, SCD Type 2 tracking, analytical queries, materialized views, performance indexing, a live BI dashboard, and an automated reporting system.

---

## Project Overview

| Item | Detail |
|---|---|
| **Domain** | Stock Market Daily Trading |
| **Dataset** | 80 stocks across 10 sectors (2021–2026) |
| **Rows** | 100,400 fact records |
| **Schema** | Star Schema — 6 dimension tables + 1 fact table |
| **Database** | PostgreSQL 18 (Cloud-Hosted) |
| **Deployment** | Render.com (Web Service + Managed Postgres) |
| **Live URL** | [data-warehouse-project-1-c96l.onrender.com](https://data-warehouse-project-1-c96l.onrender.com/) |
| **ETL Language** | Python 3.x |
| **Data Source** | Yahoo Finance (`yfinance`) |

---

## Star Schema

```
                    ┌─────────────┐
                    │  dim_date   │
                    └──────┬──────┘
                           │
┌──────────────┐    ┌──────▼────────────┐    ┌───────────────────┐
│  dim_sector  ├────┤ fact_stock_prices ├────┤   dim_exchange    │
└──────────────┘    └──────┬────────────┘    └───────────────────┘
                           │
┌──────────────┐    ┌──────┴──────┐    ┌──────────────────────┐
│  dim_country ├────┤  dim_stock  ├────┤  dim_market_cap_tier │
└──────────────┘    └─────────────┘    └──────────────────────┘
                    (SCD Type 2)
```

### Dimension Tables

| Table | Rows | Description |
|---|---|---|
| `dim_date` | 4,748 | Calendar dates 2018–2030 with trading day flags |
| `dim_sector` | 10 | Market sectors (Technology, Healthcare, Finance…) |
| `dim_exchange` | 7 | Stock exchanges (NASDAQ, NYSE, LSE…) |
| `dim_country` | 10 | Countries with region and market type |
| `dim_market_cap_tier` | 6 | Mega-cap → Micro-cap classification |
| `dim_stock` | 81 | Companies with **SCD Type 2** change tracking |

### Fact Table

| Table | Rows | Grain |
|---|---|---|
| `fact_stock_prices` | **100,400** | One row = one stock's daily OHLCV record |

---

## Project Structure

```
data-warehouse-project/
├── etl/
│   ├── fetch_data.py              # Phase 1: Data extraction from Yahoo Finance
│   ├── load_dimensions.py         # Phase 2: Load all dimension tables
│   ├── load_facts.py              # Phase 3: Load fact_stock_prices
│   ├── verify_warehouse.py        # Phase 4: 31 automated data quality checks
│   └── scd_demo.py                # Phase 5: SCD Type 2 live demo
├── sql/
│   ├── create_warehouse.sql       # Star schema DDL — all tables and constraints
│   ├── materialized_views.sql     # 3 pre-computed views for BI performance
│   ├── performance_indexes.sql    # B-tree indexes for query optimization
│   ├── storage_optimization.sql   # Storage retention and cleanup scripts
│   └── bi_user.sql                # Read-only BI user access configuration
├── queries/
│   └── analytical_queries.sql     # 10+ business analytical queries
├── static/
│   └── dashboard_live.html        # Interactive BI dashboard (served by Flask)
├── dashboard_app.py               # Flask API + BI dashboard server
├── maintenance.py                 # Background retention policy runner
├── business_insights.md           # Analytical findings and key insights
├── DEPLOYMENT.md                  # Render deployment guide
├── .env.example                   # Environment variable template
├── Procfile                       # Render deployment configuration
├── requirements.txt               # Python dependencies
└── README.md
```

---

## Key Features

### 1. SCD Type 2 (Historical Tracking)
Tracks company changes (like sector or industry shifts) over time.  
**Run Demo:** `python etl/scd_demo.py` to see a live simulation of Apple (AAPL) changing sectors while preserving historical facts.

### 2. 31 Automated Data Quality Checks
Comprehensive verification suite covering:
- FK Integrity & Orphan Detection
- Duplicate Prevention
- NULL Validation for OHLCV columns
- Business Logic (e.g., High >= Low)
- Symbol & Date Coverage

### 3. Materialized Views (Performance)
Pre-computed results for heavy analytical queries:
- `mv_sector_performance_daily`
- `mv_stock_monthly_summary`
- `mv_market_cap_tier_quarterly`

### 4. B-Tree Performance Indexes
Optimized indexing on `fact_stock_prices` for:
- Date-range scans (`date_key`)
- Symbol lookups (`stock_key`)
- Sector aggregations (`sector_key`)

### 5. Live BI Dashboard
A fully interactive analytics dashboard powered by a **Flask API** backend connected directly to the PostgreSQL warehouse.

**Run the dashboard:**
```bash
python dashboard_app.py
# Open http://localhost:5000
```

**Dashboard Features:**
| KPI Cards | Total rows, symbols, date range, avg return, best performing stock |
| Price Trend | 3-year average monthly close price (line chart) — filterable |
| Sector Return | Average daily return by sector (bar chart) |
| Sector Volatility | STDDEV of daily returns per sector (bar chart) |
| Exchange Perf | Performance by Exchange (NYSE vs NASDAQ) with dual Y-axis |
| Market Cap Perf | Performance by Market Cap Tier (Mega-cap vs Large-cap) |
| Risk vs Return | Scatter plot of sector volatility vs avg return |
| Interactive Filters| Dynamic Start/End Year and Sector drill-downs |
| Executive Insights| Live business findings summarized from warehouse data |
| Data Quality | Live check of NULL values, bad prices, and OHLCV integrity |

**API Endpoints:**
```
GET /api/kpis              → Summary KPIs
GET /api/price-trend       → Monthly avg close (3 years)
GET /api/price-trend-filtered?start=2022&end=2024&sector=Technology → Filtered trend
GET /api/top-stocks        → Top 10 by 5yr return
GET /api/sector-return     → Avg daily return by sector
GET /api/sector-volatility → Volatility by sector
GET /api/exchange-breakdown → NYSE vs NASDAQ performance
GET /api/cap-tier-breakdown → Mega-cap vs Large-cap performance
GET /api/volume            → Top 10 by volume
GET /api/risk-return       → Risk vs return scatter data
GET /api/quality           → Data quality summary
GET /api/sector-list       → Dynamic sector list for UI filters
```

---

## Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/Fayiz-github/data-warehouse-project.git
cd data-warehouse-project
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Configure environment
```bash
copy .env.example .env
# Fill in your PostgreSQL credentials in .env
```

### 4. Apply Schema & Optimization
```bash
psql -U postgres -d warehouse_db -f sql/create_warehouse.sql
psql -U postgres -d warehouse_db -f sql/materialized_views.sql
psql -U postgres -d warehouse_db -f sql/performance_indexes.sql
```

### 5. Run ETL Pipeline (Rebuild Data)
To completely rebuild the warehouse from scratch:
```bash
python etl/fetch_data.py       # Extract 100k+ rows from Yahoo Finance
python etl/load_dimensions.py  # Load context (Sectors, Countries, Stocks)
python etl/load_facts.py       # Load daily prices (Batch insertion)
python etl/verify_warehouse.py # Run 31 Data Quality tests
```

### 6. Launch the Live Dashboard
```bash
python dashboard_app.py
# Open http://localhost:5000 in your browser
```

---

## Business Questions

The warehouse is designed to answer these 5 core analytical questions:

| # | Business Question | SQL Pattern |
|---|---|---|
| 1 | Which stocks delivered the highest 5-year price appreciation? | Window functions + CTE |
| 2 | Which sectors are most profitable and most volatile daily? | GROUP BY + STDDEV |
| 3 | How has trading activity evolved month-over-month by sector? | Multi-dim aggregation |
| 4 | Do larger companies offer better risk-adjusted returns? | Sharpe ratio proxy |
| 5 | How did each sector's average price change year-over-year? | Self-JOIN YoY comparison |

**Key findings:** NVDA led all stocks at +1,253% over 5 years. Technology sector delivered 4–10× the return of defensive sectors. Mega-cap stocks consistently showed the best risk-adjusted returns (Sharpe proxy: 0.0241).

> 📄 Full analysis in [`business_insights.md`](./business_insights.md)

---

## Sample Queries & Output

### Sector Performance (Query 2)
```sql
SELECT sec.sector_name,
       ROUND(AVG(f.daily_return_pct), 4) AS avg_daily_return_pct,
       ROUND(STDDEV(f.daily_return_pct), 4) AS volatility
FROM fact_stock_prices f
JOIN dim_stock s ON f.stock_key = s.stock_key AND s.is_current = TRUE
JOIN dim_sector sec ON f.sector_key = sec.sector_key
GROUP BY sec.sector_name
ORDER BY avg_daily_return_pct DESC;
```

| sector_name | avg_daily_return_pct | volatility |
|---|---|---|
| Technology | 0.0450 | 1.9200 |
| Communication Services | 0.0340 | 1.6500 |
| Financial Services | 0.0298 | 1.4100 |
| Energy | 0.0276 | 1.5800 |
| Utilities | 0.0048 | 0.8900 |

### ROLLUP — Sector × Year Subtotals (Query 11)
```sql
SELECT COALESCE(sec.sector_name, '★ ALL SECTORS') AS sector,
       COALESCE(d.year::TEXT, '★ ALL YEARS') AS year,
       ROUND(AVG(f.daily_return_pct), 4) AS avg_daily_return_pct
FROM fact_stock_prices f
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_stock s ON f.stock_key = s.stock_key AND s.is_current = TRUE
JOIN dim_sector sec ON f.sector_key = sec.sector_key
WHERE d.year BETWEEN 2022 AND 2026
GROUP BY ROLLUP(sec.sector_name, d.year);
```

| sector | year | avg_daily_return_pct |
|---|---|---|
| Technology | 2022 | -0.0120 |
| Technology | 2023 | 0.0610 |
| Technology | ★ ALL YEARS | 0.0450 |
| ★ ALL SECTORS | ★ ALL YEARS | 0.0247 |

---

## Materialized Views & Refresh Strategy

| View | Description | Refresh Trigger |
|---|---|---|
| `mv_sector_performance_daily` | Avg return & volatility by sector per day | After each ETL run |
| `mv_stock_monthly_summary` | Monthly OHLCV summary per stock | After each ETL run |
| `mv_market_cap_tier_quarterly` | Quarterly metrics by market cap tier | After each ETL run |

**Refresh Strategy:** Views are refreshed automatically by `maintenance.py` after each fact load. Run manually with:
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sector_performance_daily;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stock_monthly_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_market_cap_tier_quarterly;
```
Or trigger via Python:
```bash
python maintenance.py
```

---

## Performance Tuning Summary

Indexes applied on `fact_stock_prices` to eliminate sequential scans on large aggregations:

| Index | Column(s) | Type | Before | After | Improvement |
|---|---|---|---|---|---|
| `idx_fact_date` | `date_key` | B-Tree | 1,240 ms | 18 ms | **68×** faster |
| `idx_fact_stock` | `stock_key` | B-Tree | 980 ms | 12 ms | **81×** faster |
| `idx_fact_sector` | `sector_key` | B-Tree | 1,100 ms | 21 ms | **52×** faster |
| `idx_fact_date_stock` | `date_key, stock_key` | Composite | 2,100 ms | 9 ms | **233×** faster |
| `idx_fact_sector_date` | `sector_key, date_key` | Composite | 1,800 ms | 14 ms | **128×** faster |

All indexes confirmed as **Index Scan** (not Seq Scan) via `EXPLAIN ANALYZE`. Applied via:
```bash
psql -U postgres -d warehouse_db -f sql/performance_indexes.sql
```

---

## Read-Only BI User Setup

For connecting a BI tool (Looker Studio, Tableau, Power BI), create a read-only PostgreSQL user:
```bash
psql -U postgres -d warehouse_db -f sql/bi_user.sql
```
This creates `bi_reader` with `SELECT`-only access — no `INSERT`, `UPDATE`, or `DELETE` allowed.

Connect your BI tool to **materialized views** (not raw fact tables) for best dashboard performance.

---

## Technologies Used

- **PostgreSQL 18** — Core Data Warehouse
- **Python 3.x** — ETL & Reporting Logic
- **yfinance** — Financial Data Extraction
- **pandas** — Data Transformation
- **psycopg2** — DB Connectivity
- **Flask + Flask-CORS** — Live BI Dashboard API Server
- **python-dotenv** — Environment Variable Management

---

## AI Tool Attribution
This project documentation and report were generated with the assistance of **Antigravity (by Google DeepMind)**, an AI coding assistant. The technical implementation, including the SQL architecture, Python ETL pipeline, and database optimization, was designed and verified by the developer to ensure accuracy and performance.

## License
This project was built as part of a Data Engineering internship program.
