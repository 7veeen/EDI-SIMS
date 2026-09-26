-- ====================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2
-- Seed Script: Real Purchase Orders and Items in Supabase DB
-- ====================================================================

-- Insert PO 1: Pending Supplier Response
INSERT INTO "PurchaseOrders" (
    supplier_id, ordered_by, order_date, expected_delivery, total_amount, status, supplier_response
) VALUES (
    4, 2, CURRENT_DATE, CURRENT_DATE + INTERVAL '7 days', 39960.00, 'Pending', 'Pending'
);

-- Insert Items for the latest PO
INSERT INTO "PurchaseOrderItems" (
    purchase_order_id, product_id, quantity, unit_price, subtotal
) VALUES 
    ((SELECT MAX(purchase_order_id) FROM "PurchaseOrders"), 2, 20, 999.00, 19980.00),
    ((SELECT MAX(purchase_order_id) FROM "PurchaseOrders"), 1, 20, 799.00, 15980.00),
    ((SELECT MAX(purchase_order_id) FROM "PurchaseOrders"), 5, 8, 500.00, 4000.00);

-- Insert PO 2: Pending Supplier Response
INSERT INTO "PurchaseOrders" (
    supplier_id, ordered_by, order_date, expected_delivery, total_amount, status, supplier_response
) VALUES (
    4, 2, CURRENT_DATE - INTERVAL '1 day', CURRENT_DATE + INTERVAL '5 days', 15980.00, 'Pending', 'Pending'
);

-- Insert Items for PO 2
INSERT INTO "PurchaseOrderItems" (
    purchase_order_id, product_id, quantity, unit_price, subtotal
) VALUES 
    ((SELECT MAX(purchase_order_id) FROM "PurchaseOrders"), 1, 20, 799.00, 15980.00);
