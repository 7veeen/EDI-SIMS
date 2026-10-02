// SIMS Shared Authentication Helpers
const Auth = {
  getUser() {
    try {
      return JSON.parse(localStorage.getItem("sims_user")) || null;
    } catch {
      return null;
    }
  },

  setUser(user) {
    localStorage.setItem("sims_user", JSON.stringify(user));
  },

  isAuthenticated() {
    return !!API.getToken();
  },

  async login(username, password) {
    const data = await API.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
    if (data && data.access_token) {
      API.setToken(data.access_token);
      if (data.user) this.setUser(data.user);
      return data;
    }
    throw new Error("Authentication failed");
  },

  logout() {
    API.removeToken();
    localStorage.removeItem("sims_user");
    // Redirect to index or login
    const isPagesDir = window.location.pathname.includes("/pages/");
    window.location.href = isPagesDir ? "../index.html" : "index.html";
  }
};

