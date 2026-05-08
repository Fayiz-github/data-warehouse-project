-- =============================================================
-- storage_optimization.sql
-- Stock Market Data Warehouse — Storage Management
-- Purpose : Keep the warehouse lean by applying retention
--           policies, vacuuming dead rows, and monitoring size
-- Run     : psql -U postgres -d warehouse_db -f sql/storage_optimization.sql
-- =============================================================


-- =============================================================
-- SECTION 1: CHECK CURRENT DATABASE SIZE
-- =============================================================
SELECT
    pg_size_pretty(pg_database_size(current_database())) AS db_size,
    current_database() AS db_name;

-- Table-level size breakdown
SELECT
    relname                          AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid))        AS table_size,
    pg_size_pretty(pg_indexes_size(relid))         AS index_size,
    n_live_tup                                     AS live_rows,
    n_dead_tup                                     AS dead_rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;


-- =============================================================
-- SECTION 2: RETENTION POLICY
-- Keep only the last 5 years of fact data (configurable)
-- Safe: Uses a CTE to preview before deleting
-- =============================================================

-- PREVIEW: How many rows would be deleted?
SELECT COUNT(*) AS rows_to_delete
FROM fact_stock_prices f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.full_date < NOW() - INTERVAL '5 years';

-- APPLY: Delete fact rows older than 5 years
-- Uncomment to execute:
/*
DELETE FROM fact_stock_prices f
USING dim_date d
WHERE f.date_key = d.date_key
  AND d.full_date < NOW() - INTERVAL '5 years';
*/

-- APPLY: Delete fact rows older than 3 years (more aggressive)
/*
DELETE FROM fact_stock_prices f
USING dim_date d
WHERE f.date_key = d.date_key
  AND d.full_date < NOW() - INTERVAL '3 years';
*/


-- =============================================================
-- SECTION 3: VACUUM & ANALYZE (Reclaim Dead Row Space)
-- Run this after bulk deletes or updates
-- =============================================================

-- Full vacuum + analyze on the fact table
VACUUM ANALYZE fact_stock_prices;

-- Vacuum all dimension tables
VACUUM ANALYZE dim_stock;
VACUUM ANALYZE dim_date;
VACUUM ANALYZE dim_sector;
VACUUM ANALYZE dim_country;
VACUUM ANALYZE dim_exchange;
VACUUM ANALYZE dim_market_cap_tier;


-- =============================================================
-- SECTION 4: REFRESH MATERIALIZED VIEWS
-- After retention cleanup, refresh aggregated views
-- =============================================================
REFRESH MATERIALIZED VIEW mv_sector_performance_daily;
REFRESH MATERIALIZED VIEW mv_stock_monthly_summary;
REFRESH MATERIALIZED VIEW mv_market_cap_tier_quarterly;


-- =============================================================
-- SECTION 5: DUPLICATE GUARD
-- Remove any accidental duplicate fact rows
-- (same stock + same date should appear only once)
-- =============================================================

-- PREVIEW duplicates
SELECT stock_key, date_key, COUNT(*) AS cnt
FROM fact_stock_prices
GROUP BY stock_key, date_key
HAVING COUNT(*) > 1
ORDER BY cnt DESC;

-- REMOVE duplicates (keeps lowest ctid = oldest inserted)
/*
DELETE FROM fact_stock_prices
WHERE ctid NOT IN (
    SELECT MIN(ctid)
    FROM fact_stock_prices
    GROUP BY stock_key, date_key
);
*/


-- =============================================================
-- SECTION 6: VERIFY STORAGE AFTER CLEANUP
-- =============================================================
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Remaining fact rows after cleanup
SELECT
    COUNT(*) AS remaining_rows,
    MIN(d.full_date) AS oldest_date,
    MAX(d.full_date) AS newest_date
FROM fact_stock_prices f
JOIN dim_date d ON f.date_key = d.date_key;
