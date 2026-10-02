// SIMS REST API Client with Live Backend & Graceful Fallback
const API = {
  getBaseUrl() {
    return Store.settings.apiUrl || "http://127.0.0.1:5000";
  },

  getToken() {
    return localStorage.getItem("sims_jwt_token") || "";
  },

  setToken(token) {
    localStorage.setItem("sims_jwt_token", token);
  },

  async request(endpoint, options = {}) {
    const url = `${this.getBaseUrl()}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      console.warn(`[API] Live request to ${endpoint} failed (${err.message}). Using local store data.`);
      return null;
    }
  },

  // Auth
  async login(username, password) {
    const res = await this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
    if (res && res.access_token) {
      this.setToken(res.access_token);
      return res;
    }
    return null;
  },

  // Dashboard metrics
  async getEmployeeDashboard() {
    return await this.request("/api/dashboard/employee");
  },

  async getSupplierDashboard() {
    return await this.request("/api/dashboard/supplier");
  },

  // Reports
  async getReports() {
    const res = await this.request("/api/reports/");
    return res || Store.reports;
  },

  async getInventoryStatus() {
    const res = await this.request("/api/reports/status");
    return res || { status: "READY", progress: 100, message: "Inventory cache synchronized and ready for reports." };
  },

  async generateReport(reportName, reportType = "Inventory", generatedBy = 1) {
    const res = await this.request("/api/reports/generate", {
      method: "POST",
      body: JSON.stringify({ report_name: reportName, report_type: reportType, generated_by: generatedBy })
    });
    return res;
  },

  // Backups
  async getBackups() {
    const res = await this.request("/api/backups/");
    return res || Store.backups;
  },

  async createBackup(createdBy = 1) {
    const res = await this.request("/api/backups/", {
      method: "POST",
      body: JSON.stringify({ created_by: createdBy })
    });
    return res;
  },

  // Notifications
  async getNotifications() {
    const res = await this.request("/api/notifications/");
    return res || Store.notifications;
  },

  // Audit logs
  async getAuditLogs() {
    const res = await this.request("/api/audit-logs/");
    return res || Store.auditLogs;
  },

  // Categories
  async getCategories() {
    const res = await this.request("/api/categories/");
    return res || Store.categories;
  },

  // Users
  async getUsers() {
    const res = await this.request("/api/users/");
    return res || Store.users;
  }
};

