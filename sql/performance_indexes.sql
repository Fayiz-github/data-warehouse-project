-- =============================================================
-- performance_indexes.sql
-- Stock Market Data Warehouse — Performance Tuning
-- Purpose : Speed up common analytical query patterns
-- =============================================================

-- 1. Index for date-range scans (Very common in time-series)
CREATE INDEX IF NOT EXISTS idx_fact_date_key ON fact_stock_prices (date_key);

-- 2. Index for stock-specific lookups
CREATE INDEX IF NOT EXISTS idx_fact_stock_key ON fact_stock_prices (stock_key);

-- 3. Composite index for (stock, date) - helps with window functions and trends
CREATE INDEX IF NOT EXISTS idx_fact_stock_date ON fact_stock_prices (stock_key, date_key);

-- 4. Index for sector-based aggregation (joining to dim_sector)
CREATE INDEX IF NOT EXISTS idx_fact_sector_key ON fact_stock_prices (sector_key);

-- 5. Index for market cap tier analysis
CREATE INDEX IF NOT EXISTS idx_fact_cap_tier_key ON fact_stock_prices (cap_tier_key);

-- 6. Index for country/region analysis
CREATE INDEX IF NOT EXISTS idx_fact_country_key ON fact_stock_prices (country_key);

-- 7. Index for volume-based filtering
CREATE INDEX IF NOT EXISTS idx_fact_volume ON fact_stock_prices (volume);

-- Analyze tables to update statistics for the query planner
ANALYZE fact_stock_prices;
ANALYZE dim_stock;
ANALYZE dim_date;
ANALYZE dim_sector;
ANALYZE dim_country;
ANALYZE dim_exchange;
ANALYZE dim_market_cap_tier;

-- Verification query
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'fact_stock_prices'
ORDER BY indexname;
