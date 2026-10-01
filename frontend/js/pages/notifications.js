// notifications.js

App.pages['notifications'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <h3 style="margin: 0"><i class='bx bx-bell text-primary'></i> System Notifications</h3>
            </div>
            
            <div class="glass-panel table-container">
                <table id="notifications-table">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Title</th>
                            <th>Message</th>
                            <th>Date</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="6" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    },

    async init() {
        this.loadNotifications();
    },

    async loadNotifications() {
        const tbody = document.querySelector('#notifications-table tbody');
        try {
            const data = await Api.get('/notifications/');
            
            if (!data || data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center;">No notifications found.</td></tr>`;
                return;
            }

            // Also update the global bell badge
            const unreadCount = data.filter(n => !n.is_read).length;
            const badge = document.getElementById('notification-badge');
            if (badge) {
                if (unreadCount > 0) {
                    badge.textContent = unreadCount;
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            }

            tbody.innerHTML = data.map(n => `
                <tr style="background: ${n.is_read ? 'transparent' : 'rgba(255, 255, 255, 0.05)'}">
                    <td><span class="badge" style="position: relative; top:0; background: var(--warning); color: var(--dark)">${n.notification_type}</span></td>
                    <td><strong>${Utils.escapeHtml(n.title)}</strong></td>
                    <td>${Utils.escapeHtml(n.message)}</td>
                    <td>${Utils.formatDate(n.created_at)}</td>
                    <td>
                        <span class="status-badge ${n.is_read ? 'status-active' : 'status-pending'}">
                            ${n.is_read ? 'Read' : 'Unread'}
                        </span>
                    </td>
                    <td>
                        ${!n.is_read ? `
                        <button class="btn btn-outline" style="padding: 0.3rem 0.6rem; font-size: 0.8rem" onclick="App.pages['notifications'].markAsRead(${n.notification_id})">
                            Mark Read
                        </button>
                        ` : '-'}
                    </td>
                </tr>
            `).join('');
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-danger" style="text-align: center;">Failed to load notifications: ${error.message}</td></tr>`;
        }
    },

    async markAsRead(id) {
        try {
            await Api.patch(`/notifications/${id}/read`);
            this.loadNotifications();
        } catch (error) {
            Utils.showToast(error.message, 'error');
        }
    }
};
