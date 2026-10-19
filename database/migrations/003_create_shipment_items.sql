-- ============================================================================
-- SIMS Migration: 003_create_shipment_items.sql
-- Module: Logistics & Inventory / Procurement Module
-- Feature: Shipment Items Line-Level Allocation Schema
-- Target: Supabase PostgreSQL (public schema)
-- Date: October 18, 2026
--
-- BUSINESS RULES & ARCHITECTURAL SPECIFICATION:
-- 1. SHIPMENT-LEVEL ALLOCATION:
--    - Each shipment can explicitly specify the product allocations it contains.
--    - Enables accurate split-shipment receiving without ambiguous full-PO assumptions.
-- 2. REFERENTIAL INTEGRITY:
--    - shipment_id references public."Shipments"(shipment_id) ON DELETE CASCADE.
--    - product_id references public."Products"(product_id).
-- 3. UNIQUENESS & VALIDATION:
--    - UNIQUE (shipment_id, product_id) prevents duplicate product lines per shipment.
--    - CHECK (quantity > 0) guarantees all allocated quantities are strictly positive.
-- 4. PERFORMANCE & INDEXING:
--    - B-Tree indexes on shipment_id and product_id optimize allocation lookup
--      during goods receipt (stock_in) and shipment aggregation.
-- 5. IDEMPOTENCY:
--    - Uses CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public."ShipmentItems" (
    shipment_item_id    BIGSERIAL PRIMARY KEY,
    shipment_id         BIGINT NOT NULL REFERENCES public."Shipments"(shipment_id) ON DELETE CASCADE,
    product_id          BIGINT NOT NULL REFERENCES public."Products"(product_id),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_shipment_product UNIQUE (shipment_id, product_id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_shipment_items_shipment_id 
    ON public."ShipmentItems" (shipment_id);

CREATE INDEX IF NOT EXISTS idx_shipment_items_product_id 
    ON public."ShipmentItems" (product_id);

COMMIT;
