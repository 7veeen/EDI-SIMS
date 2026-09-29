-- ====================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2
-- Module: Soumya — Shipment & History
-- Seed Script: Populate Realistic Previous Quotations for Suppliers
-- Target: Supabase Shared PostgreSQL Database ("SupplierQuotations")
-- ====================================================================

-- Quotations for Supplier 4
INSERT INTO "SupplierQuotations" (
    supplier_id, product_id, quotation_date, quoted_price, quantity, valid_until, status
)
SELECT 
    4, 1, CURRENT_DATE - INTERVAL '14 days', 750.00, 50, CURRENT_DATE + INTERVAL '16 days', 'Accepted'
WHERE EXISTS (SELECT 1 FROM "Suppliers" WHERE supplier_id = 4)
  AND EXISTS (SELECT 1 FROM "Products" WHERE product_id = 1)
  AND NOT EXISTS (SELECT 1 FROM "SupplierQuotations" WHERE supplier_id = 4 AND product_id = 1 AND status = 'Accepted');

INSERT INTO "SupplierQuotations" (
    supplier_id, product_id, quotation_date, quoted_price, quantity, valid_until, status
)
SELECT 
    4, 2, CURRENT_DATE - INTERVAL '10 days', 920.00, 30, CURRENT_DATE + INTERVAL '20 days', 'Pending'
WHERE EXISTS (SELECT 1 FROM "Suppliers" WHERE supplier_id = 4)
  AND EXISTS (SELECT 1 FROM "Products" WHERE product_id = 2)
  AND NOT EXISTS (SELECT 1 FROM "SupplierQuotations" WHERE supplier_id = 4 AND product_id = 2 AND status = 'Pending');

INSERT INTO "SupplierQuotations" (
    supplier_id, product_id, quotation_date, quoted_price, quantity, valid_until, status
)
SELECT 
    4, 5, CURRENT_DATE - INTERVAL '30 days', 480.00, 100, CURRENT_DATE - INTERVAL '2 days', 'Expired'
WHERE EXISTS (SELECT 1 FROM "Suppliers" WHERE supplier_id = 4)
  AND EXISTS (SELECT 1 FROM "Products" WHERE product_id = 5)
  AND NOT EXISTS (SELECT 1 FROM "SupplierQuotations" WHERE supplier_id = 4 AND product_id = 5 AND status = 'Expired');

-- Quotations for Supplier 5
INSERT INTO "SupplierQuotations" (
    supplier_id, product_id, quotation_date, quoted_price, quantity, valid_until, status
)
SELECT 
    5, 4, CURRENT_DATE - INTERVAL '20 days', 4200.00, 10, CURRENT_DATE + INTERVAL '10 days', 'Accepted'
WHERE EXISTS (SELECT 1 FROM "Suppliers" WHERE supplier_id = 5)
  AND EXISTS (SELECT 1 FROM "Products" WHERE product_id = 4)
  AND NOT EXISTS (SELECT 1 FROM "SupplierQuotations" WHERE supplier_id = 5 AND product_id = 4 AND status = 'Accepted');

INSERT INTO "SupplierQuotations" (
    supplier_id, product_id, quotation_date, quoted_price, quantity, valid_until, status
)
SELECT 
    5, 3, CURRENT_DATE - INTERVAL '7 days', 75.00, 200, CURRENT_DATE + INTERVAL '23 days', 'Under Review'
WHERE EXISTS (SELECT 1 FROM "Suppliers" WHERE supplier_id = 5)
  AND EXISTS (SELECT 1 FROM "Products" WHERE product_id = 3)
  AND NOT EXISTS (SELECT 1 FROM "SupplierQuotations" WHERE supplier_id = 5 AND product_id = 3 AND status = 'Under Review');
