# Smart Inventory Management System (SIMS) - UML & Architectural Diagrams

This document contains visual architectural specifications and models for SIMS using standard **Mermaid** syntax, supported directly in GitHub, Markdown viewers, and documentation tools.

---

## 1. Entity-Relationship Diagram (ERD) - 15 Tables

```mermaid
erDiagram
    Roles ||--o{ Users : "assigns"
    Users ||--o{ StockTransactions : "executes"
    Users ||--o{ PurchaseOrders : "creates"
    Users ||--o{ Reports : "generates"
    Users ||--o{ Notifications : "receives"
    Users ||--o{ AuditLogs : "triggers"
    Users ||--o{ BackupHistory : "initiates"

    Categories ||--o{ Products : "classifies"
    Products ||--|| Inventory : "tracks_stock"
    Products ||--o{ StockTransactions : "involves"
    Products ||--o{ PurchaseOrderItems : "contains"
    Products ||--o{ SupplierQuotations : "quotes"

    Suppliers ||--o{ SupplierQuotations : "submits"
    Suppliers ||--o{ PurchaseOrders : "receives"

    PurchaseOrders ||--o{ PurchaseOrderItems : "includes"
    PurchaseOrders ||--o{ StockTransactions : "relates_to"

    Roles {
        int role_id PK
        string role_name
        string description
    }

    Users {
        int user_id PK
        string username
        string email
        string password_hash
        int role_id FK
        string status
    }

    Categories {
        int category_id PK
        string category_name
        string description
    }

    Products {
        int product_id PK
        string product_name
        int category_id FK
        string sku
        decimal selling_price
        int reorder_level
        string status
    }

    Inventory {
        int inventory_id PK
        int product_id FK
        int quantity_available
        datetime last_updated
    }

    StockTransactions {
        int transaction_id PK
        int product_id FK
        int user_id FK
        int purchase_order_id FK
        string transaction_type
        int quantity
        datetime transaction_date
    }

    Suppliers {
        int supplier_id PK
        string supplier_name
        string contact_person
        string phone
        string email
        string status
    }

    SupplierQuotations {
        int quotation_id PK
        int supplier_id FK
        int product_id FK
        datetime quotation_date
        decimal quoted_price
        int quantity
        date valid_until
        string status
    }

    PurchaseOrders {
        int purchase_order_id PK
        int supplier_id FK
        int ordered_by FK
        datetime order_date
        date expected_delivery
        decimal total_amount
        string status
    }

    PurchaseOrderItems {
        int purchase_order_item_id PK
        int purchase_order_id FK
        int product_id FK
        int quantity
        decimal unit_price
        decimal subtotal
    }

    SystemStatus {
        int status_id PK
        string module_name
        string status
        int progress
        string message
        datetime updated_at
    }

    Reports {
        int report_id PK
        string report_name
        string report_type
        int generated_by FK
        datetime generated_on
    }

    Notifications {
        int notification_id PK
        int user_id FK
        string title
        string message
        string notification_type
        boolean is_read
        datetime created_at
    }

    AuditLogs {
        int log_id PK
        int user_id FK
        string action
        string table_name
        int record_id
        datetime action_time
        string ip_address
    }

    BackupHistory {
        int backup_id PK
        string backup_name
        string backup_type
        string backup_size
        int created_by FK
        string status
        datetime backup_date
    }
```

---

## 2. System Use Case Diagram

```mermaid
flowchart LR
    subgraph Actors
        Owner["👤 Owner"]
        Manager["👤 Manager"]
        Employee["👤 Employee"]
        Supplier["👤 Supplier"]
    end

    subgraph SIMS["Smart Inventory Management System"]
        UC1(["User Onboarding & Status Management"])
        UC2(["Audit Log Inspection"])
        UC3(["Database Snapshot Backup & Recovery"])
        UC4(["Category & Catalog Management"])
        UC5(["Supplier Directory & Quotation Approval"])
        UC6(["Purchase Order Creation"])
        UC7(["Stock In / Stock Out Entry"])
        UC8(["Employee Dashboard & Stock Checks"])
        UC9(["Gated Inventory Report Generation"])
        UC10(["Supplier Quotation Bidding"])
        UC11(["Supplier Dashboard & Order Tracking"])
        UC12(["System Notifications & Alerts"])
    end

    Owner --> UC1
    Owner --> UC2
    Owner --> UC3
    Owner --> UC9

    Manager --> UC4
    Manager --> UC5
    Manager --> UC6
    Manager --> UC9
    Manager --> UC12

    Employee --> UC7
    Employee --> UC8
    Employee --> UC12

    Supplier --> UC10
    Supplier --> UC11
    Supplier --> UC12
```

---

## 3. High-Level Component & Tier Architecture

```mermaid
flowchart TD
    subgraph PresentationTier["Presentation Layer (Client)"]
        UI_Login["Login & Profile Page"]
        UI_Dash["Role Dashboards (Employee / Supplier)"]
        UI_Catalog["Product & Category Management"]
        UI_Procure["PO & Supplier Views"]
        UI_Reports["Reports & Backups Portal"]
    end

    subgraph SecurityLayer["Security & RBAC Middleware"]
        JWT_Filter["JWT Token Verification"]
        Active_Check["verify_active_user()"]
        Role_Guard["@role_required(Owner, Manager, ...)"]
    end

    subgraph BackendTier["Application Layer (Flask Blueprints & Services)"]
        subgraph Team1["Team 1: Foundation"]
            Auth_BP["routes/team1/auth.py"]
            User_BP["routes/team1/users.py"]
            Cat_BP["routes/team1/categories.py"]
            Auth_Svc["services/team1/auth_service.py"]
            User_Svc["services/team1/user_service.py"]
            Cat_Svc["services/team1/category_service.py"]
        end

        subgraph Team2["Team 2: Procurement"]
            Supp_BP["routes/team2/suppliers.py"]
            PO_BP["routes/team2/purchase_orders.py"]
            Trans_BP["routes/team2/transactions.py"]
        end

        subgraph Team3["Team 3: Telemetry & Operations"]
            Dash_BP["routes/team3/dashboard.py"]
            Rep_BP["routes/team3/reports.py"]
            Notif_BP["routes/team3/notifications.py"]
            Audit_BP["routes/team3/audit_logs.py"]
            Back_BP["routes/team3/backups.py"]
            Dash_Svc["services/team3/dashboard_service.py"]
        end
    end

    subgraph PersistenceTier["Data Layer (PostgreSQL Database)"]
        DB[(PostgreSQL Database)]
        JSON_Backups["backend/backups/*.json Snapshots"]
    end

    PresentationTier --> SecurityLayer
    SecurityLayer --> BackendTier
    Team1 --> DB
    Team2 --> DB
    Team3 --> DB
    Back_BP --> JSON_Backups
```

---

## 4. Sequence Diagram: Authentication & Role Verification Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant AuthRoute as routes/team1/auth.py
    participant AuthSvc as services/team1/auth_service.py
    participant Middleware as middleware/team1_auth.py
    participant DB as PostgreSQL ("Users", "Roles")

    User->>AuthRoute: POST /api/auth/login (username, password)
    AuthRoute->>AuthSvc: login_user(username, password)
    AuthSvc->>DB: SELECT password_hash, role_name, status WHERE username = %s
    DB-->>AuthSvc: Return user record
    
    alt User Inactive
        AuthSvc-->>AuthRoute: Error: "User account is inactive"
        AuthRoute-->>User: HTTP 403 Forbidden
    else Invalid Password
        AuthSvc-->>AuthRoute: Error: "Invalid credentials"
        AuthRoute-->>User: HTTP 401 Unauthorized
    else Valid Credentials
        AuthSvc->>AuthSvc: create_access_token(identity=user_id, claims={"role": role_name})
        AuthSvc-->>AuthRoute: Access Token & User details
        AuthRoute-->>User: HTTP 200 OK (access_token, user)
    end

    Note over User, DB: Subsequent Protected Request
    User->>AuthRoute: GET /api/users/ (Bearer JWT Token)
    AuthRoute->>Middleware: @role_required("Owner", "Manager")
    Middleware->>DB: verify_active_user()
    DB-->>Middleware: status = 'Active'
    Middleware->>Middleware: Validate role claim
    Middleware->>AuthRoute: Proceed to handler
    AuthRoute-->>User: HTTP 200 OK (User list)
```

---

## 5. Sequence Diagram: Gated Inventory Report Generation

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Manager
    participant ReportRoute as routes/team3/reports.py
    participant DB as PostgreSQL

    Client->>ReportRoute: POST /api/reports/generate (report_name, report_type="Inventory", generated_by)
    ReportRoute->>DB: SELECT status, progress, message FROM "SystemStatus" WHERE module_name = 'Inventory'
    DB-->>ReportRoute: Return status row

    alt Status != "READY" (e.g. "LOADING" or "REFRESHING")
        ReportRoute-->>Client: HTTP 423 Locked (error="Report generation locked", progress)
    else Status == "READY"
        ReportRoute->>DB: SELECT p.product_id, p.product_name, p.sku, i.quantity_available, p.reorder_level FROM Products p JOIN Inventory i
        DB-->>ReportRoute: Return inventory records
        ReportRoute->>ReportRoute: Calculate stock_status ("LOW STOCK" if qty <= reorder_level)
        ReportRoute->>DB: INSERT INTO "Reports" (...) RETURNING report_id, generated_on
        DB-->>ReportRoute: Report metadata
        ReportRoute-->>Client: HTTP 201 Created (report metadata + aggregated report data)
    end
```

---

## 6. Sequence Diagram: Automated Full Database Backup

```mermaid
sequenceDiagram
    autonumber
    actor Admin as System Owner
    participant BackupRoute as routes/team3/backups.py
    participant DB as PostgreSQL
    participant FileSystem as Local Disk (backend/backups/)

    Admin->>BackupRoute: POST /api/backups/ (created_by: 1)
    BackupRoute->>DB: Verify user_id exists in "Users"
    DB-->>BackupRoute: User valid
    BackupRoute->>DB: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
    DB-->>BackupRoute: Returns 15 table names

    loop For each table
        BackupRoute->>DB: SELECT * FROM <table>
        DB-->>BackupRoute: Returns all rows & column descriptors
        BackupRoute->>BackupRoute: Serialize dates, datetimes, decimals to JSON-safe formats
    end

    BackupRoute->>FileSystem: Write JSON file `backend/backups/inventory_backup_<timestamp>.json`
    BackupRoute->>FileSystem: Calculate file size (KB / MB)
    BackupRoute->>DB: INSERT INTO "BackupHistory" (backup_name, backup_type, backup_size, created_by, status)
    DB-->>BackupRoute: Return backup_id, backup_date
    BackupRoute-->>Admin: HTTP 201 Created (backup metadata & file path)
```

