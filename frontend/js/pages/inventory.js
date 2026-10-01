// inventory.js

App.pages['inventory'] = {
    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="stats-grid">
                <div class="glass-panel stat-card">
                    <div class="icon"><i class='bx bx-check-shield'></i></div>
                    <div class="details">
                        <h3>---</h3>
                        <p>In Stock</p>
                    </div>
                </div>
                <div class="glass-panel stat-card">
                    <div class="icon" style="color: var(--warning); background: rgba(251, 191, 36, 0.1)"><i class='bx bx-error'></i></div>
                    <div class="details">
                        <h3>---</h3>
                        <p>Low Stock</p>
                    </div>
                </div>
            </div>

            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <div class="search-box input-with-icon">
                    <i class='bx bx-search'></i>
                    <input type="text" placeholder="Search inventory..." disabled>
                </div>
                <button class="btn btn-primary" disabled>
                    <i class='bx bx-transfer'></i> Adjust Stock
                </button>
            </div>
            
            <div class="glass-panel table-container">
                <table>
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>Product Name</th>
                            <th>Available Qty</th>
                            <th>Reorder Level</th>
                            <th>Status</th>
                            <th>Last Updated</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7">
                            ${Utils.emptyState('bx-box', 'Inventory Tracking', 'The backend API for inventory is currently under development. This module will be available soon.')}
                        </td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    }
};
