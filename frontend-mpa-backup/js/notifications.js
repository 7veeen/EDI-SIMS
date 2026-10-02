// Page Behavior: Notifications
document.addEventListener("DOMContentLoaded", async () => {
  const list = document.getElementById("notifications-list");

  async function loadNotifications() {
    try {
      const data = await API.request("/api/notifications/");
      if (data && list) {
        if (data.length === 0) {
          list.innerHTML = '<p style="color: #10b981;">No notifications to display.</p>';
        } else {
          list.innerHTML = data.map(n => `
            <div class="notif-card ${!n.is_read ? 'unread' : ''}">
              <div class="notif-header">
                <span class="notif-title">${n.title}</span>
                <span class="status-pill ${n.notification_type === 'WARNING' ? 'warning' : 'neutral'}">${n.notification_type}</span>
              </div>
              <div class="notif-body">${n.message}</div>
              <div class="notif-time">${n.created_at || 'Recently'}</div>
            </div>
          `).join("");
        }
      }
    } catch (err) {
      if (list) {
        list.innerHTML = '<p style="color: #b45309;">Start backend at http://127.0.0.1:5000 to fetch notifications.</p>';
      }
    }
  }

  loadNotifications();
});
