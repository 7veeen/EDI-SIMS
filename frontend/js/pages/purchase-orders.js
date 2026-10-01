// purchase-orders.js

App.pages['purchase-orders'] = {
    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <div class="search-box input-with-icon">
                    <i class='bx bx-search'></i>
                    <input type="text" placeholder="Search POs..." disabled>
                </div>
                <button class="btn btn-primary" disabled>
                    <i class='bx bx-receipt'></i> Create PO
                </button>
            </div>
            
            <div class="glass-panel table-container">
                <table>
                    <thead>
                        <tr>
                            <th>PO Number</th>
                            <th>Supplier</th>
                            <th>Date Ordered</th>
                            <th>Expected Delivery</th>
                            <th>Total Amount</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7">
                            ${Utils.emptyState('bx-receipt', 'Purchase Orders', 'The backend API for purchase orders is currently under development. This module will be available soon.')}
                        </td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    }
};
