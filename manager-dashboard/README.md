# Smart Inventory Management System (SIMS) - Manager Dashboard Module

**Developed by Team 2**

This is an isolated, production-ready, standalone **Manager Dashboard** module for the Smart Inventory Management System. It acts as an operational overview and action center for warehouse Managers, querying real data directly from Supabase PostgreSQL without using mock or hardcoded data.

---

## 1. Project Structure

```text
manager-dashboard/
├── backend/
│   ├── app.py                          # Flask application entrypoint (runs on port 5001)
│   ├── config.py                       # Configuration & environment variable loader
│   ├── extensions.py                   # PostgreSQL connection pool & schema utilities
│   ├── requirements.txt                # Python backend dependencies
│   ├── .env.example                    # Environment variable template
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth_middleware.py          # Manager/Owner JWT role authorization
│   ├── routes/
│   │   ├── __init__.py
│   │   └── manager_dashboard_routes.py # 10 REST API endpoints
│   └── services/
│       ├── __init__.py
│       └── manager_dashboard_service.py# Direct Supabase SQL query services
├── frontend/
│   ├── index.html                      # Manager Console UI
│   ├── css/
│   │   └── manager-dashboard.css       # Custom design system & responsive styling
│   └── js/
│       ├── api.js                      # Authenticated API client wrapper
│       └── manager-dashboard.js        # UI controller, charts & real-time sync
├── sql/
│   └── dashboard_queries.sql           # Documentation of all SQL queries used
└── README.md                           # Comprehensive documentation & integration guide
```

---

## 2. Environment Variables

Create `backend/.env` (or `manager-dashboard/backend/.env`) with the following values:

```env
# Supabase PostgreSQL Connection String
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Supabase Project API Credentials
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_KEY=your_supabase_key

# JWT Secret Key (matching Team 1 auth)
JWT_SECRET_KEY=smart-inventory-management-system-super-secret-jwt-key-2026

# Server Port
PORT=5001
FLASK_ENV=development
```

---

## 3. How to Run the Standalone Dashboard

### Step 1: Start Backend API
```bash
cd manager-dashboard/backend
python app.py
```
The backend will run at `http://127.0.0.1:5001`.
Health check: `http://127.0.0.1:5001/api/manager/dashboard/health`

### Step 2: Open Frontend
You can open `manager-dashboard/frontend/index.html` using:
- **VS Code Live Server** (right click `index.html` -> "Open with Live Server")
- Or standard Python HTTP server:
  ```bash
  cd manager-dashboard/frontend
  python -m http.server 8080
  ```
  Then visit `http://127.0.0.1:8080`.

---

## 4. REST API Endpoints Specification

All endpoints return JSON in the format:
```json
{
  "success": true,
  "data": { ... }
}
```

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/manager/dashboard/health` | Service & Supabase connectivity status |
| `GET` | `/api/manager/dashboard/summary` | 8 summary metric counts (products, low stock, out of stock, pending POs, etc.) |
| `GET` | `/api/manager/dashboard/inventory-overview` | Stock health breakdown (Available, Low Stock, Out of Stock, Category distribution) |
| `GET` | `/api/manager/dashboard/procurement-overview` | Pipeline funnel counts (Requests -> Quotations -> POs -> Delivered) |
| `GET` | `/api/manager/dashboard/pending-actions` | Prioritized tasks requiring Manager action |
| `GET` | `/api/manager/dashboard/low-stock` | Products where `quantity_available <= reorder_level` |
| `GET` | `/api/manager/dashboard/recent-purchase-orders` | Recent POs with supplier, amount, status, date |
| `GET` | `/api/manager/dashboard/recent-transactions` | Recent stock movements (Stock-In / Stock-Out) |
| `GET` | `/api/manager/dashboard/employees` | Active employees and roster preview |
| `GET` | `/api/manager/dashboard/suppliers` | Active suppliers count and directory |
| `GET` | `/api/manager/dashboard/notifications` | Manager alerts and unread counts |
| `PATCH` | `/api/manager/dashboard/notifications/<id>/read` | Mark specific notification as read |

---

## 5. Database Tables & Schema Compatibility

The module executes pure SQL queries against the following existing tables:
- `public."Users"`
- `public."Roles"`
- `public."Categories"`
- `public."Products"`
- `public."Inventory"`
- `public."StockTransactions"`
- `public."PurchaseOrders"`
- `public."SupplierQuotations"` (or `Quotations`)
- `public."StockRequests"`
- `public."Suppliers"`
- `public."Notifications"`

> **Strict No-Mock-Data Policy**: If any table has zero records, the API returns `0` or `[]` and the frontend presents clean empty states ("No products found", "No low stock items", etc.).

---

## 6. Integration Instructions for the Main Project

To integrate the Manager Dashboard into the main `backend/app/` in the future:
1. Copy `manager-dashboard/backend/routes/manager_dashboard_routes.py` to `backend/app/routes/team2/manager_dashboard.py`.
2. Copy `manager-dashboard/backend/services/manager_dashboard_service.py` to `backend/app/services/team2/manager_dashboard_service.py`.
3. In `backend/app/__init__.py`, register the blueprint:
   ```python
   from app.routes.team2.manager_dashboard import manager_dashboard_bp
   app.register_blueprint(manager_dashboard_bp)
   ```
4. Copy `manager-dashboard/frontend/` assets to `frontend/pages/manager-dashboard/`.

---

## 7. Testing Protocol

Run automated tests:
```bash
python -m py_compile manager-dashboard/backend/app.py
```
Check health check endpoint:
```bash
curl http://127.0.0.1:5001/api/manager/dashboard/health
```
