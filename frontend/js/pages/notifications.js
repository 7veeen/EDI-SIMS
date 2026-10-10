// notifications.js - Step 7C Notification UI, Filters, Search & Navigation

App.pages['notifications'] = {
    rawNotifications: [],
    currentFilter: 'all', // 'all', 'unread', 'read'
    searchQuery: '',
    pendingMarkReadIds: new Set(),
    isMarkingAllRead: false,
    debounceTimer: null,

    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 20px;">
                <div>
                    <span class="eyebrow">COMMUNICATION &amp; ALERTS</span>
                    <h1 style="margin: 4px 0 0 0; display: flex; align-items: center; gap: 8px;">
                        <i class='bx bx-bell text-primary'></i> Notifications
                    </h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-secondary); font-size: 13px;">View and manage your private system alerts, stock notifications, and operational updates.</p>
                </div>
                <div class="header-actions" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <button class="btn btn-outline" id="btn-refresh-notifications" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer;">
                        <i class='bx bx-refresh' id="refresh-icon"></i> Refresh
                    </button>
                    <button class="btn btn-primary" id="btn-mark-all-read" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; background: #2563eb; color: white; border: none;">
                        <i class='bx bx-check-double'></i> Mark All as Read
                    </button>
                </div>
            </div>

            <!-- Filter & Search Toolbar -->
            <div class="card" style="padding: 14px 18px; margin-bottom: 18px; display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; flex: 1;">
                    <!-- Filter Tabs -->
                    <div class="notif-filter-tabs" role="tablist" aria-label="Notification Filters">
                        <button type="button" class="notif-filter-tab active" data-filter="all" id="notif-tab-all" role="tab" aria-selected="true">
                            <span>All</span>
                            <span class="notif-count-pill" id="notif-count-all">0</span>
                        </button>
                        <button type="button" class="notif-filter-tab" data-filter="unread" id="notif-tab-unread" role="tab" aria-selected="false">
                            <span>Unread</span>
                            <span class="notif-count-pill" id="notif-count-unread">0</span>
                        </button>
                        <button type="button" class="notif-filter-tab" data-filter="read" id="notif-tab-read" role="tab" aria-selected="false">
                            <span>Read</span>
                            <span class="notif-count-pill" id="notif-count-read">0</span>
                        </button>
                    </div>

                    <!-- Search Input -->
                    <div class="global-search" style="margin: 0; flex: 1; min-width: 220px; max-width: 380px; height: 38px; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="notif-search-input" placeholder="Search title, message, type..." style="background: transparent; font-size: 13.5px;">
                        <button type="button" id="notif-search-clear" style="background: none; border: none; color: var(--text-light); cursor: pointer; display: none; padding: 2px;">
                            <i class='bx bx-x' style="font-size: 16px;"></i>
                        </button>
                    </div>
                </div>

                <div id="notif-result-indicator" style="font-size: 12px; color: var(--text-secondary); white-space: nowrap;">
                    <!-- Updated dynamically -->
                </div>
            </div>
            
            <!-- Notifications Table Card -->
            <div class="card table-responsive" style="border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); overflow: hidden;">
                <table class="table" id="notifications-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--bg-surface, #f9fafb); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
                            <th style="padding: 12px 16px; text-align: left;">TYPE</th>
                            <th style="padding: 12px 16px; text-align: left;">TITLE</th>
                            <th style="padding: 12px 16px; text-align: left;">MESSAGE</th>
                            <th style="padding: 12px 16px; text-align: center;">PRIORITY</th>
                            <th style="padding: 12px 16px; text-align: left;">DATE</th>
                            <th style="padding: 12px 16px; text-align: center;">STATUS</th>
                            <th style="padding: 12px 16px; text-align: center;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody id="notifications-tbody">
                        <tr>
                            <td colspan="7" style="text-align: center; padding: 40px 20px; color: var(--text-secondary);">
                                <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; display: block; margin-bottom: 8px;"></i>
                                Loading your notifications...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    },

    async init() {
        this.currentFilter = 'all';
        this.searchQuery = '';
        this.rawNotifications = [];
        this.pendingMarkReadIds.clear();

        // 1. Setup Filter Tabs
        const filterTabs = document.querySelectorAll('.notif-filter-tab');
        filterTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                filterTabs.forEach(t => {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                this.currentFilter = tab.dataset.filter || 'all';
                this.renderTable();
            });
        });

        // 2. Setup Search Box with Debounce
        const searchInput = document.getElementById('notif-search-input');
        const clearBtn = document.getElementById('notif-search-clear');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.debounceTimer);
                const val = e.target.value.trim();
                if (clearBtn) {
                    clearBtn.style.display = val ? 'block' : 'none';
                }
                this.debounceTimer = setTimeout(() => {
                    this.searchQuery = val.toLowerCase();
                    this.renderTable();
                }, 200);
            });
        }

        if (clearBtn && searchInput) {
            clearBtn.addEventListener('click', () => {
                searchInput.value = '';
                clearBtn.style.display = 'none';
                this.searchQuery = '';
                this.renderTable();
                searchInput.focus();
            });
        }

        // 3. Setup Refresh Button
        const refreshBtn = document.getElementById('btn-refresh-notifications');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadNotifications());
        }

        // 4. Setup Mark All as Read Button
        const markAllBtn = document.getElementById('btn-mark-all-read');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => this.markAllAsRead());
        }

        // 5. Initial Data Load
        await this.loadNotifications();
    },

    async loadNotifications() {
        const tbody = document.getElementById('notifications-tbody');
        const refreshIcon = document.getElementById('refresh-icon');
        if (refreshIcon) refreshIcon.classList.add('bx-spin');

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px 20px; color: var(--text-secondary);">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; display: block; margin-bottom: 8px;"></i>
                        Loading your notifications...
                    </td>
                </tr>
            `;
        }

        try {
            const data = await Api.getNotifications();
            this.rawNotifications = Array.isArray(data) ? data : [];
            this.updateCounts();
            this.renderTable();
        } catch (error) {
            this.rawNotifications = [];
            this.updateCounts();
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" style="text-align: center; padding: 40px 20px; color: #dc2626;">
                            <i class='bx bx-error-circle' style="font-size: 28px; display: block; margin-bottom: 8px;"></i>
                            <div style="font-weight: 600; margin-bottom: 4px;">Failed to load notifications</div>
                            <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">${Utils.escapeHtml(error.message || 'Server error')}</div>
                            <button class="btn btn-outline btn-sm" id="btn-retry-notifs" style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; border-radius: 6px; cursor: pointer;">
                                <i class='bx bx-refresh'></i> Retry
                            </button>
                        </td>
                    </tr>
                `;
                const retryBtn = document.getElementById('btn-retry-notifs');
                if (retryBtn) {
                    retryBtn.addEventListener('click', () => this.loadNotifications());
                }
            }
        } finally {
            if (refreshIcon) refreshIcon.classList.remove('bx-spin');
        }
    },

    updateCounts() {
        const total = this.rawNotifications.length;
        const unread = this.rawNotifications.filter(n => !n.is_read).length;
        const read = total - unread;

        const countAll = document.getElementById('notif-count-all');
        const countUnread = document.getElementById('notif-count-unread');
        const countRead = document.getElementById('notif-count-read');

        if (countAll) countAll.textContent = total;
        if (countUnread) countUnread.textContent = unread;
        if (countRead) countRead.textContent = read;

        // Keep header unread badge synchronized
        if (App.notifications && typeof App.notifications.renderBadge === 'function') {
            App.notifications.unreadCount = unread;
            App.notifications.renderBadge(unread);
        }
    },

    renderTable() {
        const tbody = document.getElementById('notifications-tbody');
        const indicator = document.getElementById('notif-result-indicator');
        if (!tbody) return;

        // 1. Overall empty state
        if (this.rawNotifications.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 50px 20px;">
                        ${Utils.emptyState('bx-bell', 'No Notifications', 'You are all caught up! There are no notifications for your account.')}
                    </td>
                </tr>
            `;
            if (indicator) indicator.textContent = '0 notifications';
            return;
        }

        // 2. Filter by status
        let filtered = this.rawNotifications.filter(n => {
            if (this.currentFilter === 'unread') return !n.is_read;
            if (this.currentFilter === 'read') return n.is_read;
            return true;
        });

        // 3. Filter by search query
        if (this.searchQuery) {
            filtered = filtered.filter(n => {
                const combined = [
                    n.title || '',
                    n.message || '',
                    n.notification_type || '',
                    n.priority || '',
                    n.reference_type || ''
                ].join(' ').toLowerCase();
                return combined.includes(this.searchQuery);
            });
        }

        if (indicator) {
            indicator.textContent = `Showing ${filtered.length} of ${this.rawNotifications.length}`;
        }

        // 4. Filtered empty state
        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 50px 20px;">
                        <div class="empty-state">
                            <i class='bx bx-search' style="font-size: 32px; color: var(--text-light); margin-bottom: 8px;"></i>
                            <h3 style="margin: 0 0 6px 0; font-size: 15px;">No matching notifications</h3>
                            <p style="margin: 0 0 12px 0; color: var(--text-secondary); font-size: 13px;">No notifications match your current filter or search criteria.</p>
                            <button class="btn btn-outline btn-sm" id="btn-clear-filters" style="padding: 6px 12px; border-radius: 6px; cursor: pointer;">
                                Reset Filter &amp; Search
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            const clearBtn = document.getElementById('btn-clear-filters');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.currentFilter = 'all';
                    this.searchQuery = '';
                    const searchInput = document.getElementById('notif-search-input');
                    const clearInputBtn = document.getElementById('notif-search-clear');
                    if (searchInput) searchInput.value = '';
                    if (clearInputBtn) clearInputBtn.style.display = 'none';

                    document.querySelectorAll('.notif-filter-tab').forEach(t => {
                        const isAll = t.dataset.filter === 'all';
                        t.classList.toggle('active', isAll);
                        t.setAttribute('aria-selected', isAll ? 'true' : 'false');
                    });
                    this.renderTable();
                });
            }
            return;
        }

        // 5. Render Rows
        tbody.innerHTML = filtered.map(n => {
            const isUnread = !n.is_read;
            const nType = (n.notification_type || '').toLowerCase();

            // Type Badge Color
            let badgeBg = 'rgba(59, 130, 246, 0.1)';
            let badgeColor = '#2563eb';
            if (nType.includes('low stock') || nType.includes('reject') || nType.includes('warning')) {
                badgeBg = 'rgba(239, 68, 68, 0.1)';
                badgeColor = '#dc2626';
            } else if (nType.includes('delivered') || nType.includes('approved') || nType.includes('accepted') || nType.includes('stock-in')) {
                badgeBg = 'rgba(16, 185, 129, 0.1)';
                badgeColor = '#059669';
            } else if (nType.includes('assignment') || nType.includes('submitted')) {
                badgeBg = 'rgba(147, 51, 234, 0.1)';
                badgeColor = '#9333ea';
            }

            // Priority Badge Color
            const prio = n.priority || 'Normal';
            let prioBg = 'rgba(107, 114, 128, 0.1)';
            let prioColor = '#4b5563';
            if (prio === 'High' || prio === 'Critical') {
                prioBg = 'rgba(239, 68, 68, 0.12)';
                prioColor = '#dc2626';
            } else if (prio === 'Normal') {
                prioBg = 'rgba(59, 130, 246, 0.1)';
                prioColor = '#2563eb';
            }

            const rowBg = isUnread ? 'rgba(37, 99, 235, 0.04)' : 'transparent';
            const borderLeftStyle = isUnread ? '3.5px solid #2563eb' : '3.5px solid transparent';
            const dateFormatted = Utils.formatDate(n.created_at);
            const hasReference = n.reference_type && n.reference_id;

            return `
                <tr style="background: ${rowBg}; border-bottom: 1px solid var(--border); border-left: ${borderLeftStyle}; transition: background 0.15s ease;" onmouseover="this.style.background='var(--bg-hover, rgba(0,0,0,0.02))'" onmouseout="this.style.background='${rowBg}'">
                    <td style="padding: 12px 16px;">
                        <span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: ${badgeBg}; color: ${badgeColor}; font-size: 11px; font-weight: 600; white-space: nowrap;">
                            ${Utils.escapeHtml(n.notification_type || 'Alert')}
                        </span>
                    </td>
                    <td style="padding: 12px 16px; font-weight: ${isUnread ? '700' : '500'}; color: var(--text);">
                        ${hasReference ? `
                            <a href="javascript:void(0)" onclick="App.navigateToReference('${Utils.escapeHtml(n.reference_type)}', '${Utils.escapeHtml(n.reference_id)}', ${n.notification_id})" 
                               style="color: var(--text); text-decoration: none; display: inline-flex; align-items: center; gap: 4px;" 
                               title="Navigate to ${Utils.escapeHtml(n.reference_type)} #${Utils.escapeHtml(n.reference_id)}">
                                ${Utils.escapeHtml(n.title)}
                                <i class='bx bx-link-external' style="font-size: 13px; color: var(--primary); opacity: 0.8;"></i>
                            </a>
                        ` : Utils.escapeHtml(n.title)}
                    </td>
                    <td style="padding: 12px 16px; color: var(--text-secondary); font-size: 13px; max-width: 380px; line-height: 1.4;">
                        ${Utils.escapeHtml(n.message)}
                    </td>
                    <td style="padding: 12px 16px; text-align: center;">
                        <span style="display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 4px; background: ${prioBg}; color: ${prioColor}; font-size: 11px; font-weight: 600;">
                            ${Utils.escapeHtml(prio)}
                        </span>
                    </td>
                    <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary); white-space: nowrap;">
                        ${dateFormatted}
                    </td>
                    <td style="padding: 12px 16px; text-align: center;">
                        <span class="status-badge ${isUnread ? 'status-pending' : 'status-active'}" style="font-size: 11px; padding: 2px 8px; border-radius: 4px;">
                            ${isUnread ? 'Unread' : 'Read'}
                        </span>
                    </td>
                    <td style="padding: 12px 16px; text-align: center;">
                        <div style="display: inline-flex; gap: 6px; align-items: center; justify-content: center; flex-wrap: wrap;">
                            ${isUnread ? `
                                <button class="btn btn-sm" id="btn-read-${n.notification_id}" 
                                        onclick="App.pages['notifications'].markAsRead(${n.notification_id}, this)" 
                                        style="padding: 4px 10px; font-size: 12px; border-radius: 6px; background: rgba(37, 99, 235, 0.08); color: #2563eb; border: 1px solid rgba(37, 99, 235, 0.2); cursor: pointer; font-weight: 600; white-space: nowrap;"
                                        title="Mark as read">
                                    <i class='bx bx-check'></i> Mark Read
                                </button>
                            ` : ''}

                            ${hasReference ? `
                                <button class="btn btn-sm btn-outline" 
                                        onclick="App.navigateToReference('${Utils.escapeHtml(n.reference_type)}', '${Utils.escapeHtml(n.reference_id)}', ${n.notification_id})" 
                                        style="padding: 4px 8px; font-size: 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;"
                                        title="Navigate to ${Utils.escapeHtml(n.reference_type)} #${Utils.escapeHtml(n.reference_id)}">
                                    <i class='bx bx-right-arrow-alt'></i> View
                                </button>
                            ` : ''}

                            ${!isUnread && !hasReference ? `
                                <span style="color: var(--text-light); font-size: 13px;">—</span>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    },

    async markAsRead(id, btnElement = null) {
        if (!id) return;
        if (this.pendingMarkReadIds.has(id)) return; // Prevent repeated double-clicks

        this.pendingMarkReadIds.add(id);
        if (btnElement) {
            btnElement.disabled = true;
            btnElement.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i>`;
        }

        try {
            await Api.markNotificationRead(id);
            
            // Update local in-memory dataset
            const item = this.rawNotifications.find(n => n.notification_id === id);
            if (item) {
                item.is_read = true;
                item.read_at = new Date().toISOString();
            }

            Utils.showToast('Notification marked as read', 'success');
            this.updateCounts();
            this.renderTable();
        } catch (error) {
            Utils.showToast(error.message || 'Failed to mark notification as read', 'error');
            if (btnElement) {
                btnElement.disabled = false;
                btnElement.innerHTML = `<i class='bx bx-check'></i> Mark Read`;
            }
        } finally {
            this.pendingMarkReadIds.delete(id);
        }
    },

    async markAllAsRead() {
        if (this.isMarkingAllRead) return;

        const unreadCount = this.rawNotifications.filter(n => !n.is_read).length;
        if (unreadCount === 0) {
            Utils.showToast('All notifications are already read', 'info');
            return;
        }

        const confirmed = window.confirm(`Mark all ${unreadCount} unread notification${unreadCount === 1 ? '' : 's'} as read?`);
        if (!confirmed) return;

        const markAllBtn = document.getElementById('btn-mark-all-read');
        this.isMarkingAllRead = true;
        if (markAllBtn) {
            markAllBtn.disabled = true;
            markAllBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Updating...`;
        }

        try {
            const res = await Api.markAllNotificationsRead();
            const count = res && res.updated_count !== undefined ? res.updated_count : unreadCount;
            
            // Mark all items read locally
            this.rawNotifications.forEach(n => {
                n.is_read = true;
                if (!n.read_at) n.read_at = new Date().toISOString();
            });

            Utils.showToast(`Marked ${count} notification${count === 1 ? '' : 's'} as read`, 'success');
            this.updateCounts();
            this.renderTable();
        } catch (error) {
            Utils.showToast(error.message || 'Failed to mark all as read', 'error');
        } finally {
            this.isMarkingAllRead = false;
            if (markAllBtn) {
                markAllBtn.disabled = false;
                markAllBtn.innerHTML = `<i class='bx bx-check-double'></i> Mark All as Read`;
            }
        }
    }
};
