// Page Behavior: Categories
document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.getElementById("categories-tbody");

  async function loadCategories() {
    try {
      const data = await API.request("/api/categories/");
      if (data && tbody) {
        if (data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 16px;">No categories found.</td></tr>';
        } else {
          tbody.innerHTML = data.map(c => `
            <tr>
              <td>#${c.category_id}</td>
              <td><strong>${c.category_name}</strong></td>
              <td style="color: #64748b;">${c.description || "N/A"}</td>
            </tr>
          `).join("");
        }
      }
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #b45309; padding: 16px;">Start backend at http://127.0.0.1:5000 to load live categories.</td></tr>';
      }
    }
  }

  loadCategories();
});
