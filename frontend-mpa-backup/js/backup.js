// Page Behavior: Backup Center
document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.getElementById("backup-tbody");
  const createBtn = document.getElementById("btn-create-backup");

  async function loadBackups() {
    try {
      const data = await API.request("/api/backups/");
      if (data && tbody) {
        if (data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 16px;">No backups recorded.</td></tr>';
        } else {
          tbody.innerHTML = data.map(b => `
            <tr>
              <td>#${b.backup_id}</td>
              <td><strong>${b.backup_name}</strong></td>
              <td><span class="status-pill neutral">${b.backup_type}</span></td>
              <td>${b.backup_size}</td>
              <td>${b.created_by}</td>
              <td style="color: #64748b;">${b.backup_date}</td>
              <td><span class="status-pill success">${b.status}</span></td>
            </tr>
          `).join("");
        }
      }
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #b45309; padding: 16px;">Start backend at http://127.0.0.1:5000 to load backups.</td></tr>';
      }
    }
  }

  if (createBtn) {
    createBtn.addEventListener("click", async () => {
      try {
        const res = await API.request("/api/backups/", {
          method: "POST",
          body: JSON.stringify({ created_by: 1 })
        });
        alert("Backup created successfully: " + res.backup_name);
        loadBackups();
      } catch (err) {
        alert("Backup creation failed: " + err.message);
      }
    });
  }

  loadBackups();
});
