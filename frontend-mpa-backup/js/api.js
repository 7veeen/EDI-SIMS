// SIMS Shared API Client
const API = {
  baseUrl: "http://127.0.0.1:5000",

  getToken() {
    return localStorage.getItem("sims_access_token") || "";
  },

  setToken(token) {
    localStorage.setItem("sims_access_token", token);
  },

  removeToken() {
    localStorage.removeItem("sims_access_token");
  },

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      console.warn(`[API] ${endpoint} request error:`, err.message);
      throw err;
    }
  }
};

