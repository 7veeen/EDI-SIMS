-- ============================================================================
-- SIMS Proposed Security Migration: 002_secure_supplier_payments_and_invoices_rls.sql
-- Module: Supplier Portal & Finance / Procurement Security Hardening
-- Feature: Supplier Payments MVP — PostgREST Data API Access Lockdown & RLS
-- Target: Supabase PostgreSQL (public schema)
-- Date: October 11, 2026
-- Status: PROPOSED / PENDING DBA APPROVAL (DO NOT APPLY UNTIL AUTHORIZED)
--
-- ARCHITECTURAL RATIONALE:
-- 1. BACKEND-ONLY ARCHITECTURE:
--    SIMS enforces all authentication and role-based access control (RBAC) in
--    the Python/Flask backend using custom JWTs (flask_jwt_extended) and
--    application-level authorization decorators (@role_required).
--    The frontend never calls Supabase PostgREST Data API directly.
--
-- 2. SUPABASE DEFAULT PRIVILEGES (EXPOSURE RISK):
--    By default, Supabase grants SELECT, INSERT, UPDATE, DELETE on newly
--    created tables in the 'public' schema to 'anon' and 'authenticated' roles
--    via pg_default_acl. Because existing SIMS tables have RLS disabled, newly
--    created tables would be immediately accessible via PostgREST Data API
--    (https://<project-ref>.supabase.co/rest/v1/) to anyone with the anon key.
--
-- 3. SMALLEST SAFE SECURITY CHANGE:
--    - Enable Row Level Security (RLS) on "SupplierInvoices" and "SupplierPayments".
--      With zero public policies, non-superuser roles default to DENY ALL.
--    - Explicitly REVOKE ALL permissions on both tables from 'anon', 'authenticated', and PUBLIC.
--
-- 4. BACKEND CONNECTION COMPATIBILITY:
--    - The Flask backend connects as PostgreSQL user 'postgres' (or pooler user).
--    - Role 'postgres' has superuser privileges (rolsuper = true) and
--      bypasses RLS (rolbypassrls = true).
--    - 'postgres' is the table owner, so revoking grants from 'anon' and
--      'authenticated' has ZERO effect on backend queries.
--    - Zero application queries, zero backend services, and zero endpoints are broken.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Enable Row Level Security (Default-Deny for non-superuser roles)
-- ----------------------------------------------------------------------------
ALTER TABLE public."SupplierInvoices" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."SupplierPayments" ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 2. Revoke PostgREST Data API Access from anon, authenticated, and PUBLIC roles
-- ----------------------------------------------------------------------------
REVOKE ALL ON TABLE public."SupplierInvoices" FROM anon, authenticated, PUBLIC;
REVOKE ALL ON TABLE public."SupplierPayments" FROM anon, authenticated, PUBLIC;

-- Comments documenting the security lockdown
COMMENT ON TABLE public."SupplierInvoices" IS 
    'Stores supplier invoices. Secured with RLS and restricted from Supabase Data API (PostgREST). Access mediated exclusively via Flask backend.';

COMMENT ON TABLE public."SupplierPayments" IS 
    'Stores supplier payments. Secured with RLS and restricted from Supabase Data API (PostgREST). Access mediated exclusively via Flask backend.';

COMMIT;
