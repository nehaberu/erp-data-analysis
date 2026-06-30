-- =============================================================================
-- ERP Order-to-Cash : SQL-based data analysis & error diagnosis
-- Dialect: SQLite (runs with no setup). The patterns are standard SQL.
-- The Python pipeline (analyze.py) loads erp_orders.csv into a table `orders`
-- and runs these queries. Read each one top-to-bottom to understand it.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- PART A — ERROR DIAGNOSIS (data quality)
-- "Find the records that are wrong, and WHY."
-- -----------------------------------------------------------------------------

-- A1. Duplicate orders: same order_id appearing more than once.
--     GROUP BY the key that should be unique, keep groups with COUNT > 1.
SELECT order_id, COUNT(*) AS times_seen
FROM   orders
GROUP  BY order_id
HAVING COUNT(*) > 1
ORDER  BY times_seen DESC;

-- A2. Missing required field (region is empty/NULL).
SELECT COUNT(*) AS rows_missing_region
FROM   orders
WHERE  region IS NULL OR region = '';

-- A3. Impossible values: zero/negative amount (price errors, sign errors).
SELECT
    SUM(CASE WHEN amount <= 0 THEN 1 ELSE 0 END) AS bad_amount_rows,
    SUM(CASE WHEN unit_price = 0 THEN 1 ELSE 0 END) AS zero_price_rows
FROM orders;

-- A4. Illogical process dates: shipped BEFORE it was ordered.
SELECT order_id, order_date, ship_date
FROM   orders
WHERE  julianday(ship_date) < julianday(order_date);

-- A5. Inconsistent category spelling (e.g. 'Dairy' vs 'dairy') -> would split
--     one real category into two in any report. Compare raw vs normalised.
SELECT category AS raw_category, COUNT(*) AS rows
FROM   orders
GROUP  BY category
ORDER  BY LOWER(category), category;


-- -----------------------------------------------------------------------------
-- PART B — PROCESS ANALYSIS (efficiency / optimization potential)
-- "How long does each step take, and where is the bottleneck?"
-- Only use CLEAN rows (valid dates) so metrics aren't polluted by errors.
-- -----------------------------------------------------------------------------

-- B1. Average duration of each process step, in days.
SELECT
    ROUND(AVG(julianday(approval_date) - julianday(order_date)), 2) AS avg_days_order_to_approval,
    ROUND(AVG(julianday(ship_date)     - julianday(approval_date)), 2) AS avg_days_approval_to_ship,
    ROUND(AVG(julianday(invoice_date)  - julianday(ship_date)), 2)     AS avg_days_ship_to_invoice,
    ROUND(AVG(julianday(invoice_date)  - julianday(order_date)), 2)    AS avg_total_cycle_days
FROM orders
WHERE julianday(ship_date) >= julianday(order_date);   -- exclude broken rows

-- B2. Cycle time by region: where is the process slowest?
SELECT
    region,
    COUNT(*) AS orders,
    ROUND(AVG(julianday(invoice_date) - julianday(order_date)), 2) AS avg_cycle_days
FROM   orders
WHERE  region IS NOT NULL
   AND julianday(ship_date) >= julianday(order_date)
GROUP  BY region
ORDER  BY avg_cycle_days DESC;

-- B3. Revenue by category (using only valid amounts) -> business value view.
SELECT
    LOWER(category) AS category,             -- normalise the spelling first!
    COUNT(*)        AS orders,
    ROUND(SUM(amount), 2) AS total_revenue
FROM   orders
WHERE  amount > 0
GROUP  BY LOWER(category)
ORDER  BY total_revenue DESC;

-- B4. Data-quality scorecard in one query: % of rows that are "clean".
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN region IS NULL OR region = ''            THEN 1 ELSE 0 END) AS missing_region,
    SUM(CASE WHEN amount <= 0                              THEN 1 ELSE 0 END) AS bad_amount,
    SUM(CASE WHEN julianday(ship_date) < julianday(order_date) THEN 1 ELSE 0 END) AS bad_dates
FROM orders;
