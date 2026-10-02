// View: Inventory Section (Inventory, Products, Categories)
const InventoryView = {
  // 1. Inventory View
  renderInventory() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Inventory Stock Levels</h2>
              <p>Real-time physical stock counts across all warehouse bins</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.navigate('stock-transactions')">
                ${Icons.transactions} Stock In / Out
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search inventory by product or SKU..." oninput="App.filterTable(this, 'table-inventory')"/>
            </div>
            <span class="pagination-info">Total Units: <strong>${Store.inventory.reduce((a,b)=>a+Number(b.quantity_available),0)}</strong></span>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-inventory">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Available Quantity</th>
                  <th>Reorder Level</th>
                  <th>Stock Health</th>
                  <th>Last Sync</th>
                  <th style="text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${Store.inventory.map(item => {
                  const isLow = Number(item.quantity_available) <= Number(item.reorder_level);
                  return `
                    <tr>
                      <td><input type="checkbox" class="table-checkbox" /></td>
                      <td>
                        <div class="entity-cell">
                          <div class="entity-icon-avatar">${item.product_name.charAt(0)}</div>
                          <div>
                            <div class="entity-name">${item.product_name}</div>
                            <div class="entity-sub">ID: #${item.product_id}</div>
                          </div>
                        </div>
                      </td>
                      <td><code>${item.sku}</code></td>
                      <td><strong style="font-size: 15px;">${item.quantity_available}</strong></td>
                      <td>${item.reorder_level}</td>
                      <td>
                        <span class="status-pill ${isLow ? 'lowstock' : 'instock'}">
                          ${isLow ? 'LOW STOCK' : 'IN STOCK'}
                        </span>
                      </td>
                      <td>${item.last_updated}</td>
                      <td style="text-align: right;">
                        <button class="action-icon-btn" title="Adjust Stock" onclick="App.openRestockModal(${item.product_id})">
                          ${Icons.edit}
                        </button>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.inventory.length} of ${Store.inventory.length} entries</div>
            <div class="pagination-controls">
              <button class="page-btn">${Icons.chevronLeft}</button>
              <button class="page-btn active">1</button>
              <button class="page-btn">${Icons.chevronRight}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  // 2. Products Catalog View
  renderProducts() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Product Catalog</h2>
              <p>Manage product items, category links, pricing, and safety reorder rules</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-add-product')">
                ${Icons.plus} Add New Product
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search products..." oninput="App.filterTable(this, 'table-products')"/>
            </div>
            <span class="pagination-info">Total Catalog: <strong>${Store.products.length} Products</strong></span>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-products">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Product Name</th>
                  <th>SKU</th>
                  <th>Category</th>
                  <th>Selling Price</th>
                  <th>Reorder Limit</th>
                  <th>Status</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${Store.products.map(p => `
                  <tr>
                    <td><input type="checkbox" class="table-checkbox" /></td>
                    <td>
                      <div class="entity-cell">
                        <div class="entity-icon-avatar">${p.product_name.charAt(0)}</div>
                        <div class="entity-name">${p.product_name}</div>
                      </div>
                    </td>
                    <td><code>${p.sku}</code></td>
                    <td><span class="status-pill role">${p.category_name}</span></td>
                    <td><strong>₹${Number(p.selling_price).toFixed(2)}</strong></td>
                    <td>${p.reorder_level}</td>
                    <td><span class="status-pill active">${p.status}</span></td>
                    <td style="text-align: right;">
                      <div class="table-actions" style="justify-content: flex-end;">
                        <button class="action-icon-btn" title="Edit Product">${Icons.edit}</button>
                        <button class="action-icon-btn danger" title="Delete" onclick="App.deleteProduct(${p.product_id})">${Icons.trash}</button>
                      </div>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.products.length} of ${Store.products.length} entries</div>
            <div class="pagination-controls">
              <button class="page-btn">${Icons.chevronLeft}</button>
              <button class="page-btn active">1</button>
              <button class="page-btn">${Icons.chevronRight}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  // 3. Categories View
  renderCategories() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Inventory Categories</h2>
              <p>Organize products into hierarchical classification groups</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-add-category')">
                ${Icons.plus} Add Category
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search categories..." oninput="App.filterTable(this, 'table-categories')"/>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-categories">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Category Name</th>
                  <th>Description</th>
                  <th>Linked Products</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${Store.categories.map(c => `
                  <tr>
                    <td><input type="checkbox" class="table-checkbox" /></td>
                    <td>
                      <div class="entity-cell">
                        <div class="entity-icon-avatar">${c.category_name.charAt(0)}</div>
                        <div class="entity-name">${c.category_name}</div>
                      </div>
                    </td>
                    <td style="color: #64748b;">${c.description}</td>
                    <td><span class="status-pill role">${c.item_count || 1} Items</span></td>
                    <td style="text-align: right;">
                      <div class="table-actions" style="justify-content: flex-end;">
                        <button class="action-icon-btn" title="Edit">${Icons.edit}</button>
                        <button class="action-icon-btn danger" title="Delete" onclick="App.deleteCategory(${c.category_id})">${Icons.trash}</button>
                      </div>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.categories.length} of ${Store.categories.length} entries</div>
            <div class="pagination-controls">
              <button class="page-btn">${Icons.chevronLeft}</button>
              <button class="page-btn active">1</button>
              <button class="page-btn">${Icons.chevronRight}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }
};

