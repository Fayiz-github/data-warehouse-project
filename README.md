# Stock Market Data Warehouse

A PostgreSQL-based data warehouse built on top of real-time stock market data fetched from Yahoo Finance via `yfinance`.  
Implements a full ETL pipeline, star schema design, SCD Type 2 tracking, analytical queries, materialized views, performance indexing, and an automated reporting system.

---

## Project Overview

| Item | Detail |
|---|---|
| **Domain** | Stock Market Daily Trading |
| **Dataset** | 80 stocks across 10 sectors (2021–2026) |
| **Rows** | 100,400 fact records |
| **Schema** | Star Schema — 6 dimension tables + 1 fact table |
| **Database** | PostgreSQL 18 |
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
├── data/
│   ├── raw_stock_prices.csv       # 100,400 rows (yfinance)
│   └── company_metadata.csv       # 81 company profiles
├── etl/
│   ├── fetch_data.py              # Phase 1: Data extraction
│   ├── load_dimensions.py         # Phase 3: Load all 6 dim tables
│   ├── load_facts.py              # Phase 3: Load fact_stock_prices
│   ├── verify_warehouse.py        # Phase 3: 31 data quality checks
│   └── scd_demo.py                # Phase 7: SCD Type 2 Live Demo
├── sql/
│   ├── create_warehouse.sql       # Phase 2: Full DDL + seeded data
│   ├── analytical_queries.sql     # Phase 4: 10 business queries
│   ├── materialized_views.sql     # Phase 5: 3 cached views for BI
│   └── performance_indexes.sql    # Phase 6: B-tree indexes for tuning
├── docs/
│   └── Project_Progress_Report.docx # Generated project report
├── doc_builder.py                 # Core reporting engine
├── generate_report.py             # Phase 10: Automated report generator
├── .env.example                   # Environment variable template
├── .gitignore
├── requirements.txt
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

### 5. Automated Reporting
Generates a professionally formatted DOCX report summarizing the entire project lifecycle, architecture, and current progress.  
**Generate:** `python generate_report.py`

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

### 5. Run ETL Pipeline
```bash
python etl/fetch_data.py       # Extract
python etl/load_dimensions.py  # Load Dims
python etl/load_facts.py       # Load Facts
python etl/verify_warehouse.py # Verify (31 Checks)
```

---

## Technologies Used

- **PostgreSQL 18** — Core Data Warehouse
- **Python 3.x** — ETL & Reporting Logic
- **yfinance** — Financial Data Extraction
- **pandas** — Data Transformation
- **psycopg2** — DB Connectivity
- **python-docx** — Professional Report Generation

---

## License

This project was built as part of a Data Engineering internship program.
