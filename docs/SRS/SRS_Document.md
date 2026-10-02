# Software Requirements Specification (SRS)
## Smart Inventory Management System (SIMS)

**Standard:** IEEE 830-1998 Aligned  
**Version:** 1.0.0  
**Date:** September 2026  
**Status:** Approved & Under Implementation  

---

## Table of Contents
1. [Introduction](#1-introduction)
   - 1.1 Purpose
   - 1.2 Document Conventions
   - 1.3 Intended Audience & Reading Suggestions
   - 1.4 Project Scope
   - 1.5 References
2. [Overall Description](#2-overall-description)
   - 2.1 Product Perspective
   - 2.2 Product Functions
   - 2.3 User Classes and Characteristics
   - 2.4 Operating Environment
   - 2.5 Design and Implementation Constraints
   - 2.6 Assumptions and Dependencies
3. [System Features & Functional Requirements](#3-system-features--functional-requirements)
   - 3.1 Authentication & Role-Based Access Control (RBAC)
   - 3.2 Master Catalog & Inventory Management
   - 3.3 Supplier Procurement & Order Lifecycle
   - 3.4 Operational Telemetry & Reporting Engine
   - 3.5 System Auditing & Disaster Recovery
4. [External Interface Requirements](#4-external-interface-requirements)
   - 4.1 User Interfaces
   - 4.2 Software Interfaces
   - 4.3 Communications Interfaces
5. [Non-Functional Requirements (NFRs)](#5-non-functional-requirements-nfrs)
   - 5.1 Performance Requirements
   - 5.2 Safety & Security Requirements
   - 5.3 Software Quality Attributes
6. [Requirements Traceability Matrix](#6-requirements-traceability-matrix)

---

## 1. Introduction

### 1.1 Purpose
This document provides the complete specification of requirements for the **Smart Inventory Management System (SIMS)**. It outlines functional behavior, performance constraints, user role boundaries, security guarantees, and external interfaces for system architects, developers, and reviewers.

### 1.2 Document Conventions
* **Shall / Must**: Mandatory requirement.
* **Should**: Recommended feature.
* **May**: Optional or future phase enhancement.
* Requirement IDs follow the pattern `[FR-XX]` for Functional Requirements and `[NFR-XX]` for Non-Functional Requirements.

### 1.3 Intended Audience & Reading Suggestions
* **Software Developers & Engineers**: For API contract compliance, database schema integrity, and middleware verification.
* **Project Evaluators & Architects**: For system boundaries, security models, and compliance with enterprise standards.
* **QA & Test Teams**: For test-case authoring, boundary testing, and end-to-end verification.

### 1.4 Project Scope
SIMS is a centralized web platform engineered to eliminate manual inventory reconciliations, supply bottlenecks, and unauthorized stock manipulation. It features multi-role governance (Owner, Manager, Employee, Supplier), automated stock tracking, purchase order lifecycles, real-time KPI dashboards, audit logging, and automated disaster recovery exports.

### 1.5 References
* IEEE Standard 830-1998: *Recommended Practice for Software Requirements Specifications*.
* RFC 7519: *JSON Web Token (JWT)*.
* PostgreSQL 15 Documentation: *Relational Database Architecture & Indexing*.

---

## 2. Overall Description

### 2.1 Product Perspective
SIMS operates as a modular, 3-tier client-server architecture:
```
[Client Web Browser] <--> [Flask REST API (WSGI)] <--> [PostgreSQL Relational DB]
```
The system operates independently with decoupled Blueprint controllers, isolated business services, and database snapshot storage on local disk.

### 2.2 Product Functions
* Authenticate users using JWT tokens with automated account state validation.
* Maintain categorized product catalogs with SKU, cost, selling price, and reorder levels.
* Track inventory quantities, triggers for low stock ($\le 10$ units), and historical movements.
* Coordinate supplier quotations, purchase orders (Created $\rightarrow$ Received $\rightarrow$ Completed), and line items.
* Deliver tailored dashboard metrics for operational staff and external suppliers.
* Enforce gated reporting synchronized with background inventory readiness status.
* Audit database mutations and capture point-in-time JSON database backups.

### 2.3 User Classes and Characteristics

| Role | Role ID | Description & Responsibilities |
| :--- | :---: | :--- |
| **Owner** | `1` | Executive administrator with unrestricted access: user onboarding, role management, audit log inspection, and disaster recovery execution. |
| **Manager** | `2` | Operations lead: catalog item maintenance, supplier onboarding, quotation review, and purchase order creation. |
| **Employee** | `3` | Warehouse staff: stock status monitoring, stock-in/stock-out logging, receiving shipment validation, and employee dashboard access. |
| **Supplier** | `4` | External supply partner: submitting quotations, reviewing purchase orders, and supplier dashboard tracking. |

### 2.4 Operating Environment
* **Server OS**: Windows Server / Linux Ubuntu 22.04 LTS.
* **Runtime**: Python 3.10+ (WSGI compliant).
* **Database**: PostgreSQL 14+.
* **Client Browsers**: Google Chrome 100+, Mozilla Firefox 100+, Microsoft Edge 100+, Safari 15+.

### 2.5 Design and Implementation Constraints
* **Decoupling**: HTTP route handlers must not invoke SQL queries directly; all transactions must pass through the `services/` layer.
* **Statelessness**: Server sessions are strictly stateless, authenticated solely via cryptographically signed JWT tokens.
* **Driver**: Database access must utilize standard parameterized drivers (`psycopg2`) to prevent SQL injection vulnerabilities.

---

## 3. System Features & Functional Requirements

### 3.1 Authentication & Role-Based Access Control (RBAC)
* **[FR-01.1] User Authentication**: The system shall validate submitted usernames and passwords against stored one-way hashes (`generate_password_hash` / `check_password_hash`).
* **[FR-01.2] JWT Issuance**: Upon successful authentication, the system shall issue a signed JWT containing `user_id` identity and `role` claims.
* **[FR-01.3] Active Status Guard**: On every protected route, `verify_active_user()` shall confirm the user's status is `Active` in the database. Inactive users must receive an immediate `403 Forbidden`.
* **[FR-01.4] Password Governance**: Password updates must enforce a minimum length of 8 characters and require verification of the existing password.
* **[FR-01.5] User State Toggling**: The system shall allow Owners to toggle user status between `Active` and `Inactive`.

### 3.2 Master Catalog & Inventory Management
* **[FR-02.1] Category Management**: The system shall support CRUD operations for product categories (`category_name`, `description`).
* **[FR-02.2] Product Catalog**: Products shall record `product_name`, `category_id`, `sku`, `selling_price`, `reorder_level`, and `status`.
* **[FR-02.3] Low-Stock Alerts**: The system shall flag any inventory record where `quantity_available <= 10` as `LOW STOCK` in dashboards and reports.
* **[FR-02.4] Stock Recalculation**: Recording a `STOCK_IN` or `STOCK_OUT` transaction must adjust `Inventory.quantity_available` and update `last_updated`.

### 3.3 Supplier Procurement & Order Lifecycle
* **[FR-03.1] Supplier Directory**: The system shall maintain supplier records (`supplier_name`, `contact_person`, `phone`, `email`, `status`).
* **[FR-03.2] Supplier Quotations**: Suppliers may submit quotations (`quoted_price`, `quantity`, `valid_until`) with statuses (`Pending`, `Approved`, `Rejected`).
* **[FR-03.3] Purchase Order Lifecycle**: Purchase orders shall track total amounts and transition through `Created` $\rightarrow$ `Received` $\rightarrow$ `Completed`.
* **[FR-03.4] Multi-Item Line Support**: PO items shall record `product_id`, `quantity`, `unit_price`, and auto-calculate `subtotal`.

### 3.4 Operational Telemetry & Reporting Engine
* **[FR-04.1] Employee Dashboard**: Shall provide metrics for total products, total stock units, stock-in aggregate, stock-out aggregate, and low-stock item list.
* **[FR-04.2] Supplier Dashboard**: Shall display total purchase orders, completed orders, pending quotations, and total order volume.
* **[FR-04.3] Gated Inventory Report Generation**: When generating inventory reports, the system shall query `SystemStatus` for module `'Inventory'`. If the status is not `'READY'`, the system shall block report generation with `423 Locked`.
* **[FR-04.4] Notification Dispatch**: The system shall log notifications with read status (`is_read`), allowing users to mark alerts as read via `PATCH`.

### 3.5 System Auditing & Disaster Recovery
* **[FR-05.1] Security Audit Logging**: Mutations across key tables must record `action` (INSERT/UPDATE/DELETE), `table_name`, `record_id`, `user_id`, `ip_address`, and `action_time`.
* **[FR-05.2] Automated Database Backup**: On request, the system shall query PostgreSQL's `information_schema.tables`, export all records from every public table to an indented JSON snapshot file under `backend/backups/`, and record metadata in `BackupHistory`.

---

## 4. External Interface Requirements

### 4.1 User Interfaces
* Modern, responsive interface built with HTML5, CSS3, and JavaScript.
* Visual status badges for inventory health (`IN STOCK` vs `LOW STOCK`).
* Tabular views for audit logs and report downloads.

### 4.2 Software Interfaces
* **PostgreSQL Database**: Accessed through `psycopg2` using connection strings configured in `.env`.
* **JWT Engine**: Powered by `Flask-JWT-Extended` with HMAC-SHA256 signature verification.

### 4.3 Communications Interfaces
* REST over HTTP/HTTPS.
* JSON payload serialization and deserialization for all API requests and responses.

---

## 5. Non-Functional Requirements (NFRs)

### 5.1 Performance Requirements
* **[NFR-01] API Response Time**: Dashboard and telemetry queries shall respond in $\le 250\text{ ms}$ under normal database conditions.
* **[NFR-02] Backup Efficiency**: Complete database snapshot export shall complete in $\le 3\text{ seconds}$ for databases under 50,000 records.

### 5.2 Safety & Security Requirements
* **[NFR-03] Credential Security**: Passwords must never be stored in plaintext; hashing must use modern cryptographic salt algorithms (`pbkdf2:sha256` or `scrypt`).
* **[NFR-04] Authorization Boundary**: Access tokens must be verified against current database status to prevent revoked/inactive users from accessing cached sessions.
* **[NFR-05] SQL Injection Prevention**: Dynamic SQL formatting must use `psycopg2.sql` identifiers and parameterized query placeholders (`%s`).

### 5.3 Software Quality Attributes
* **Reliability**: Gated reporting protects consumers from processing partial or corrupted inventory calculations.
* **Maintainability**: Clear separation across `routes/`, `services/`, and `middleware/` allows modular team contributions without merge conflicts.
* **Recoverability**: Automated point-in-time JSON exports enable zero-data-loss rollback.

---

## 6. Requirements Traceability Matrix

| Requirement ID | Module / Feature Area | Target Component | Verifying Test / Route |
| :--- | :--- | :--- | :--- |
| **FR-01.1 - FR-01.5** | Authentication & RBAC | `middleware/team1_auth.py`, `services/team1/auth_service.py` | `POST /api/auth/login`, `PUT /api/auth/change-password` |
| **FR-02.1 - FR-02.4** | Catalog & Stock | `services/team1/category_service.py`, `routes/team1/categories.py` | `GET/POST /api/categories/` |
| **FR-03.1 - FR-03.4** | Procurement & Logistics | `backend/app/routes/team2/`, `services/team2/` | `POST /api/purchase-orders/`, `POST /api/transactions/` |
| **FR-04.1 - FR-04.4** | Telemetry & Reports | `services/team3/dashboard_service.py`, `routes/team3/reports.py` | `GET /api/dashboard/*`, `POST /api/reports/generate` |
| **FR-05.1 - FR-05.2** | Audits & Backups | `routes/team3/audit_logs.py`, `routes/team3/backups.py` | `GET /api/audit-logs/`, `POST /api/backups/` |
| **NFR-01 - NFR-05** | Security & Performance | `app/config.py`, `app/extensions.py`, `middleware/` | Continuous integration & security benchmarks |

