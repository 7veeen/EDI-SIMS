// utils.js

const Utils = {
    showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = 'bx-check-circle';
        if (type === 'error') icon = 'bx-error-circle';
        if (type === 'warning') icon = 'bx-error';

        toast.innerHTML = `
            <i class='bx ${icon}'></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            if (container.contains(toast)) {
                toast.remove();
            }
        }, 3500);
    },

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    },

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
             .toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    },
    
    emptyState(icon, title, subtitle = '') {
        return `
            <div class="empty-state">
                <i class='bx ${icon}'></i>
                <h3>${title}</h3>
                <p>${subtitle}</p>
            </div>
        `;
    }
};
