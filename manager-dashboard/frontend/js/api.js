/**
 * SMART INVENTORY MANAGEMENT SYSTEM - MANAGER DASHBOARD
 * API Client Module (Team 2)
 * Connects frontend directly to the standalone Flask REST API.
 */

// Detect whether we are running standalone or integrated
const API_BASE_URL = window.location.port === "5001" 
  ? "/api/manager/dashboard" 
  : "http://127.0.0.1:5001/api/manager/dashboard";

/**
 * Universal authenticated fetch wrapper
 */
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem("sims_access_token") || sessionStorage.getItem("sims_access_token");
  
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.message || result.error || `HTTP error ${response.status}`);
    }

    return result;
  } catch (err) {
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

export const DashboardAPI = {
  // Health check
  getHealth: () => apiFetch("/health"),

  // 1. Summary Cards
  getSummary: () => apiFetch("/summary"),

  // 2. Inventory Overview
  getInventoryOverview: () => apiFetch("/inventory-overview"),

  // 3. Procurement Funnel Overview
  getProcurementOverview: () => apiFetch("/procurement-overview"),

  // 4. Pending Actions Priority List
  getPendingActions: () => apiFetch("/pending-actions"),

  // 5. Low Stock Products
  getLowStock: () => apiFetch("/low-stock"),

  // 6. Recent Purchase Orders
  getRecentPurchaseOrders: (limit = 8) => apiFetch(`/recent-purchase-orders?limit=${limit}`),

  // 7. Recent Stock Transactions
  getRecentTransactions: (limit = 8) => apiFetch(`/recent-transactions?limit=${limit}`),

  // 8. Employee Overview
  getEmployees: () => apiFetch("/employees"),

  // 9. Supplier Overview
  getSuppliers: () => apiFetch("/suppliers"),

  // 10. Notifications
  getNotifications: (limit = 10) => apiFetch(`/notifications?limit=${limit}`),
  markNotificationRead: (id) => apiFetch(`/notifications/${id}/read`, { method: "PATCH" })
};
