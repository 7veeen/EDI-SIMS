// shipments.js
App.pages['shipments'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">WORKSPACE</span>
                    <h1>Shipments</h1>
                    <p>Track outgoing deliveries and fulfillment status.</p>
                </div>
            </div>
            <div class="card" style="padding: 2rem; text-align: center; margin-top: 2rem;">
                <i class='bx bx-car' style="font-size: 48px; color: var(--text-light); margin-bottom: 1rem;"></i>
                <h3>No Active Shipments</h3>
                <p style="color: var(--text-secondary);">Your dispatch records will appear here.</p>
            </div>
        `;
        return container;
    }
};
