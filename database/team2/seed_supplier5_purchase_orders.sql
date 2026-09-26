-- ====================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2
-- Seed Script: Purchase Orders specifically assigned to Supplier 5 (Demo Supplier Company)
-- Ensures multi-supplier data isolation and supplier-specific viewing
-- ====================================================================

-- PO for Supplier 5 (Demo Supplier Company): Pending Supplier Response
INSERT INTO "PurchaseOrders" (
    supplier_id, ordered_by, order_date, expected_delivery, total_amount, status, supplier_response
) VALUES (
    5, 2, CURRENT_DATE, CURRENT_DATE + INTERVAL '12 days', 49000.00, 'Pending', 'Pending'
);

-- Line items for the new PO
INSERT INTO "PurchaseOrderItems" (
    purchase_order_id, product_id, quantity, unit_price, subtotal
) VALUES 
    ((SELECT MAX(purchase_order_id) FROM "PurchaseOrders"), 3, 50, 80.00, 4000.00),
    ((SELECT MAX(purchase_order_id) FROM "PurchaseOrders"), 4, 10, 4500.00, 45000.00);

-- PO 2 for Supplier 5: Accepted PO
INSERT INTO "PurchaseOrders" (
    supplier_id, ordered_by, order_date, expected_delivery, total_amount, status, supplier_response, supplier_response_date
) VALUES (
    5, 2, CURRENT_DATE - INTERVAL '3 days', CURRENT_DATE + INTERVAL '4 days', 15000.00, 'Accepted', 'Accepted', NOW()
);

-- Line items for PO 2
INSERT INTO "PurchaseOrderItems" (
    purchase_order_id, product_id, quantity, unit_price, subtotal
) VALUES 
    ((SELECT MAX(purchase_order_id) FROM "PurchaseOrders"), 5, 30, 500.00, 15000.00);
