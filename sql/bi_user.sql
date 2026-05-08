-- =============================================================
-- bi_user.sql
-- Creates a read-only PostgreSQL user for BI tool access
-- No INSERT, UPDATE, or DELETE privileges granted
-- =============================================================

-- Step 1: Create the read-only user
CREATE USER bi_reader WITH PASSWORD 'bi_readonly_2026';

-- Step 2: Allow connection to the warehouse database
GRANT CONNECT ON DATABASE warehouse_db TO bi_reader;

-- Step 3: Allow schema access
GRANT USAGE ON SCHEMA public TO bi_reader;

-- Step 4: Grant SELECT on all existing tables (including materialized views)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_reader;

-- Step 5: Ensure SELECT applies to future tables too
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO bi_reader;

-- =============================================================
-- Verify the user was created correctly:
-- =============================================================
-- \du bi_reader
-- Should show: bi_reader | Cannot login? No — it CAN login but only SELECT

-- Test connection (run as bi_reader):
-- psql -U bi_reader -d warehouse_db -c "SELECT COUNT(*) FROM fact_stock_prices;"
-- Expected: 100400
-- psql -U bi_reader -d warehouse_db -c "INSERT INTO dim_sector VALUES (99, 'Test');"
-- Expected: ERROR: permission denied for table dim_sector

-- =============================================================
-- 6B — dashboard_user (from intern guide Step 6B)
-- Exact SQL block as specified in the Project 4 guide
-- =============================================================
-- Run this block to create the guide-specified dashboard_user:

-- CREATE USER dashboard_user WITH PASSWORD 'dashboard_pass';
-- GRANT CONNECT ON DATABASE warehouse_db TO dashboard_user;
-- GRANT USAGE ON SCHEMA public TO dashboard_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--     GRANT SELECT ON TABLES TO dashboard_user;

-- Note: bi_reader (above) is the production read-only user used by
-- dashboard_app.py.  dashboard_user follows the guide's naming convention
-- and can be applied identically for any external BI tool connection
-- (Looker Studio, Tableau, Power BI, Apache Superset, Metabase).
