-- =============================================================
-- create_warehouse.sql
-- Stock Market Data Warehouse — Star Schema DDL
-- Domain  : Stock Market Daily Trading
-- Grain   : One row = one stock's OHLCV record for one trading day
-- Dimensions: 6 (dim_date, dim_sector, dim_exchange, dim_stock,
--                dim_country, dim_market_cap_tier)
-- =============================================================

-- Drop existing tables in reverse dependency order (safe re-run)
DROP TABLE IF EXISTS fact_stock_prices   CASCADE;
DROP TABLE IF EXISTS dim_stock           CASCADE;
DROP TABLE IF EXISTS dim_exchange        CASCADE;
DROP TABLE IF EXISTS dim_sector          CASCADE;
DROP TABLE IF EXISTS dim_date            CASCADE;
DROP TABLE IF EXISTS dim_country         CASCADE;
DROP TABLE IF EXISTS dim_market_cap_tier CASCADE;

-- =============================================================
-- 1. DIM_DATE
-- Pre-populated with one row per calendar day (2018-01-01 to 2030-12-31)
-- =============================================================
CREATE TABLE dim_date (
    date_key        INTEGER         PRIMARY KEY,        -- YYYYMMDD format
    full_date       DATE            NOT NULL UNIQUE,
    day             SMALLINT        NOT NULL,
    month           SMALLINT        NOT NULL,
    month_name      VARCHAR(20)     NOT NULL,
    quarter         SMALLINT        NOT NULL,
    year            SMALLINT        NOT NULL,
    day_of_week     SMALLINT        NOT NULL,           -- 0=Sun, 6=Sat
    day_name        VARCHAR(20)     NOT NULL,
    is_weekend      BOOLEAN         NOT NULL,
    is_trading_day  BOOLEAN         NOT NULL DEFAULT TRUE,
    is_holiday      BOOLEAN         NOT NULL DEFAULT FALSE,
    fiscal_quarter  VARCHAR(10),
    week_of_year    SMALLINT        NOT NULL
);

-- Populate dim_date for 2018-01-01 to 2030-12-31
INSERT INTO dim_date (
    date_key, full_date, day, month, month_name,
    quarter, year, day_of_week, day_name,
    is_weekend, is_trading_day, is_holiday,
    fiscal_quarter, week_of_year
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER         AS date_key,
    d::DATE                                  AS full_date,
    EXTRACT(DAY     FROM d)::SMALLINT        AS day,
    EXTRACT(MONTH   FROM d)::SMALLINT        AS month,
    TO_CHAR(d, 'Month')                      AS month_name,
    EXTRACT(QUARTER FROM d)::SMALLINT        AS quarter,
    EXTRACT(YEAR    FROM d)::SMALLINT        AS year,
    EXTRACT(DOW     FROM d)::SMALLINT        AS day_of_week,
    TO_CHAR(d, 'Day')                        AS day_name,
    EXTRACT(DOW FROM d) IN (0, 6)            AS is_weekend,
    EXTRACT(DOW FROM d) NOT IN (0, 6)        AS is_trading_day,
    FALSE                                    AS is_holiday,
    'Q' || EXTRACT(QUARTER FROM d)           AS fiscal_quarter,
    EXTRACT(WEEK FROM d)::SMALLINT           AS week_of_year
FROM generate_series(
    '2018-01-01'::DATE,
    '2030-12-31'::DATE,
    '1 day'::INTERVAL
) d;

-- =============================================================
-- 2. DIM_SECTOR
-- Denormalized sector/industry lookup
-- =============================================================
CREATE TABLE dim_sector (
    sector_key      SERIAL          PRIMARY KEY,
    sector_name     VARCHAR(100)    NOT NULL,
    industry_group  VARCHAR(150),
    description     TEXT,
    created_at      TIMESTAMP       DEFAULT NOW()
);

-- =============================================================
-- 3. DIM_EXCHANGE
-- Stock exchange details
-- =============================================================
CREATE TABLE dim_exchange (
    exchange_key    SERIAL          PRIMARY KEY,
    exchange_code   VARCHAR(20)     NOT NULL UNIQUE,    -- NYSE, NASDAQ
    exchange_name   VARCHAR(150)    NOT NULL,
    country         VARCHAR(50)     DEFAULT 'USA',
    timezone        VARCHAR(50)     DEFAULT 'America/New_York',
    currency        VARCHAR(10)     DEFAULT 'USD',
    trading_hours   VARCHAR(50)     DEFAULT '09:30-16:00 ET',
    created_at      TIMESTAMP       DEFAULT NOW()
);

-- =============================================================
-- 4. DIM_COUNTRY
-- Country where the company is headquartered
-- =============================================================
CREATE TABLE dim_country (
    country_key     SERIAL          PRIMARY KEY,
    country_code    VARCHAR(10)     NOT NULL UNIQUE,    -- USA, GBR, CHN
    country_name    VARCHAR(100)    NOT NULL,
    region          VARCHAR(50),                        -- North America, Europe, Asia
    sub_region      VARCHAR(50),                        -- Western Europe, East Asia
    currency        VARCHAR(10)     DEFAULT 'USD',
    market_type     VARCHAR(30)     DEFAULT 'Developed', -- Developed / Emerging / Frontier
    created_at      TIMESTAMP       DEFAULT NOW()
);

-- Seed known countries
INSERT INTO dim_country (country_code, country_name, region, sub_region, currency, market_type)
VALUES
    ('USA', 'United States',     'North America', 'Northern America', 'USD', 'Developed'),
    ('GBR', 'United Kingdom',    'Europe',         'Northern Europe',  'GBP', 'Developed'),
    ('CHN', 'China',             'Asia',           'East Asia',        'CNY', 'Emerging'),
    ('JPN', 'Japan',             'Asia',           'East Asia',        'JPY', 'Developed'),
    ('DEU', 'Germany',           'Europe',         'Western Europe',   'EUR', 'Developed'),
    ('FRA', 'France',            'Europe',         'Western Europe',   'EUR', 'Developed'),
    ('CAN', 'Canada',            'North America',  'Northern America', 'CAD', 'Developed'),
    ('AUS', 'Australia',         'Oceania',        'Australia',        'AUD', 'Developed'),
    ('IND', 'India',             'Asia',           'South Asia',       'INR', 'Emerging'),
    ('OTHER', 'Other / Unknown', 'Unknown',        'Unknown',          'USD', 'Unknown')
ON CONFLICT (country_code) DO NOTHING;

-- =============================================================
-- 5. DIM_MARKET_CAP_TIER
-- Pre-seeded market capitalisation classification
-- =============================================================
CREATE TABLE dim_market_cap_tier (
    cap_tier_key    SERIAL          PRIMARY KEY,
    tier_name       VARCHAR(30)     NOT NULL UNIQUE,    -- Mega-cap, Large-cap ...
    min_market_cap  BIGINT,                             -- inclusive lower bound (USD)
    max_market_cap  BIGINT,                             -- exclusive upper bound (NULL = no limit)
    description     TEXT,
    typical_examples VARCHAR(200),
    created_at      TIMESTAMP       DEFAULT NOW()
);

-- Seed market cap tiers
INSERT INTO dim_market_cap_tier (tier_name, min_market_cap, max_market_cap, description, typical_examples)
VALUES
    ('Mega-cap',   200000000000, NULL,          'Market cap >= $200B',             'AAPL, MSFT, GOOGL'),
    ('Large-cap',  10000000000,  200000000000,  'Market cap $10B - $200B',         'many S&P 500 stocks'),
    ('Mid-cap',    2000000000,   10000000000,   'Market cap $2B - $10B',           'mid-tier companies'),
    ('Small-cap',  300000000,    2000000000,    'Market cap $300M - $2B',          'smaller public companies'),
    ('Micro-cap',  0,            300000000,     'Market cap < $300M',              'small/speculative stocks'),
    ('Unknown',    NULL,         NULL,          'Market cap not available',        'N/A')
ON CONFLICT (tier_name) DO NOTHING;

-- =============================================================
-- 6. DIM_STOCK  (SCD Type 2)
-- Company/ticker dimension — tracks changes over time
-- =============================================================
CREATE TABLE dim_stock (
    stock_key           SERIAL          PRIMARY KEY,        -- surrogate key
    symbol              VARCHAR(10)     NOT NULL,           -- natural key (ticker)
    company_name        VARCHAR(200)    NOT NULL,
    sector_key          INTEGER         REFERENCES dim_sector(sector_key),
    exchange_key        INTEGER         REFERENCES dim_exchange(exchange_key),
    country_key         INTEGER         REFERENCES dim_country(country_key),
    cap_tier_key        INTEGER         REFERENCES dim_market_cap_tier(cap_tier_key),
    industry            VARCHAR(150),
    market_cap_tier     VARCHAR(20),                        -- denormalized copy for convenience
    country             VARCHAR(50)     DEFAULT 'USA',
    currency            VARCHAR(10)     DEFAULT 'USD',
    market_cap          BIGINT,
    employees           INTEGER,
    website             VARCHAR(255),
    description         TEXT,
    -- SCD Type 2 tracking columns
    effective_from      DATE            NOT NULL DEFAULT CURRENT_DATE,
    effective_to        DATE            NOT NULL DEFAULT '9999-12-31',
    is_current          BOOLEAN         NOT NULL DEFAULT TRUE,
    version             SMALLINT        NOT NULL DEFAULT 1,
    created_at          TIMESTAMP       DEFAULT NOW(),
    updated_at          TIMESTAMP       DEFAULT NOW()
);

-- =============================================================
-- 7. FACT_STOCK_PRICES
-- Grain: one row = one stock's daily OHLCV record
-- =============================================================
CREATE TABLE fact_stock_prices (
    price_key           BIGSERIAL       PRIMARY KEY,
    -- Foreign keys to all 6 dimensions
    date_key            INTEGER         NOT NULL REFERENCES dim_date(date_key),
    stock_key           INTEGER         NOT NULL REFERENCES dim_stock(stock_key),
    exchange_key        INTEGER         REFERENCES dim_exchange(exchange_key),
    sector_key          INTEGER         REFERENCES dim_sector(sector_key),
    country_key         INTEGER         REFERENCES dim_country(country_key),
    cap_tier_key        INTEGER         REFERENCES dim_market_cap_tier(cap_tier_key),
    -- Numeric measures
    open_price          NUMERIC(12, 4)  NOT NULL,
    high_price          NUMERIC(12, 4)  NOT NULL,
    low_price           NUMERIC(12, 4)  NOT NULL,
    close_price         NUMERIC(12, 4)  NOT NULL,
    adj_close_price     NUMERIC(12, 4),
    volume              BIGINT          NOT NULL,
    -- Derived measures (calculated at load time)
    price_change        NUMERIC(12, 4),                     -- close - open
    daily_return_pct    NUMERIC(8,  4),                     -- (close-open)/open * 100
    high_low_spread     NUMERIC(12, 4),                     -- high - low
    -- Metadata
    created_at          TIMESTAMP       DEFAULT NOW(),
    updated_at          TIMESTAMP       DEFAULT NOW()
);

-- =============================================================
-- Seed: known exchanges
-- =============================================================
INSERT INTO dim_exchange (exchange_code, exchange_name, country, timezone, currency)
VALUES
    ('NASDAQ', 'NASDAQ Stock Market',        'USA', 'America/New_York', 'USD'),
    ('NYSE',   'New York Stock Exchange',    'USA', 'America/New_York', 'USD'),
    ('NYQ',    'NYSE (Yahoo format)',         'USA', 'America/New_York', 'USD'),
    ('NMS',    'NASDAQ Market Select',       'USA', 'America/New_York', 'USD'),
    ('NGM',    'NASDAQ Global Market',       'USA', 'America/New_York', 'USD'),
    ('LSE',    'London Stock Exchange',      'GBR', 'Europe/London',    'GBP'),
    ('OTHER',  'Other / Unknown Exchange',   'USA', 'America/New_York', 'USD')
ON CONFLICT (exchange_code) DO NOTHING;

-- =============================================================
-- Verification queries (run after creation)
-- =============================================================
-- SELECT COUNT(*) FROM dim_date;             -- expect 4748
-- SELECT COUNT(*) FROM dim_exchange;         -- expect 7
-- SELECT COUNT(*) FROM dim_country;          -- expect 10
-- SELECT COUNT(*) FROM dim_market_cap_tier;  -- expect 6
-- SELECT * FROM dim_date WHERE full_date = CURRENT_DATE;
