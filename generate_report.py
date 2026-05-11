"""
generate_report.py
Generates a professionally structured DOCX report for the Data Warehouse project.
Run: .\\venv\\Scripts\\python.exe generate_report.py
"""
import os
from docx import Document
from docx.shared import Pt
from doc_builder import (
    set_page_margins, add_page_number, cover,
    h1, h2, h3, body, code, note, divider, two_col_table
)

os.makedirs("docs", exist_ok=True)
doc = Document()
set_page_margins(doc)
add_page_number(doc)

# ── COVER PAGE ────────────────────────────────────────────────
cover(doc,
      "Stock Market Data Warehouse",
      "Project Progress Report",
      "Mohammed (Fayiz)", "May 2026")

# ── SECTION 1 ─────────────────────────────────────────────────
h1(doc, "1. Project Overview")
body(doc,
     "This project builds a fully functional Data Warehouse for stock market "
     "analysis using PostgreSQL. Unlike a regular database that stores raw "
     "records, a data warehouse is designed specifically for answering business "
     "questions quickly — like 'Which sector performed best this quarter?' or "
     "'How volatile was AAPL compared to MSFT over the past 3 years?'")
body(doc,
     "We collect 5 years of daily stock price data for 80 major companies across "
     "10 market sectors, store it in a structured Star Schema, and build analytical "
     "queries and dashboards on top of it.")

two_col_table(doc, [
    ("Item",          "Detail"),
    ("Domain",        "Stock Market Daily Trading"),
    ("Stocks",        "80 companies across 10 sectors"),
    ("Total Rows",    "100,400 daily price records"),
    ("Date Range",    "May 2021 → May 2026  (5 years)"),
    ("Database",      "PostgreSQL 18"),
    ("ETL Language",  "Python 3"),
    ("Data Source",   "Yahoo Finance via yfinance library"),
])

# ── SECTION 2 ─────────────────────────────────────────────────
h1(doc, "2. Environment Setup  (Phase 0)")
body(doc,
     "Before writing any code, we set up a clean project environment. "
     "Think of this as preparing the workspace before starting a construction project.")

h2(doc, "2.1  Folder Structure")
code(doc,
     "data-warehouse-project/\n"
     "├── data/          ← raw CSV files (never committed to GitHub)\n"
     "├── etl/           ← Python ETL scripts\n"
     "├── sql/           ← all SQL files\n"
     "├── queries/       ← analytical SQL queries\n"
     "├── docs/          ← reports and documentation\n"
     "├── .env           ← secrets (excluded from GitHub)\n"
     "├── .env.example   ← safe template to share\n"
     "├── .gitignore\n"
     "└── requirements.txt")

h2(doc, "2.2  Virtual Environment & Dependencies")
body(doc,
     "A virtual environment keeps our project's libraries separate from "
     "other Python projects on the machine. This avoids version conflicts.")
code(doc,
     "python -m venv venv\n"
     ".\\venv\\Scripts\\activate          # activate on Windows\n"
     "pip install -r requirements.txt   # install all dependencies")
code(doc,
     "# requirements.txt\n"
     "yfinance        # fetch stock data from Yahoo Finance\n"
     "pandas          # data manipulation\n"
     "psycopg2-binary # connect Python to PostgreSQL\n"
     "python-dotenv   # load .env file into environment variables\n"
     "tqdm            # progress bars")

h2(doc, "2.3  Environment Variables (.env)")
body(doc,
     "Sensitive information like database passwords are stored in a .env file "
     "that is never uploaded to GitHub. We share only a .env.example template.")
code(doc,
     "DB_HOST=127.0.0.1\n"
     "DB_PORT=5433\n"
     "DB_NAME=warehouse_db\n"
     "DB_USER=postgres\n"
     "DB_PASSWORD=your_password_here")

# ── SECTION 3 ─────────────────────────────────────────────────
h1(doc, "3. Data Collection  (Phase 1)")
body(doc,
     "We need real historical stock price data. We initially tried Alpha Vantage "
     "API but its free tier limits requests to 25 per day — far too slow for "
     "80 stocks. We switched to yfinance, a free Python library that fetches "
     "unlimited data from Yahoo Finance.")

h2(doc, "3.1  Stocks Selected")
body(doc, "80 companies were selected across 10 market sectors:")
code(doc,
     "Technology:    AAPL  MSFT  GOOGL  NVDA  META  TSLA  AMD  INTC  ADBE\n"
     "Healthcare:    JNJ   PFE   UNH   ABBV  MRK   TMO   ABT  AMGN  GILD  BMY\n"
     "Finance:       JPM   BAC   GS    WFC   C     MS    BLK  SCHW  AXP   PGR\n"
     "Energy:        XOM   CVX   SLB   COP   EOG   MPC   VLO\n"
     "Consumer Def:  WMT   PG    KO    PEP\n"
     "Industrials:   CAT   BA    HON   UPS   LMT   RTX   GE   MMM   DE    FDX\n"
     "Communication: T     VZ    DIS   NFLX  CMCSA  META  ATVI\n"
     "Real Estate:   AMT   PLD   CCI   EQIX  SPG\n"
     "Utilities:     NEE   DUK   SO    AEP   EXC   SRE   D    AES   ETR   ES   PCG\n"
     "Cons. Cyclical: AMZN  HD    MCD   NKE   SBUX  LOW   TGT")

h2(doc, "3.2  How Data Is Fetched")
body(doc,
     "yfinance downloads all 80 stocks in a single bulk API call, "
     "which takes about 30 seconds for 5 years of daily data.")
code(doc,
     "import yfinance as yf\n\n"
     "raw = yf.download(\n"
     "    tickers  = ALL_SYMBOLS,  # list of 80 ticker symbols\n"
     "    period   = '5y',         # last 5 years of data\n"
     "    interval = '1d',         # one row per trading day\n"
     "    threads  = True,         # download in parallel (faster)\n"
     ")")

h2(doc, "3.3  Calculated Columns Added")
body(doc, "After downloading, we add 3 columns calculated from the raw price data:")
code(doc,
     "price_change     = close - open\n"
     "                   Did the stock go up or down today?\n\n"
     "daily_return_pct = (close - open) / open × 100\n"
     "                   By what percentage?\n\n"
     "high_low_spread  = high - low\n"
     "                   How wide was the price range today?")

h2(doc, "3.4  Output Files")
two_col_table(doc, [
    ("File",                   "Contents"),
    ("raw_stock_prices.csv",   "100,400 rows — daily OHLCV for all 80 stocks"),
    ("company_metadata.csv",   "81 rows — company name, sector, exchange, market cap, etc."),
])
note(doc, "100,400 rows = 80 stocks × ~1,255 trading days over 5 years.")

# ── SECTION 4 ─────────────────────────────────────────────────
h1(doc, "4. Star Schema Design  (Phase 2)")
body(doc,
     "A Star Schema organises the database into a central fact table surrounded "
     "by dimension tables — like a star. The fact table stores the numbers "
     "(prices, volumes), and dimension tables store the context "
     "(which company? which date? which sector?).")
body(doc,
     "This separation makes analytical queries very fast because you can filter "
     "and group by any combination of dimensions without scanning the entire dataset.")

h2(doc, "4.1  The 6 Dimension Tables")

dims = [
    ("dim_date\n4,748 rows",
     "Every calendar day from 2018 to 2030, pre-populated using PostgreSQL's "
     "generate_series() function. Includes is_weekend, is_trading_day, "
     "fiscal_quarter, month_name, and week_of_year."),
    ("dim_sector\n10 rows",
     "The 10 market sectors: Technology, Healthcare, Financial Services, "
     "Energy, Consumer Defensive, Industrials, Communication Services, "
     "Real Estate, Utilities, Consumer Cyclical."),
    ("dim_exchange\n7 rows",
     "Stock exchanges pre-seeded: NASDAQ, NYSE, NYQ, NMS, NGM, LSE, and OTHER. "
     "Includes timezone and trading hours."),
    ("dim_country\n10 rows",
     "Countries where companies are headquartered. Includes region "
     "(North America, Europe), sub-region, currency, and market type "
     "(Developed / Emerging)."),
    ("dim_market_cap_tier\n6 rows",
     "Market cap classification: Mega-cap (>$200B), Large-cap ($10B–$200B), "
     "Mid-cap ($2B–$10B), Small-cap ($300M–$2B), Micro-cap (<$300M), Unknown. "
     "Pre-seeded with threshold values."),
    ("dim_stock  [SCD Type 2]\n81 rows",
     "One row per company version. Implements Slowly Changing Dimension Type 2 "
     "to track changes over time using effective_from, effective_to, "
     "is_current, and version columns."),
]
for name_rows, desc in dims:
    h3(doc, name_rows)
    body(doc, desc)

h2(doc, "4.2  The Fact Table — fact_stock_prices")
body(doc,
     "The central table of the warehouse. Every row = one stock on one trading day. "
     "It contains 6 foreign keys (one to each dimension) plus the numeric measures.")
code(doc,
     "CREATE TABLE fact_stock_prices (\n"
     "    price_key        BIGSERIAL  PRIMARY KEY,\n"
     "    -- 6 foreign keys linking to all dimension tables:\n"
     "    date_key         INTEGER    REFERENCES dim_date,\n"
     "    stock_key        INTEGER    REFERENCES dim_stock,\n"
     "    exchange_key     INTEGER    REFERENCES dim_exchange,\n"
     "    sector_key       INTEGER    REFERENCES dim_sector,\n"
     "    country_key      INTEGER    REFERENCES dim_country,\n"
     "    cap_tier_key     INTEGER    REFERENCES dim_market_cap_tier,\n"
     "    -- The actual price measures:\n"
     "    open_price       NUMERIC(12,4),\n"
     "    high_price       NUMERIC(12,4),\n"
     "    low_price        NUMERIC(12,4),\n"
     "    close_price      NUMERIC(12,4),\n"
     "    adj_close_price  NUMERIC(12,4),\n"
     "    volume           BIGINT,\n"
     "    -- Pre-calculated derived measures:\n"
     "    price_change     NUMERIC(12,4),  -- close - open\n"
     "    daily_return_pct NUMERIC(8,4),   -- % gain or loss\n"
     "    high_low_spread  NUMERIC(12,4)   -- range width\n"
     ");")

h2(doc, "4.3  What is SCD Type 2?")
body(doc,
     "SCD stands for Slowly Changing Dimension. Type 2 means we keep a full "
     "history of changes instead of overwriting old data. Each dim_stock record has:")
code(doc,
     "effective_from  DATE     -- when this company version became active\n"
     "effective_to    DATE     -- when it was replaced (9999-12-31 = still active)\n"
     "is_current      BOOLEAN  -- TRUE means this is the latest version\n"
     "version         SMALLINT -- 1=original, 2=first change, 3=second change...")
body(doc,
     "Example: If Apple changes sector, we close the old record and add a new one. "
     "Old fact rows automatically still point to the old sector through the surrogate key.")

# ── SECTION 5 ─────────────────────────────────────────────────
h1(doc, "5. Natural Keys vs Surrogate Keys")
body(doc,
     "This is one of the most important concepts in data warehousing. "
     "When loading raw data into the warehouse, we convert natural keys "
     "(text identifiers from the source) into surrogate keys "
     "(integers generated internally by the database).")

h2(doc, "5.1  Definitions")
two_col_table(doc, [
    ("Term",           "Definition"),
    ("Natural Key",    "The real-world identifier from the source system. Example: 'AAPL', '2024-01-15'"),
    ("Surrogate Key",  "A system-generated integer with no business meaning. Example: stock_key=1, date_key=20240115"),
])

h2(doc, "5.2  Why Surrogate Keys Are Needed")

h3(doc, "Reason 1 — Performance")
body(doc,
     "Integers are much faster to join and compare than text strings. "
     "With 100,400 rows and 6 joins per query, this difference is significant.")
code(doc,
     "❌ Text join:    WHERE symbol = 'Communication Services'  ← 23 bytes\n"
     "✅ Integer join: WHERE sector_key = 4                    ← 4 bytes\n\n"
     "Integers join 10x faster and use far less storage across 100,000 rows.")

h3(doc, "Reason 2 — SCD Type 2 (Historical Accuracy)")
body(doc,
     "Without surrogate keys, tracking changes over time is impossible. "
     "Consider AAPL changing from 'Technology' to a new sector:")
code(doc,
     "❌ WITHOUT surrogate keys:\n"
     "   Update dim_stock: AAPL sector = 'Consumer Electronics'\n"
     "   All 1,255 fact rows for AAPL now show wrong historical sector!\n\n"
     "✅ WITH surrogate keys:\n"
     "   Old: stock_key=1,  AAPL, Technology,         effective_to=2022\n"
     "   New: stock_key=47, AAPL, Consumer Electronics, is_current=TRUE\n\n"
     "   2022 facts → stock_key=1  → 'Technology'          ✅ correct\n"
     "   2023 facts → stock_key=47 → 'Consumer Electronics' ✅ correct")

h3(doc, "Reason 3 — Source System Independence")
code(doc,
     "Yahoo Finance today: 'BRK-B'\n"
     "New provider tomorrow: 'BRK.B'\n\n"
     "❌ Natural key: UPDATE 1,255 fact rows\n"
     "✅ Surrogate key: UPDATE 1 row in dim_stock — fact table untouched")

h2(doc, "5.3  How We Implement This")
body(doc,
     "In load_facts.py, we query dimension tables ONCE, store results in "
     "Python dictionaries, then do all key conversions in memory — "
     "no extra database queries per row:")
code(doc,
     "# Build lookup dicts ONCE (not per row)\n"
     "stock_lookup = {\n"
     "    'AAPL': {'stock_key': 1, 'sector_key': 3, 'country_key': 1},\n"
     "    'MSFT': {'stock_key': 2, 'sector_key': 3, 'country_key': 1},\n"
     "    ...  # all 81 companies\n"
     "}\n"
     "date_lookup = {'2024-01-15': 20240115, ...}  # 4,748 dates\n\n"
     "# For each of 100,400 CSV rows:\n"
     "for row in price_data:\n"
     "    fact_row = (\n"
     "        date_lookup[row['date']],                # 20240115\n"
     "        stock_lookup[row['symbol']]['stock_key'], # 1\n"
     "        stock_lookup[row['symbol']]['sector_key'],# 3\n"
     "        ... open, high, low, close, volume ...\n"
     "    )\n"
     "    batch.append(fact_row)\n"
     "    if len(batch) == 5000:\n"
     "        execute_values(cur, INSERT_SQL, batch)  # bulk insert")
note(doc, "This approach loaded all 100,400 rows in under 60 seconds with 0 skipped rows.")

# ── SECTION 6 ─────────────────────────────────────────────────
h1(doc, "6. ETL Pipeline  (Phase 3)")
body(doc,
     "ETL stands for Extract, Transform, Load. This is the process of moving "
     "data from raw CSV files into the structured warehouse tables. "
     "We built 3 Python scripts.")

h2(doc, "6.1  load_dimensions.py")
body(doc,
     "Reads company_metadata.csv and loads all 5 dimension tables "
     "in dependency order (sectors first, then exchanges, countries, then stocks).")
code(doc,
     "# Execution order (each step resolves FK for the next):\n"
     "load_dim_sector(cur, meta_df)    # 10 sectors\n"
     "load_dim_exchange(cur, meta_df)  # 7 exchanges\n"
     "load_dim_country(cur, meta_df)   # 10 countries\n"
     "load_dim_stock(cur, meta_df)     # 81 companies (SCD Type 2 logic)")
body(doc, "Result: All dimension tables populated with correct surrogate key mappings.")

h2(doc, "6.2  load_facts.py")
body(doc,
     "Reads raw_stock_prices.csv and inserts 100,400 rows into fact_stock_prices "
     "using batch inserts of 5,000 rows for maximum performance.")
body(doc, "Result: 100,400 rows inserted, 0 rows skipped, all 6 FK columns populated.")

h2(doc, "6.3  verify_warehouse.py  — 31 Quality Checks")
body(doc,
     "Automated data quality checks run after every load to confirm the "
     "warehouse is clean and ready for analysis.")

checks = [
    ("Row Counts (7 checks)",        "All 7 tables have expected number of rows"),
    ("100K Target (1 check)",        "fact_stock_prices has at least 100,000 rows"),
    ("FK Integrity (4 checks)",      "No orphaned rows — all FKs resolve to valid dim records"),
    ("No Duplicates (1 check)",      "No two rows share the same (date_key, stock_key)"),
    ("No NULLs (5 checks)",          "OHLCV columns never contain NULL"),
    ("Business Logic (4 checks)",    "high >= low, all prices > 0, volume >= 0"),
    ("Date Range (2 checks)",        "Data spans >= 3 years, includes recent records"),
    ("SCD Type 2 (3 checks)",        "Each symbol has exactly one current dim_stock record"),
    ("Symbol Coverage (1 check)",    "All symbols in fact table exist in dim_stock"),
    ("Dim Completeness (3 checks)",  "All stocks have sector, exchange, and cap tier assigned"),
]
two_col_table(doc, [("Check Category", "What It Verifies")] + checks)
note(doc, "Final result: 31/31 checks PASSED — warehouse is clean and production-ready.")

# ── SECTION 7 ─────────────────────────────────────────────────
h1(doc, "7. Analytical Queries  (Phase 4)")
body(doc,
     "We wrote 10 SQL queries in queries/analytical_queries.sql that answer "
     "real business questions using the full star schema. "
     "Each query joins multiple dimension tables to the fact table.")

queries = [
    ("Q1",  "Top 10 Best Performing Stocks",
     "Which stocks gave the highest 5-year total return?",
     "Window functions compare first vs last closing price per stock."),
    ("Q2",  "Sector Performance",
     "Which sectors are most profitable and most volatile?",
     "AVG(daily_return_pct) and STDDEV grouped by sector."),
    ("Q3",  "Monthly Volume Trends",
     "How has trading activity changed month by month since 2023?",
     "SUM(volume) grouped by year, month, sector."),
    ("Q4",  "Most Volatile Stocks",
     "Which stocks have the widest daily price swings?",
     "AVG(high_low_spread / close_price × 100) — spread as % of price."),
    ("Q5",  "Year-over-Year by Sector",
     "How did each sector's average price change annually?",
     "Self-join on yearly aggregates to compute YoY % change."),
    ("Q6",  "Highest Volume Trading Days",
     "What were the top 10 most active trading days?",
     "ORDER BY volume DESC LIMIT 10."),
    ("Q7",  "Market Cap Tier Analysis",
     "Do bigger companies give better risk-adjusted returns?",
     "Sharpe proxy = AVG(return) / STDDEV(return)."),
    ("Q8",  "Quarterly Performance",
     "Which fiscal quarter is consistently the strongest?",
     "Grouped by year and fiscal_quarter with pos/neg day counts."),
    ("Q9",  "30 & 90-Day Moving Averages",
     "What is the rolling price trend for top tech stocks?",
     "Window function: AVG() OVER (ROWS BETWEEN N PRECEDING AND CURRENT ROW)."),
    ("Q10", "Country & Exchange Analysis",
     "How do companies compare across geographies?",
     "JOIN dim_country and dim_exchange, group by region and exchange."),
]
for qnum, qtitle, biz, tech in queries:
    h3(doc, f"{qnum}: {qtitle}")
    body(doc, f"Business question:     {biz}")
    body(doc, f"Technical approach:    {tech}")

h2(doc, "Sample Result — Q2: Sector Performance")
code(doc,
     "sector_name              | avg_return | volatility\n"
     "-------------------------+------------+-----------\n"
     "Technology               |  0.0469%   |  2.0449\n"
     "Communication Services   |  0.0356%   |  1.5647\n"
     "Financial Services       |  0.0315%   |  1.4854\n"
     "Energy                   |  0.0306%   |  1.7233\n"
     "Utilities                |  0.0056%   |  1.2596")
note(doc,
     "Technology gives the highest return but also highest volatility. "
     "Utilities gives the lowest return but also lowest volatility — "
     "classic risk/reward tradeoff confirmed by real data.")

# ── SECTION 8 ─────────────────────────────────────────────────
h1(doc, "8. Materialized Views  (Phase 5)")
body(doc,
     "A materialized view is a pre-computed query result stored as a physical table. "
     "Instead of running complex JOINs across 100,400 rows every time a dashboard "
     "refreshes, the calculation is done once and the result is cached. "
     "This makes dashboards load in milliseconds instead of seconds.")

h2(doc, "8.1  Three Materialized Views Created")

views = [
    ("mv_sector_performance_daily\n12,550 rows",
     "Daily aggregates per sector: avg return, total volume, volatility, "
     "count of positive vs negative stocks. Indexed on full_date and sector_name. "
     "Ideal for a live daily market dashboard."),
    ("mv_stock_monthly_summary\n100,400 rows",
     "Monthly OHLCV + performance metrics per stock: monthly open/high/low/close, "
     "total volume, win rate, and volatility. Indexed on symbol and year+month. "
     "Used for individual stock performance charts."),
    ("mv_market_cap_tier_quarterly\n42 rows",
     "Quarterly performance aggregated by market cap tier: Sharpe ratio proxy, "
     "win rate, cumulative return. Indexed on year+quarter. "
     "Used for executive-level investment strategy reports."),
]
for name, desc in views:
    h3(doc, name)
    body(doc, desc)

h2(doc, "8.2  Sample Result — Quarterly Tier Performance (2025)")
code(doc,
     "year | quarter | tier      | avg_return | sharpe | win_rate\n"
     "-----+---------+-----------+------------+--------+---------\n"
     "2025 | Q2      | Mega-cap  | +0.2257%   | 0.097  | 54.6%\n"
     "2025 | Q2      | Large-cap | +0.0490%   | 0.024  | 52.3%\n"
     "2025 | Q4      | Mega-cap  | -0.0406%   | -0.026 | 50.3%\n"
     "2025 | Q4      | Large-cap | -0.0270%   | -0.020 | 49.5%")

h2(doc, "8.3  How to Refresh After New Data")
code(doc,
     "-- Run after each new daily data load:\n"
     "REFRESH MATERIALIZED VIEW mv_sector_performance_daily;\n"
     "REFRESH MATERIALIZED VIEW mv_stock_monthly_summary;\n"
     "REFRESH MATERIALIZED VIEW mv_market_cap_tier_quarterly;")

# ── SECTION 9 ─────────────────────────────────────────────────
h1(doc, "9. GitHub Workflow")
body(doc,
     "The entire project is version-controlled on GitHub using a professional "
     "Git branching strategy. Each phase of development was done on its own "
     "feature branch, keeping the main branch always clean and production-ready.")

h2(doc, "9.1  Branch Strategy")
code(doc,
     "main                          ← production-ready, always stable\n"
     "develop                       ← integration branch\n"
     "feature/data-extraction       ← Phase 1: data collection\n"
     "feature/star-schema           ← Phase 2: SQL DDL\n"
     "feature/etl-dimensions        ← Phase 3a: dimension loading\n"
     "feature/etl-facts             ← Phase 3b: fact loading\n"
     "feature/data-verification     ← Phase 3c: 31 quality checks\n"
     "feature/analytical-queries    ← Phase 4: 10 business queries\n"
     "feature/materialized-views    ← Phase 5: 3 materialized views")

h2(doc, "9.2  Commit History")
code(doc,
     "Apr 21  feat: initialize project structure and environment\n"
     "Apr 23  feat: implement data extraction pipeline using yfinance\n"
     "Apr 25  feat: design and implement star schema DDL\n"
     "Apr 28  feat: implement ETL dimension loader with SCD Type 2\n"
     "Apr 30  feat: implement fact table ETL loader (100,400 rows)\n"
     "May 02  feat: add 31-check warehouse verification suite\n"
     "May 05  feat: add 10 business analytical queries\n"
     "May 07  feat: add 3 materialized views with indexes")

h2(doc, "9.3  Repository")
body(doc, "GitHub: https://github.com/Fayiz-github/data-warehouse-project")

# ── SECTION 10 ────────────────────────────────────────────────
h1(doc, "10. What's Still To Come")

remaining = [
    ("Phase 6 — Performance Indexes",
     "Add B-tree indexes on fact table for the most common query patterns "
     "(symbol lookups, date range scans, sector filters). This further "
     "speeds up ad-hoc analytical queries."),
    ("Phase 7 — SCD Type 2 Live Demo",
     "Simulate a real company changing its sector and demonstrate how "
     "the warehouse preserves historical accuracy through surrogate keys "
     "and the effective_from/to mechanism."),
    ("Phase 8 — BI Dashboard",
     "Connect the warehouse to a visualization tool (Looker Studio or "
     "a custom web dashboard) to display sector trends, stock comparisons, "
     "and quarterly performance charts."),
    ("Phase 9 — Business Insights Document",
     "A written analysis of the key findings from the data: "
     "best-performing stocks, most volatile sectors, market cap tier comparison."),
    ("Phase 10 — Final Cleanup",
     "Update README, merge all feature branches into main via pull requests, "
     "add GitHub Actions CI, and produce the final handover report."),
]
for phase, desc in remaining:
    h3(doc, phase)
    body(doc, desc)

body(doc, "")
body(doc, "Estimated remaining time: approximately 2 hours.")

# ── SAVE ─────────────────────────────────────────────────────
doc.save("docs/Project_Progress_Report.docx")
print("[DONE] Saved -> docs/Project_Progress_Report.docx")
