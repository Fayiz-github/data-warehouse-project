# Stock Market Data Warehouse

A PostgreSQL-based data warehouse built on top of real-time stock market data fetched from Yahoo Finance via `yfinance`.  
Implements a full ETL pipeline, star schema design, SCD Type 2, analytical queries, materialized views, and performance indexing.

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
│   └── verify_warehouse.py        # Phase 3: 31 data quality checks
├── sql/
│   └── create_warehouse.sql       # Phase 2: Full DDL + seeded data
├── queries/
│   └── analytical_queries.sql     # Phase 4: 10 business queries
├── .env.example                   # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/data-warehouse-project.git
cd data-warehouse-project
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### 3. Configure environment
```bash
copy .env.example .env
# Fill in your PostgreSQL credentials in .env
```

### 4. Create PostgreSQL database
```bash
psql -U postgres -c "CREATE DATABASE warehouse_db;"
```

### 5. Apply schema
```bash
psql -U postgres -d warehouse_db -f sql/create_warehouse.sql
```

### 6. Run ETL pipeline
```bash
# Fetch data from Yahoo Finance
python etl/fetch_data.py

# Load dimensions (dim_sector, dim_exchange, dim_country, dim_stock)
python etl/load_dimensions.py

# Load facts (100,400 rows → fact_stock_prices)
python etl/load_facts.py

# Verify data quality (31 checks)
python etl/verify_warehouse.py
```

### 7. Run analytical queries
```bash
psql -U postgres -d warehouse_db -f queries/analytical_queries.sql
```

---

## Key Features

- **SCD Type 2** on `dim_stock` — tracks company sector/industry changes over time with `effective_from`, `effective_to`, `is_current`, `version`
- **31 automated data quality checks** — FK integrity, NULL validation, business logic, duplicate detection
- **10 business analytical queries** — sector performance, volatility, YoY trends, rolling averages, market cap analysis
- **6-dimensional star schema** — enables multi-dimensional slicing and dicing
- **100,400 fact rows** — 80 stocks × 5 years of daily trading data

---

## Data Quality Verification Results

| Category | Checks | Result |
|---|---|---|
| Row counts | 7 | ✅ All pass |
| 100K target | 1 | ✅ 100,400 rows |
| FK integrity | 4 | ✅ No orphans |
| Duplicate detection | 1 | ✅ No duplicates |
| NULL validation | 5 | ✅ No NULLs |
| Business logic | 4 | ✅ All pass |
| Date coverage | 2 | ✅ 2021-2026 |
| SCD Type 2 | 3 | ✅ Integrity valid |
| Symbol coverage | 1 | ✅ 80 symbols |
| Dimension completeness | 3 | ✅ All pass |
| **Total** | **31** | **✅ 31/31** |

---

## Technologies Used

- **PostgreSQL 18** — relational data warehouse
- **Python 3.x** — ETL scripting
- **yfinance** — real-time stock data extraction
- **pandas** — data transformation
- **psycopg2** — PostgreSQL adapter
- **python-dotenv** — environment variable management

---

## License

This project was built as part of a Data Engineering internship program.
