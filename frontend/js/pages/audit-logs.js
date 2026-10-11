// audit-logs.js

App.pages['audit-logs'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <h3 style="margin: 0"><i class='bx bx-history text-primary'></i> Audit Logs</h3>
                <p style="color: var(--gray); margin: 0; font-size: 0.9rem;">Complete history of system changes</p>
            </div>
            
            <div class="glass-panel table-container">
                <table id="audit-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Time</th>
                            <th>User</th>
                            <th>Action</th>
                            <th>Table</th>
                            <th>Record ID</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    },

    async init() {
        const tbody = document.querySelector('#audit-table tbody');
        try {
            const data = await Api.get('/audit-logs/');
            
            if (!data || data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center;">No audit logs found.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.map(l => {
                const userDisplay = l.username || (l.user_id != null ? `User #${l.user_id}` : 'System');
                const recordIdDisplay = (l.record_id !== null && l.record_id !== undefined && l.record_id !== '') ? String(l.record_id) : '-';
                return `
                <tr>
                    <td>#${Utils.escapeHtml(String(l.log_id || ''))}</td>
                    <td>${Utils.formatDate(l.action_time)}</td>
                    <td>${Utils.escapeHtml(userDisplay)}</td>
                    <td><span class="badge" style="position: relative; top:0; background: #e0e0e0; color: #333;">${Utils.escapeHtml(l.action || '-')}</span></td>
                    <td>${Utils.escapeHtml(l.table_name || '-')}</td>
                    <td>${Utils.escapeHtml(recordIdDisplay)}</td>
                    <td>${Utils.escapeHtml(l.ip_address || '-')}</td>
                </tr>
            `;
            }).join('');
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-danger" style="text-align: center;">Failed to load audit logs: ${Utils.escapeHtml(error.message || 'Unknown error')}</td></tr>`;
        }
    }
};
