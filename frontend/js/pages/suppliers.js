// suppliers.js

App.pages['suppliers'] = {
    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <div class="search-box input-with-icon">
                    <i class='bx bx-search'></i>
                    <input type="text" placeholder="Search suppliers..." disabled>
                </div>
                <button class="btn btn-primary" disabled>
                    <i class='bx bx-plus'></i> Add Supplier
                </button>
            </div>
            
            <div class="glass-panel table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Company Name</th>
                            <th>Contact Person</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7">
                            ${Utils.emptyState('bx-buildings', 'Supplier Management', 'The backend API for suppliers is currently under development. This module will be available soon.')}
                        </td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    }
};
