// Page Behavior: Users & Roles
document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.getElementById("users-tbody");

  async function loadUsers() {
    try {
      const data = await API.request("/api/users/");
      if (data && tbody) {
        if (data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 16px;">No users found.</td></tr>';
        } else {
          tbody.innerHTML = data.map(u => `
            <tr>
              <td>#${u.user_id}</td>
              <td><strong>${u.username}</strong></td>
              <td>${u.email}</td>
              <td><span class="status-pill neutral">${u.role_name || u.role || 'User'}</span></td>
              <td><span class="status-pill ${u.status === 'Active' ? 'success' : 'danger'}">${u.status}</span></td>
            </tr>
          `).join("");
        }
      }
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #b45309; padding: 16px;">Start backend at http://127.0.0.1:5000 to load users.</td></tr>';
      }
    }
  }

  loadUsers();
});
