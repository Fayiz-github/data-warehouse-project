-- =============================================================
-- materialized_views.sql
-- Stock Market Data Warehouse — Materialized Views
-- Purpose : Pre-aggregate heavy analytical queries for fast BI
-- Refresh : REFRESH MATERIALIZED VIEW CONCURRENTLY <view_name>;
-- =============================================================


-- =============================================================
-- VIEW 1: mv_sector_performance_daily
-- Pre-aggregates daily sector-level metrics
-- Used by: sector dashboards, daily market summary reports
-- =============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_sector_performance_daily CASCADE;

CREATE MATERIALIZED VIEW mv_sector_performance_daily AS
SELECT
    d.full_date,
    d.year,
    d.month,
    d.month_name,
    d.quarter,
    d.fiscal_quarter,
    d.day_name,
    d.is_weekend,
    sec.sector_name,
    COUNT(DISTINCT s.symbol)                        AS num_stocks,
    ROUND(AVG(f.open_price),    2)                  AS avg_open,
    ROUND(AVG(f.close_price),   2)                  AS avg_close,
    ROUND(AVG(f.high_price),    2)                  AS avg_high,
    ROUND(AVG(f.low_price),     2)                  AS avg_low,
    ROUND(SUM(f.volume) / 1000000.0, 2)             AS total_volume_millions,
    ROUND(AVG(f.daily_return_pct), 4)               AS avg_daily_return_pct,
    ROUND(STDDEV(f.daily_return_pct), 4)            AS return_volatility,
    ROUND(AVG(f.high_low_spread), 2)                AS avg_spread,
    COUNT(CASE WHEN f.daily_return_pct > 0 THEN 1 END)  AS positive_stocks,
    COUNT(CASE WHEN f.daily_return_pct < 0 THEN 1 END)  AS negative_stocks,
    ROUND(MAX(f.daily_return_pct), 2)               AS best_return_pct,
    ROUND(MIN(f.daily_return_pct), 2)               AS worst_return_pct
FROM fact_stock_prices  f
JOIN dim_date           d   ON f.date_key   = d.date_key
JOIN dim_stock          s   ON f.stock_key  = s.stock_key AND s.is_current = TRUE
JOIN dim_sector         sec ON f.sector_key = sec.sector_key
WHERE d.is_weekend = FALSE
GROUP BY
    d.full_date, d.year, d.month, d.month_name,
    d.quarter, d.fiscal_quarter, d.day_name, d.is_weekend,
    sec.sector_name
ORDER BY d.full_date, sec.sector_name;

-- Index on the materialized view for fast lookups
CREATE INDEX idx_mv_sector_perf_date   ON mv_sector_performance_daily (full_date);
CREATE INDEX idx_mv_sector_perf_sector ON mv_sector_performance_daily (sector_name);
CREATE INDEX idx_mv_sector_perf_year   ON mv_sector_performance_daily (year, month);


-- =============================================================
-- VIEW 2: mv_stock_monthly_summary
-- Pre-aggregates monthly OHLCV and performance per stock
-- Used by: individual stock analysis, YoY comparisons, dashboard
-- =============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_stock_monthly_summary CASCADE;

CREATE MATERIALIZED VIEW mv_stock_monthly_summary AS
SELECT
    d.year,
    d.month,
    d.month_name,
    d.fiscal_quarter,
    s.symbol,
    s.company_name,
    sec.sector_name,
    ct.tier_name                                    AS market_cap_tier,
    c.country_name,
    e.exchange_code,
    COUNT(f.price_key)                              AS trading_days,
    -- OHLCV monthly aggregates
    ROUND(FIRST_VALUE(f.open_price) OVER (
        PARTITION BY d.year, d.month, s.symbol
        ORDER BY d.full_date ASC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ), 2)                                           AS month_open,
    ROUND(MAX(f.high_price), 2)                     AS month_high,
    ROUND(MIN(f.low_price),  2)                     AS month_low,
    ROUND(LAST_VALUE(f.close_price) OVER (
        PARTITION BY d.year, d.month, s.symbol
        ORDER BY d.full_date ASC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ), 2)                                           AS month_close,
    ROUND(SUM(f.volume) / 1000000.0, 2)            AS total_volume_millions,
    ROUND(AVG(f.volume) / 1000000.0, 2)            AS avg_daily_volume_millions,
    -- Performance metrics
    ROUND(AVG(f.daily_return_pct), 4)              AS avg_daily_return_pct,
    ROUND(SUM(f.daily_return_pct), 4)              AS total_monthly_return_pct,
    ROUND(STDDEV(f.daily_return_pct), 4)           AS monthly_volatility,
    ROUND(AVG(f.high_low_spread), 2)               AS avg_daily_spread,
    COUNT(CASE WHEN f.daily_return_pct > 0 THEN 1 END) AS positive_days,
    COUNT(CASE WHEN f.daily_return_pct < 0 THEN 1 END) AS negative_days
FROM fact_stock_prices      f
JOIN dim_date               d   ON f.date_key    = d.date_key
JOIN dim_stock              s   ON f.stock_key   = s.stock_key AND s.is_current = TRUE
JOIN dim_sector             sec ON f.sector_key  = sec.sector_key
JOIN dim_market_cap_tier    ct  ON f.cap_tier_key= ct.cap_tier_key
JOIN dim_country            c   ON f.country_key = c.country_key
JOIN dim_exchange           e   ON f.exchange_key= e.exchange_key
WHERE d.is_weekend = FALSE
GROUP BY
    d.year, d.month, d.month_name, d.fiscal_quarter,
    s.symbol, s.company_name, sec.sector_name,
    ct.tier_name, c.country_name, e.exchange_code,
    d.full_date, f.open_price, f.close_price
ORDER BY d.year, d.month, s.symbol;

-- Indexes for fast monthly lookups
CREATE INDEX idx_mv_monthly_symbol ON mv_stock_monthly_summary (symbol);
CREATE INDEX idx_mv_monthly_year   ON mv_stock_monthly_summary (year, month);
CREATE INDEX idx_mv_monthly_sector ON mv_stock_monthly_summary (sector_name);


-- =============================================================
-- VIEW 3: mv_market_cap_tier_quarterly
-- Quarterly performance aggregated by market cap tier
-- Used by: executive dashboards, investment strategy analysis
-- =============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_market_cap_tier_quarterly CASCADE;

CREATE MATERIALIZED VIEW mv_market_cap_tier_quarterly AS
SELECT
    d.year,
    d.quarter,
    d.fiscal_quarter,
    ct.tier_name                                    AS market_cap_tier,
    ct.min_market_cap,
    ct.max_market_cap,
    COUNT(DISTINCT s.symbol)                        AS num_stocks,
    COUNT(f.price_key)                              AS total_records,
    -- Return metrics
    ROUND(AVG(f.daily_return_pct), 4)              AS avg_daily_return_pct,
    ROUND(SUM(f.daily_return_pct), 2)              AS cumulative_return_pct,
    ROUND(STDDEV(f.daily_return_pct), 4)           AS return_volatility,
    ROUND(
        AVG(f.daily_return_pct) /
        NULLIF(STDDEV(f.daily_return_pct), 0), 4
    )                                               AS sharpe_ratio_proxy,
    -- Volume metrics
    ROUND(AVG(f.volume) / 1000000.0, 2)            AS avg_daily_vol_millions,
    ROUND(SUM(f.volume) / 1000000000.0, 2)         AS total_vol_billions,
    -- Price metrics
    ROUND(AVG(f.close_price), 2)                   AS avg_close_price,
    ROUND(AVG(f.high_low_spread), 2)               AS avg_daily_spread,
    -- Win/loss ratio
    COUNT(CASE WHEN f.daily_return_pct > 0 THEN 1 END) AS winning_days,
    COUNT(CASE WHEN f.daily_return_pct < 0 THEN 1 END) AS losing_days,
    ROUND(
        COUNT(CASE WHEN f.daily_return_pct > 0 THEN 1 END)::NUMERIC /
        NULLIF(COUNT(f.price_key), 0) * 100, 1
    )                                               AS win_rate_pct
FROM fact_stock_prices      f
JOIN dim_date               d   ON f.date_key    = d.date_key
JOIN dim_stock              s   ON f.stock_key   = s.stock_key AND s.is_current = TRUE
JOIN dim_market_cap_tier    ct  ON f.cap_tier_key= ct.cap_tier_key
WHERE d.is_weekend = FALSE
  AND ct.tier_name != 'Unknown'
GROUP BY
    d.year, d.quarter, d.fiscal_quarter,
    ct.tier_name, ct.min_market_cap, ct.max_market_cap
ORDER BY d.year, d.quarter, ct.min_market_cap DESC NULLS FIRST;

-- Index for fast tier lookups
CREATE INDEX idx_mv_tier_qtr_year ON mv_market_cap_tier_quarterly (year, quarter);
CREATE INDEX idx_mv_tier_qtr_tier ON mv_market_cap_tier_quarterly (market_cap_tier);


-- =============================================================
-- Verify all 3 materialized views created successfully
-- =============================================================
SELECT
    schemaname,
    matviewname                 AS view_name,
    hasindexes,
    ispopulated
FROM pg_matviews
WHERE schemaname = 'public'
ORDER BY matviewname;


-- =============================================================
-- HOW TO REFRESH (run after new data loads):
-- =============================================================
-- REFRESH MATERIALIZED VIEW mv_sector_performance_daily;
-- REFRESH MATERIALIZED VIEW mv_stock_monthly_summary;
-- REFRESH MATERIALIZED VIEW mv_market_cap_tier_quarterly;
