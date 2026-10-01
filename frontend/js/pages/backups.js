// backups.js

App.pages['backups'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0"><i class='bx bx-data text-primary'></i> System Backups</h3>
                <button class="btn btn-primary" id="btn-create-backup">
                    <i class='bx bx-cloud-upload'></i> Create New Backup
                </button>
            </div>
            
            <div class="glass-panel table-container">
                <table id="backups-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Backup Name</th>
                            <th>Type</th>
                            <th>Size</th>
                            <th>Date</th>
                            <th>Status</th>
                            <th>Created By</th>
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
        this.loadBackups();

        document.getElementById('btn-create-backup').addEventListener('click', () => {
            this.createBackup();
        });
    },

    async loadBackups() {
        const tbody = document.querySelector('#backups-table tbody');
        try {
            const data = await Api.get('/backups/');
            
            if (!data || data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center;">No backups found.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.map(b => `
                <tr>
                    <td>#${b.backup_id}</td>
                    <td><strong>${Utils.escapeHtml(b.backup_name)}</strong></td>
                    <td><span class="badge" style="position: relative; top:0; background: #e0e0e0; color: #333;">${b.backup_type}</span></td>
                    <td>${b.backup_size}</td>
                    <td>${Utils.formatDate(b.backup_date)}</td>
                    <td>
                        <span class="status-badge ${b.status === 'Success' ? 'status-active' : 'status-inactive'}">
                            ${b.status}
                        </span>
                    </td>
                    <td>User #${b.created_by}</td>
                </tr>
            `).join('');
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-danger" style="text-align: center;">Failed to load backups: ${error.message}</td></tr>`;
        }
    },

    async createBackup() {
        const user = Auth.getUser();
        if (!user) return;

        if (!confirm('Creating a full system backup may take some time. Do you want to proceed?')) return;

        const btn = document.getElementById('btn-create-backup');
        btn.disabled = true;
        btn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Backing up...`;

        try {
            const data = await Api.post('/backups/', { created_by: user.id });
            Utils.showToast(data.message, 'success');
            this.loadBackups();
        } catch (error) {
            Utils.showToast(error.message || "Failed to create backup", "error");
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class='bx bx-cloud-upload'></i> Create New Backup`;
        }
    }
};
