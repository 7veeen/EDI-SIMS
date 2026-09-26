-- ====================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2
-- Migration: Add Supplier Response Tracking to PurchaseOrders
-- ====================================================================

-- 1. Add supplier response tracking fields
ALTER TABLE "PurchaseOrders"
ADD COLUMN IF NOT EXISTS supplier_response VARCHAR(50) DEFAULT 'Pending',
ADD COLUMN IF NOT EXISTS supplier_response_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- 2. Performance index for supplier PO queries
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_response 
ON "PurchaseOrders"(supplier_id, supplier_response);
