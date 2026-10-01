// stock-transactions.js

App.pages['stock-transactions'] = {
    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <div class="search-box input-with-icon">
                    <i class='bx bx-search'></i>
                    <input type="text" placeholder="Search transactions..." disabled>
                </div>
                <div style="display: flex; gap: 0.5rem">
                    <button class="btn btn-primary" disabled>
                        <i class='bx bx-log-in'></i> Stock In
                    </button>
                    <button class="btn btn-danger" disabled>
                        <i class='bx bx-log-out'></i> Stock Out
                    </button>
                </div>
            </div>
            
            <div class="glass-panel table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Transaction ID</th>
                            <th>Date</th>
                            <th>Product</th>
                            <th>Type</th>
                            <th>Quantity</th>
                            <th>Reference</th>
                            <th>Recorded By</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7">
                            ${Utils.emptyState('bx-transfer-alt', 'Stock Transactions', 'The backend API for transactions is currently under development. This module will be available soon.')}
                        </td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    }
};
