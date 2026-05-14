-- =============================================================
-- analytical_queries.sql
-- Stock Market Data Warehouse — Business Intelligence Queries
-- Domain  : Stock Market Daily Trading
-- Dataset : 80 stocks | 100,400 rows | 2021-05-06 to 2026-05-05
-- =============================================================


-- =============================================================
-- QUERY 1: Top 10 Best Performing Stocks (5-Year Total Return)
-- Business Question: Which stocks delivered the highest price
--                    appreciation over the entire 5-year period?
-- =============================================================
WITH price_endpoints AS (
    SELECT
        s.symbol,
        s.company_name,
        sec.sector_name,
        t.cap_tier_key,
        ct.tier_name AS market_cap_tier,
        FIRST_VALUE(f.close_price) OVER (
            PARTITION BY s.symbol ORDER BY d.full_date ASC
        ) AS first_close,
        LAST_VALUE(f.close_price) OVER (
            PARTITION BY s.symbol ORDER BY d.full_date ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_close
    FROM fact_stock_prices f
    JOIN dim_stock        s   ON f.stock_key    = s.stock_key   AND s.is_current = TRUE
    JOIN dim_date         d   ON f.date_key     = d.date_key
    JOIN dim_sector       sec ON f.sector_key   = sec.sector_key
    JOIN dim_market_cap_tier ct ON s.cap_tier_key = ct.cap_tier_key
    WHERE t.cap_tier_key IS NOT NULL
)
SELECT DISTINCT
    symbol,
    company_name,
    sector_name,
    market_cap_tier,
    ROUND(first_close, 2)                                          AS start_price,
    ROUND(last_close,  2)                                          AS end_price,
    ROUND((last_close - first_close) / first_close * 100, 2)      AS total_return_pct
FROM price_endpoints
ORDER BY total_return_pct DESC
LIMIT 10;


-- =============================================================
-- QUERY 2: Sector Performance — Average Daily Return & Volatility
-- Business Question: Which sectors are most profitable and most
--                    volatile on a daily basis?
-- =============================================================
SELECT
    sec.sector_name,
    COUNT(DISTINCT s.symbol)                    AS num_stocks,
    COUNT(f.price_key)                          AS total_trading_days,
    ROUND(AVG(f.daily_return_pct), 4)           AS avg_daily_return_pct,
    ROUND(STDDEV(f.daily_return_pct), 4)        AS volatility_stddev,
    ROUND(AVG(f.high_low_spread), 2)            AS avg_daily_spread,
    ROUND(MAX(f.daily_return_pct), 2)           AS best_single_day_pct,
    ROUND(MIN(f.daily_return_pct), 2)           AS worst_single_day_pct,
    ROUND(AVG(f.volume), 0)                     AS avg_daily_volume
FROM fact_stock_prices  f
JOIN dim_stock          s   ON f.stock_key  = s.stock_key AND s.is_current = TRUE
JOIN dim_sector         sec ON f.sector_key = sec.sector_key
GROUP BY sec.sector_name
ORDER BY avg_daily_return_pct DESC;


-- =============================================================
-- QUERY 3: Monthly Trading Volume Trends by Sector (2023-2026)
-- Business Question: How has trading activity evolved month over
--                    month across different market sectors?
-- =============================================================
SELECT
    d.year,
    d.month,
    d.month_name,
    sec.sector_name,
    ROUND(SUM(f.volume) / 1000000.0, 2)        AS total_volume_millions,
    ROUND(AVG(f.volume), 0)                     AS avg_daily_volume,
    COUNT(DISTINCT s.symbol)                    AS active_stocks
FROM fact_stock_prices  f
JOIN dim_date           d   ON f.date_key   = d.date_key
JOIN dim_stock          s   ON f.stock_key  = s.stock_key AND s.is_current = TRUE
JOIN dim_sector         sec ON f.sector_key = sec.sector_key
WHERE d.year >= 2023
  AND d.is_weekend = FALSE
GROUP BY d.year, d.month, d.month_name, sec.sector_name
ORDER BY d.year, d.month, total_volume_millions DESC;


-- =============================================================
-- QUERY 4: Most Volatile Stocks (Highest Avg Daily Price Swing)
-- Business Question: Which stocks have the widest average daily
--                    price swings (high-low spread)?
-- =============================================================
SELECT
    s.symbol,
    s.company_name,
    sec.sector_name,
    ct.tier_name                                AS market_cap_tier,
    ROUND(AVG(f.high_low_spread), 2)            AS avg_daily_spread,
    ROUND(AVG(f.high_low_spread /
        NULLIF(f.close_price, 0) * 100), 2)    AS avg_spread_pct_of_price,
    ROUND(STDDEV(f.daily_return_pct), 4)        AS return_volatility,
    ROUND(MAX(f.high_price), 2)                 AS all_time_high,
    ROUND(MIN(f.low_price), 2)                  AS all_time_low
FROM fact_stock_prices      f
JOIN dim_stock              s   ON f.stock_key    = s.stock_key AND s.is_current = TRUE
JOIN dim_sector             sec ON f.sector_key   = sec.sector_key
JOIN dim_market_cap_tier    ct  ON f.cap_tier_key = ct.cap_tier_key
GROUP BY s.symbol, s.company_name, sec.sector_name, ct.tier_name
ORDER BY avg_spread_pct_of_price DESC
LIMIT 15;


-- =============================================================
-- QUERY 5: Year-over-Year Price Performance by Sector
-- Business Question: How did each sector's average stock price
--                    change year over year?
-- =============================================================
WITH yearly_avg AS (
    SELECT
        d.year,
        sec.sector_name,
        ROUND(AVG(f.close_price), 2)            AS avg_close_price,
        ROUND(AVG(f.daily_return_pct), 4)       AS avg_return_pct,
        ROUND(SUM(f.volume) / 1000000.0, 0)     AS total_vol_millions
    FROM fact_stock_prices  f
    JOIN dim_date           d   ON f.date_key   = d.date_key
    JOIN dim_stock          s   ON f.stock_key  = s.stock_key AND s.is_current = TRUE
    JOIN dim_sector         sec ON f.sector_key = sec.sector_key
    WHERE d.year BETWEEN 2022 AND 2026
    GROUP BY d.year, sec.sector_name
)
SELECT
    curr.sector_name,
    curr.year,
    curr.avg_close_price                        AS avg_price,
    curr.avg_return_pct,
    curr.total_vol_millions,
    ROUND(
        (curr.avg_close_price - prev.avg_close_price)
        / NULLIF(prev.avg_close_price, 0) * 100, 2
    )                                           AS yoy_price_change_pct
FROM yearly_avg curr
LEFT JOIN yearly_avg prev
    ON curr.sector_name = prev.sector_name
   AND curr.year = prev.year + 1
ORDER BY curr.sector_name, curr.year;


-- =============================================================
-- QUERY 6: Top 10 Highest Volume Trading Days (Market Events)
-- Business Question: What were the highest-volume trading days?
--                    (Often corresponds to major market events)
-- =============================================================
SELECT
    d.full_date,
    d.day_name,
    d.fiscal_quarter,
    s.symbol,
    s.company_name,
    sec.sector_name,
    f.volume,
    ROUND(f.close_price, 2)                     AS close_price,
    ROUND(f.daily_return_pct, 2)                AS daily_return_pct,
    ROUND(f.high_low_spread, 2)                 AS price_swing
FROM fact_stock_prices  f
JOIN dim_date           d   ON f.date_key   = d.date_key
JOIN dim_stock          s   ON f.stock_key  = s.stock_key AND s.is_current = TRUE
JOIN dim_sector         sec ON f.sector_key = sec.sector_key
ORDER BY f.volume DESC
LIMIT 10;


-- =============================================================
-- QUERY 7: Market Cap Tier Comparison — Return vs Risk
-- Business Question: Do larger companies offer better risk-adjusted
--                    returns compared to smaller companies?
-- =============================================================
SELECT
    ct.tier_name                                AS market_cap_tier,
    ct.min_market_cap / 1000000000.0           AS min_cap_billion,
    COUNT(DISTINCT s.symbol)                    AS num_stocks,
    COUNT(f.price_key)                          AS trading_day_records,
    ROUND(AVG(f.daily_return_pct), 4)           AS avg_daily_return_pct,
    ROUND(STDDEV(f.daily_return_pct), 4)        AS risk_stddev,
    ROUND(
        AVG(f.daily_return_pct) /
        NULLIF(STDDEV(f.daily_return_pct), 0), 4
    )                                           AS sharpe_ratio_proxy,
    ROUND(AVG(f.volume) / 1000000.0, 2)        AS avg_volume_millions,
    ROUND(AVG(f.high_low_spread), 2)            AS avg_price_spread
FROM fact_stock_prices      f
JOIN dim_stock              s   ON f.stock_key    = s.stock_key AND s.is_current = TRUE
JOIN dim_market_cap_tier    ct  ON f.cap_tier_key = ct.cap_tier_key
WHERE ct.tier_name != 'Unknown'
GROUP BY ct.tier_name, ct.min_market_cap
ORDER BY ct.min_market_cap DESC NULLS FIRST;


-- =============================================================
-- QUERY 8: Quarterly Performance Summary (2024-2026)
-- Business Question: How did the market perform each quarter?
--                    Which quarter was consistently strongest?
-- =============================================================
SELECT
    d.year,
    d.fiscal_quarter,
    COUNT(DISTINCT s.symbol)                    AS active_stocks,
    COUNT(f.price_key)                          AS trading_records,
    ROUND(AVG(f.close_price), 2)                AS avg_close_price,
    ROUND(AVG(f.daily_return_pct), 4)           AS avg_daily_return,
    ROUND(SUM(f.volume) / 1000000000.0, 2)     AS total_vol_billions,
    ROUND(AVG(f.high_low_spread), 2)            AS avg_daily_spread,
    COUNT(CASE WHEN f.daily_return_pct > 0 THEN 1 END) AS positive_days,
    COUNT(CASE WHEN f.daily_return_pct < 0 THEN 1 END) AS negative_days,
    ROUND(
        COUNT(CASE WHEN f.daily_return_pct > 0 THEN 1 END)::NUMERIC /
        NULLIF(COUNT(f.price_key), 0) * 100, 1
    )                                           AS pct_positive_days
FROM fact_stock_prices  f
JOIN dim_date           d   ON f.date_key  = d.date_key
JOIN dim_stock          s   ON f.stock_key = s.stock_key AND s.is_current = TRUE
WHERE d.year >= 2024
GROUP BY d.year, d.fiscal_quarter
ORDER BY d.year, d.fiscal_quarter;


-- =============================================================
-- QUERY 9: Rolling 30-Day Average Close Price (Top 5 Tech Stocks)
-- Business Question: What is the 30-day moving average trend for
--                    the largest technology stocks?
-- =============================================================
SELECT
    d.full_date,
    s.symbol,
    ROUND(f.close_price, 2)                     AS daily_close,
    ROUND(
        AVG(f.close_price) OVER (
            PARTITION BY s.symbol
            ORDER BY d.full_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 2
    )                                           AS ma_30_day,
    ROUND(
        AVG(f.close_price) OVER (
            PARTITION BY s.symbol
            ORDER BY d.full_date
            ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
        ), 2
    )                                           AS ma_90_day,
    ROUND(f.volume / 1000000.0, 2)             AS volume_millions
FROM fact_stock_prices  f
JOIN dim_date           d   ON f.date_key   = d.date_key
JOIN dim_stock          s   ON f.stock_key  = s.stock_key AND s.is_current = TRUE
JOIN dim_sector         sec ON f.sector_key = sec.sector_key
WHERE sec.sector_name = 'Technology'
  AND s.symbol IN ('AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META')
  AND d.year >= 2024
ORDER BY d.full_date, s.symbol;


-- =============================================================
-- QUERY 10: Country & Exchange Analysis — Stock Distribution
-- Business Question: How are companies distributed across
--                    countries and exchanges, and how do their
--                    average metrics compare?
-- =============================================================
SELECT
    c.country_name,
    c.region,
    c.market_type,
    e.exchange_code,
    COUNT(DISTINCT s.symbol)                    AS num_stocks,
    ROUND(AVG(f.close_price), 2)                AS avg_close_price,
    ROUND(AVG(f.daily_return_pct), 4)           AS avg_daily_return,
    ROUND(AVG(f.volume) / 1000000.0, 2)        AS avg_volume_millions,
    ROUND(STDDEV(f.daily_return_pct), 4)        AS return_volatility,
    COUNT(f.price_key)                          AS total_records
FROM fact_stock_prices  f
JOIN dim_stock          s   ON f.stock_key    = s.stock_key AND s.is_current = TRUE
JOIN dim_country        c   ON f.country_key  = c.country_key
JOIN dim_exchange       e   ON f.exchange_key = e.exchange_key
GROUP BY c.country_name, c.region, c.market_type, e.exchange_code
ORDER BY num_stocks DESC, avg_daily_return DESC;


-- =============================================================
-- QUERY 11: ROLLUP — Sector × Year Multi-Level Aggregation
-- Business Question: What are the subtotals and grand total of
--   trading activity broken down by sector and year?
-- Demonstrates: GROUP BY ROLLUP (hierarchical subtotals)
-- =============================================================
SELECT
    COALESCE(sec.sector_name, '★ ALL SECTORS')  AS sector,
    COALESCE(d.year::TEXT,    '★ ALL YEARS')     AS year,
    COUNT(f.fact_id)                              AS trading_records,
    ROUND(AVG(f.close_price), 2)                 AS avg_close_price,
    ROUND(AVG(f.daily_return_pct), 4)            AS avg_daily_return_pct,
    ROUND(SUM(f.volume) / 1000000000.0, 2)       AS total_vol_billions,
    ROUND(STDDEV(f.daily_return_pct), 4)         AS return_volatility
FROM fact_stock_prices  f
JOIN dim_date           d   ON f.date_key   = d.date_key
JOIN dim_stock          s   ON f.stock_key  = s.stock_key AND s.is_current = TRUE
JOIN dim_sector         sec ON f.sector_key = sec.sector_key
WHERE d.year BETWEEN 2022 AND 2026
GROUP BY ROLLUP(sec.sector_name, d.year)
ORDER BY
    CASE WHEN sec.sector_name IS NULL THEN 1 ELSE 0 END,
    sec.sector_name,
    CASE WHEN d.year IS NULL THEN 1 ELSE 0 END,
    d.year;


-- =============================================================
-- QUERY 12: CUBE — Full Cross-Dimensional Analysis
-- Business Question: How do returns and volatility compare across
--   every combination of sector, year, and geographic region?
-- Demonstrates: GROUP BY CUBE (all possible subtotal combinations)
-- =============================================================
SELECT
    COALESCE(sec.sector_name, '★ ALL SECTORS') AS sector,
    COALESCE(d.year::TEXT,    '★ ALL YEARS')   AS year,
    COALESCE(c.region,        '★ ALL REGIONS') AS region,
    COUNT(f.fact_id)                            AS records,
    COUNT(DISTINCT s.symbol)                    AS num_stocks,
    ROUND(AVG(f.daily_return_pct), 4)          AS avg_daily_return_pct,
    ROUND(STDDEV(f.daily_return_pct), 4)       AS volatility,
    ROUND(SUM(f.volume) / 1000000000.0, 2)     AS total_vol_billions
FROM fact_stock_prices  f
JOIN dim_date           d   ON f.date_key    = d.date_key
JOIN dim_stock          s   ON f.stock_key   = s.stock_key AND s.is_current = TRUE
JOIN dim_sector         sec ON f.sector_key  = sec.sector_key
JOIN dim_country        c   ON f.country_key = c.country_key
WHERE d.year BETWEEN 2023 AND 2026
GROUP BY CUBE(sec.sector_name, d.year, c.region)
ORDER BY
    CASE WHEN sec.sector_name IS NULL THEN 1 ELSE 0 END,
    sec.sector_name,
    CASE WHEN d.year IS NULL THEN 1 ELSE 0 END,
    d.year,
    CASE WHEN c.region IS NULL THEN 1 ELSE 0 END,
    c.region;
