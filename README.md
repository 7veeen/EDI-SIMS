Smart Inventory Management System

A web-based inventory management system developed as part of the Engineering Design and Innovation (EDI) project.

Features

* User Authentication
* Role-Based Access Control
* Product and Category Management
* Inventory Management
* Supplier Management
* Purchase Orders and Quotations
* Stock Transactions
* Notifications
* Dashboards and Reports
* Audit Logs
* Backup Management

Tech Stack

* Frontend: HTML, CSS, JavaScript
* Backend: Python, Flask
* Database: Supabase PostgreSQL
* Authentication: JWT
* Version Control: Git and GitHub

System Flow

```text
User
  |
  v
Authentication
  |
  v
Role
 /  \
v    v
Employee    Supplier
  |            |
  |            +--> Purchase Orders
  |            |
  |            +--> Quotations
  |
  +--> Inventory
  +--> Dashboard
  +--> Notifications
  +--> Reports
           |
           v
    Supabase PostgreSQL
```

Project Structure

```text
Smart Inventory Management System/
|
+-- frontend/
|
+-- backend/
|   +-- app/
|   |   +-- routes/
|   |   +-- services/
|   |
|   +-- backups/
|   +-- run.py
|
+-- README.md
```

Setup

Clone the repository:

```bash
git clone https://github.com/mrugadni-29/SIMS.git
cd SIMS
```

Backend:

Create a `backend/.env` file with the required database and JWT configuration.

```bash
cd backend
python run.py
```

Backend runs on:

```text
http://127.0.0.1:5000
```

Frontend:

Open the `frontend` folder in VS Code and run `index.html` using Live Server.

Team Contributions

Team 1 — Authentication and Core Inventory

Team 2 — Suppliers, Purchases and Stock Transactions

Team 3 — Dashboards, Reports and System Management

Status

Academic project developed as part of the Engineering Design and Innovation (EDI) course.
