// View: Command Center / Dashboard
const DashboardView = {
  render() {
    const totalProducts = Store.products.length;
    const totalStock = Store.inventory.reduce((sum, item) => sum + Number(item.quantity_available), 0);
    const lowStockItems = Store.inventory.filter(item => Number(item.quantity_available) <= Number(item.reorder_level));
    const totalPOValue = Store.purchaseOrders.reduce((sum, item) => sum + Number(item.total_amount), 0);

    return `
      <div class="view-section">
        <!-- 4 KPI Cards Matching Uploaded Mockup -->
        <div class="kpi-grid">
          <!-- Card 1: Total Stock Units -->
          <div class="kpi-card">
            <div class="kpi-header">
              <span>${Icons.inventory}</span>
              <span>Total Available Stock</span>
            </div>
            <div class="kpi-value-row">
              <div class="kpi-value">${totalStock.toLocaleString()}</div>
              <svg class="kpi-sparkline" viewBox="0 0 100 40" fill="none">
                <path d="M0,35 Q25,30 45,15 T90,8" stroke="#10b981" stroke-width="2.5" stroke-linecap="round"/>
                <circle cx="90" cy="8" r="4" fill="#10b981"/>
                <circle cx="90" cy="8" r="7" fill="#10b981" opacity="0.25"/>
              </svg>
            </div>
            <div class="kpi-footer">
              <span class="trend-badge positive">${Icons.trendingUp} +16%</span>
              <span class="trend-label">last month</span>
            </div>
          </div>

          <!-- Card 2: Active Products -->
          <div class="kpi-card">
            <div class="kpi-header">
              <span>${Icons.products}</span>
              <span>Catalog Products</span>
            </div>
            <div class="kpi-value-row">
              <div class="kpi-value">${totalProducts}</div>
              <svg class="kpi-sparkline" viewBox="0 0 100 40" fill="none">
                <path d="M0,28 Q30,35 55,20 T90,12" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round"/>
                <circle cx="90" cy="12" r="4" fill="#3b82f6"/>
                <circle cx="90" cy="12" r="7" fill="#3b82f6" opacity="0.25"/>
              </svg>
            </div>
            <div class="kpi-footer">
              <span class="trend-badge positive">${Icons.trendingUp} +08%</span>
              <span class="trend-label">vs target</span>
            </div>
          </div>

          <!-- Card 3: Purchase Order Volume -->
          <div class="kpi-card">
            <div class="kpi-header">
              <span>${Icons.orders}</span>
              <span>Total Orders Value</span>
            </div>
            <div class="kpi-value-row">
              <div class="kpi-value">₹${totalPOValue.toLocaleString()}</div>
              <svg class="kpi-sparkline" viewBox="0 0 100 40" fill="none">
                <path d="M0,15 Q25,5 50,25 T90,10" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/>
                <circle cx="90" cy="10" r="4" fill="#f59e0b"/>
                <circle cx="90" cy="10" r="7" fill="#f59e0b" opacity="0.25"/>
              </svg>
            </div>
            <div class="kpi-footer">
              <span class="trend-badge positive">${Icons.trendingUp} +24%</span>
              <span class="trend-label">last month</span>
            </div>
          </div>

          <!-- Card 4: Low Stock Alert Items -->
          <div class="kpi-card">
            <div class="kpi-header">
              <span>${Icons.notifications}</span>
              <span>Low Stock Alerts</span>
            </div>
            <div class="kpi-value-row">
              <div class="kpi-value" style="color: ${lowStockItems.length > 0 ? '#ef4444' : '#10b981'};">${lowStockItems.length}</div>
              <svg class="kpi-sparkline" viewBox="0 0 100 40" fill="none">
                <path d="M0,10 Q25,25 60,18 T90,30" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/>
                <circle cx="90" cy="30" r="4" fill="#ef4444"/>
                <circle cx="90" cy="30" r="7" fill="#ef4444" opacity="0.25"/>
              </svg>
            </div>
            <div class="kpi-footer">
              <span class="trend-badge negative">${Icons.trendingDown} -05%</span>
              <span class="trend-label">requires replenishment</span>
            </div>
          </div>
        </div>

        <!-- Main Card: Critical Inventory Attention & Recent Transactions -->
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Inventory Health & Critical Attention</h2>
              <p>Items reaching or falling below safety reorder threshold</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-add-product')">
                ${Icons.plus} Add Product
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search low stock items..." oninput="App.filterTable(this, 'table-low-stock')"/>
            </div>
            <button class="btn-secondary" onclick="App.navigate('inventory')">
              ${Icons.filter} View Full Inventory
            </button>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-low-stock">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Product Details</th>
                  <th>SKU Code</th>
                  <th>Stock Available</th>
                  <th>Reorder Limit</th>
                  <th>Status</th>
                  <th style="text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${lowStockItems.length === 0 ? `
                  <tr><td colspan="7" style="text-align: center; padding: 24px; color: #10b981; font-weight: 600;">All inventory levels are healthy! Zero low-stock alerts.</td></tr>
                ` : lowStockItems.map(item => `
                  <tr>
                    <td><input type="checkbox" class="table-checkbox" /></td>
                    <td>
                      <div class="entity-cell">
                        <div class="entity-icon-avatar">${item.product_name.charAt(0)}</div>
                        <div>
                          <div class="entity-name">${item.product_name}</div>
                          <div class="entity-sub">Last updated: ${item.last_updated}</div>
                        </div>
                      </div>
                    </td>
                    <td><code>${item.sku}</code></td>
                    <td><strong style="color: #ef4444; font-size: 15px;">${item.quantity_available} units</strong></td>
                    <td>${item.reorder_level} units</td>
                    <td><span class="status-pill lowstock">Low Stock</span></td>
                    <td style="text-align: right;">
                      <button class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="App.openRestockModal(${item.product_id})">
                        ${Icons.plus} Restock
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${lowStockItems.length} of ${lowStockItems.length} entries</div>
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

