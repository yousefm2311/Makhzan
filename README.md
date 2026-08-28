<div align="right">
<a href="README-AR.md"><strong>🌐 عرض باللغة العربية</strong></a>
</div>

<div align="center">
  <img src="Makhzan/static/images/logo.png" alt="Makhzan Logo" width="120" onerror="this.style.display='none'" />

  # Makhzan - Integrated WMS & ERP System

  **An enterprise-grade, fully integrated Warehouse Management System (WMS), Point of Sale (POS), and Inventory Tracking platform featuring granular RBAC permissions, E-Signatures, and Electron Desktop support.**

  [![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
  [![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
  [![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
  [![Electron](https://img.shields.io/badge/Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)](https://www.electronjs.org/)
</div>

---

## 📖 Overview

**Makhzan** is a comprehensive software solution designed for companies, warehouses, and retail stores to maintain absolute control over their supply chain and inventory. It bridges the gap between complex ERPs and simple spreadsheet tracking by providing a robust, document-driven workflow.

Whether you are managing multi-branch company assets, tracking employee custodial items (العهد), performing routine physical stocktakes, or running a retail Point of Sale (POS) counter, Makhzan adapts to your operational mode.

---

## ✨ Comprehensive Feature Set

### 📦 1. Advanced Inventory Management
*   **Multi-Location Storage:** Track stock across different physical branches, zones, and storage bins.
*   **Physical Stocktakes (الجرد):** Create draft stocktake sessions, input counted quantities, automatically calculate variances, and route the count sheet for managerial approval.
*   **Damage Control:** Log damaged items with automated deduction from active inventory and tracking of employee responsibility.
*   **Stock Adjustments & Transfers:** Comprehensive logging of all manual stock corrections.

### 👥 2. Corporate Assets & Employee Tracking (العهد)
*   **Custodial Issue Requests:** Employees can request equipment or materials. The workflow mandates dual-layer approval (Requester -> Approver -> Warehouse Execution).
*   **Electronic Signatures:** Secure the chain of custody. Approving or executing a stock issue requires the user to input their password, stamping the document with a verifiable E-Signature and timestamp.
*   **Custodial Returns:** Log the return of items from employees, noting the condition of the returned item (Usable, Damaged).

### 🛒 3. Procurement & Point of Sale (POS)
*   **Supplier Purchases:** Generate purchase invoices, track total amounts, log partial payments, and monitor due dates for outstanding balances (majel).
*   **Retail Sales (POS):** Fast-checkout interface for retail customers. Supports partial payments, outstanding balances, and direct deduction from live inventory.
*   **Corporate Mode Toggle:** The system can intelligently hide retail/POS interfaces for internal corporate environments.

### 🔐 4. Granular RBAC (Role-Based Access Control)
*   **Standard Roles:** Preconfigured roles including `Admin`, `Warehouse Manager`, `Approver`, `Auditor`, `Requester`, and `Cashier`.
*   **Custom View & Action Scopes:** Permissions are divided into specific actions (e.g., `products.view`, `issue_requests.approve`). An Admin can selectively grant granular permissions to specific users, overriding their base role.
*   **Branch-Restricted Access:** Users and employees can be locked to specific branches, ensuring they only view and interact with local inventory.

### 📊 5. Automated Reporting & Auditing
*   **Audit Trail:** Every insert, update, and delete operation is logged in the `AuditLog` table with the User ID, IP Address, Timestamp, and context.
*   **Rich PDF Exports:** Fully stylized PDF reports utilizing `ReportLab` with complete Bi-Directional (RTL) Arabic font support. 
*   **Excel Exports:** Data-heavy tables are exportable to `.xlsx` using `OpenPyXL` for offline financial analysis.

---

## 🏗 Architecture & Tech Stack

Makhzan is built on a decoupled mindset within a monolithic architecture, ensuring rapid deployment and extreme portability.

*   **Backend Framework:** Python 3.8+ / Flask
*   **Database:** SQLite via SQLAlchemy ORM (Configured with connection timeouts and busy-handlers to support concurrent reads/writes).
*   **Database Migrations:** Alembic / Flask-Migrate
*   **Frontend UI:** Jinja2 Templating, Bootstrap 5, Custom CSS (Includes Native Dark/Light Mode toggle).
*   **Desktop Wrapper:** Electron.js (Spawns a hidden Node.js child process to run the Python Flask server, then renders the `localhost` instance in a Chromium window).

### 📂 Directory Structure

```text
Makhzan/
├── Makhzan/                  # Core Flask Application
│   ├── app.py                # App factory, Configuration, core routes, and utilities
│   ├── models.py             # SQLAlchemy Database Schema (20+ relational tables)
│   ├── routes.py             # HTTP endpoints and view controllers
│   ├── forms.py              # Flask-WTF Form classes and validation logic
│   ├── static/               # Assets (CSS, JS, Images, Fonts)
│   └── templates/            # Jinja2 HTML templates organized by module
├── desktop/                  # Electron Desktop Wrapper
│   ├── main.js               # Electron lifecycle & Python sub-process manager
│   ├── preload.js            # Secure IPC bridge
│   └── package.json          # Node dependencies and build scripts
├── migrations/               # Alembic version control for database schema
├── requirements.txt          # Python dependencies
├── README.md                 # English Documentation
└── README-AR.md              # Arabic Documentation
```

---

## 🗄️ Database Schema Highlights

The system relies on a highly relational SQLite schema. Key entities include:
*   `User`, `Employee`, `Branch`: Organizational structure.
*   `Product`, `Category`, `Inventory`, `StorageLocation`: Core inventory definition.
*   `Purchase`, `PurchaseItem`, `Supplier`: Inbound supply chain.
*   `Sale`, `SaleItem`, `Customer`: Outbound retail chain.
*   `StockIssueRequest`, `StockIssue`, `EmployeeReturn`, `DamageRecord`: Internal asset tracking and workflows.
*   `InventoryTransaction`: The immutable ledger recording the Delta (`quantity_change`) of every movement.

---

## 🚀 Getting Started

### 📋 Prerequisites
*   **Python 3.8+**
*   **Node.js & npm** (Required only for the Desktop App)

### 🌐 1. Running as a Web Server (Standard)

1. **Clone & Navigate**
   ```bash
   git clone https://github.com/your-username/makhzan.git
   cd makhzan
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Server**
   ```bash
   cd Makhzan
   flask run --host=0.0.0.0 --port=5000
   ```
   > **Note:** On first boot, the system auto-generates `instance/makhzan.db` and injects a default admin account *(Username: admin, Password: admin123)*.

### 🖥️ 2. Running as a Desktop Application (Electron)

If you prefer a standalone executable experience without dealing with browser tabs:

1. Ensure Python dependencies are installed globally or in the virtual environment as shown above.
2. Open a terminal in the `desktop` directory:
   ```bash
   cd desktop
   npm install
   ```
3. Start the Electron wrapper:
   ```bash
   npm start
   ```
   *This command uses `concurrently` to boot the Python Flask server in the background and waits for port 5000 to become active before launching the native Desktop Window.*

---

## 🛡️ Security & Workflow Notes

*   **E-Signature Requirement:** When testing the `Issue Requests` approval flow, the system will prompt the logged-in user to re-enter their password. This generates an encrypted signature string stored directly on the database row.
*   **Locked DB Handling:** Because SQLite locks the database during writes, `app.py` implements a custom `commit_with_retry` function with linear backoff, ensuring multi-user environments do not experience crashing during concurrent checkouts.
*   **Data Integrity:** Inventory quantities are derived dynamically but cached in the `Inventory` table. The `InventoryTransaction` ledger acts as the ultimate source of truth for audits.

---

## 📄 License
This project is proprietary and was developed as a comprehensive WMS solution. All rights reserved.
