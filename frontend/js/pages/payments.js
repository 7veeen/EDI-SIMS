// payments.js
App.pages['payments'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">FINANCE</span>
                    <h1>Payments</h1>
                    <p>Track pending invoices and received payments.</p>
                </div>
            </div>
            <div class="card" style="padding: 2rem; text-align: center; margin-top: 2rem;">
                <i class='bx bx-money' style="font-size: 48px; color: var(--text-light); margin-bottom: 1rem;"></i>
                <h3>No Recent Transactions</h3>
                <p style="color: var(--text-secondary);">Your financial records will appear here.</p>
            </div>
        `;
        return container;
    }
};
