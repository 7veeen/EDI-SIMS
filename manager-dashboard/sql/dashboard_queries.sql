-- ========================================================
-- SMART INVENTORY MANAGEMENT SYSTEM (SIMS)
-- MANAGER DASHBOARD SQL QUERIES (TEAM 2)
-- ========================================================
-- These queries are used by the Manager Dashboard service
-- to fetch live metrics directly from the Supabase PostgreSQL database.
-- NO MOCK DATA is used anywhere in the dashboard.
-- ========================================================

-- 1. SUMMARY METRICS
-- Total Products
SELECT COUNT(*) AS total_products 
FROM "Products";

-- Low Stock Products (available <= reorder_level AND > 0)
SELECT COUNT(*) AS low_stock_products
FROM "Products" p
JOIN "Inventory" i ON p.product_id = i.product_id
WHERE i.quantity_available <= p.reorder_level AND i.quantity_available > 0;

-- Out of Stock Products
SELECT COUNT(*) AS out_of_stock_products
FROM "Inventory"
WHERE quantity_available = 0;

-- Pending Stock Requests
SELECT COUNT(*) AS pending_stock_requests
FROM "StockRequests"
WHERE status ILIKE 'Pending';

-- Pending Quotations
SELECT COUNT(*) AS pending_quotations
FROM "SupplierQuotations"
WHERE status ILIKE 'Pending';

-- Pending Purchase Orders
SELECT COUNT(*) AS pending_purchase_orders
FROM "PurchaseOrders"
WHERE status ILIKE 'Pending';

-- Orders In Transit
SELECT COUNT(*) AS orders_in_transit
FROM "PurchaseOrders"
WHERE status ILIKE 'Shipped' OR status ILIKE 'In Transit' OR status ILIKE 'Accepted';

-- Total Active Employees
SELECT COUNT(*) AS total_employees
FROM "Users" u
JOIN "Roles" r ON u.role_id = r.role_id
WHERE r.role_name = 'Employee' AND u.status = 'Active';

-- ========================================================
-- 2. INVENTORY OVERVIEW
-- Breakdown by Availability
SELECT 
    COUNT(*) FILTER (WHERE i.quantity_available > p.reorder_level) AS in_stock,
    COUNT(*) FILTER (WHERE i.quantity_available <= p.reorder_level AND i.quantity_available > 0) AS low_stock,
    COUNT(*) FILTER (WHERE i.quantity_available = 0) AS out_of_stock,
    COALESCE(SUM(i.quantity_available), 0) AS total_units
FROM "Products" p
LEFT JOIN "Inventory" i ON p.product_id = i.product_id;

-- Inventory by Category
SELECT 
    c.category_id,
    c.category_name,
    COUNT(p.product_id) AS product_count,
    COALESCE(SUM(i.quantity_available), 0) AS total_stock
FROM "Categories" c
LEFT JOIN "Products" p ON c.category_id = p.category_id
LEFT JOIN "Inventory" i ON p.product_id = i.product_id
GROUP BY c.category_id, c.category_name
ORDER BY product_count DESC;

-- ========================================================
-- 3. PROCUREMENT PIPELINE
-- Status Breakdown of Purchase Orders
SELECT 
    COUNT(*) AS total_pos,
    COUNT(*) FILTER (WHERE status ILIKE 'Pending') AS pending,
    COUNT(*) FILTER (WHERE status ILIKE 'Accepted') AS accepted,
    COUNT(*) FILTER (WHERE status ILIKE 'Shipped' OR status ILIKE 'In Transit') AS shipped,
    COUNT(*) FILTER (WHERE status ILIKE 'Delivered' OR status ILIKE 'Received') AS delivered,
    COUNT(*) FILTER (WHERE status ILIKE 'Completed') AS completed
FROM "PurchaseOrders";

-- ========================================================
-- 4. LOW STOCK PRODUCTS LIST
SELECT 
    p.product_id,
    p.product_name,
    p.sku,
    COALESCE(c.category_name, 'Unassigned') AS category_name,
    i.quantity_available,
    p.reorder_level,
    p.status AS product_status,
    i.last_updated
FROM "Products" p
JOIN "Inventory" i ON p.product_id = i.product_id
LEFT JOIN "Categories" c ON p.category_id = c.category_id
WHERE i.quantity_available <= p.reorder_level
ORDER BY i.quantity_available ASC, p.product_name ASC;

-- ========================================================
-- 5. RECENT PURCHASE ORDERS
SELECT 
    po.po_id,
    COALESCE(s.supplier_name, 'Supplier #' || po.supplier_id::text) AS supplier_name,
    po.total_amount,
    po.status,
    po.created_at
FROM "PurchaseOrders" po
LEFT JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
ORDER BY po.po_id DESC
LIMIT 10;

-- ========================================================
-- 6. RECENT STOCK TRANSACTIONS
SELECT 
    st.transaction_id,
    COALESCE(p.product_name, 'Product #' || st.product_id::text) AS product_name,
    st.transaction_type,
    st.quantity,
    COALESCE(u.username, 'System') AS user_name,
    st.transaction_date
FROM "StockTransactions" st
LEFT JOIN "Products" p ON st.product_id = p.product_id
LEFT JOIN "Users" u ON st.user_id = u.user_id
ORDER BY st.transaction_id DESC
LIMIT 10;

-- ========================================================
-- 7. EMPLOYEE ROSTER OVERVIEW
SELECT 
    u.user_id,
    u.username,
    u.email,
    u.status
FROM "Users" u
JOIN "Roles" r ON u.role_id = r.role_id
WHERE r.role_name = 'Employee'
ORDER BY u.user_id ASC
LIMIT 10;

-- ========================================================
-- 8. NOTIFICATIONS
SELECT 
    notification_id,
    title,
    message,
    notification_type,
    is_read,
    created_at
FROM "Notifications"
ORDER BY notification_id DESC
LIMIT 10;
