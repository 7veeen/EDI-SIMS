// app.js

const App = {
    pages: {},
    
    routes: [
        { path: 'dashboard', icon: 'bx-grid-alt', label: 'Dashboard', roles: ['Owner', 'Manager', 'Employee', 'Supplier'] },
        { path: 'stock-requests', icon: 'bx-git-pull-request', label: 'Stock Requests', roles: ['Owner', 'Manager', 'Supplier'] },
        { path: 'quotations', icon: 'bx-file', label: 'Quotations', roles: ['Owner', 'Manager', 'Supplier'] },
        { path: 'users', icon: 'bx-group', label: 'User Management', roles: ['Owner', 'Manager'] },
        { path: 'products', icon: 'bx-package', label: 'Products', roles: ['Owner', 'Manager', 'Employee'] },
        { path: 'categories', icon: 'bx-category', label: 'Categories', roles: ['Owner', 'Manager', 'Employee', 'Supplier'] },
        { path: 'inventory', icon: 'bx-box', label: 'Inventory', roles: ['Owner', 'Manager', 'Employee'] },
        { path: 'suppliers', icon: 'bx-buildings', label: 'Suppliers', roles: ['Owner', 'Manager'] },
        { path: 'purchase-orders', icon: 'bx-receipt', label: 'Purchase Orders', roles: ['Owner', 'Manager', 'Supplier'] },
        { path: 'shipments', icon: 'bx-car', label: 'Shipments', roles: ['Owner', 'Manager', 'Supplier', 'Employee'] },
        { path: 'stock-transactions', icon: 'bx-transfer', label: 'Stock Transactions', roles: ['Owner', 'Manager', 'Employee'] },
        { path: 'payments', icon: 'bx-money', label: 'Payments', roles: ['Supplier'] },
        { path: 'reports', icon: 'bx-bar-chart-alt-2', label: 'Reports', roles: ['Owner', 'Manager'] },
        { path: 'system-status', icon: 'bx-pulse', label: 'System Health', roles: ['Owner', 'Manager'] },
        { path: 'notifications', icon: 'bx-bell', label: 'Notifications', roles: ['Owner', 'Manager', 'Employee', 'Supplier'] },
        { path: 'audit-logs', icon: 'bx-history', label: 'Audit Logs', roles: ['Owner'] },
        { path: 'backups', icon: 'bx-data', label: 'Backup & Restore', roles: ['Owner'] }
    ],

    init() {
        this.initTheme();

        const loginThemeBtn = document.getElementById('loginThemeToggle');
        if (loginThemeBtn) {
            loginThemeBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        if (!Auth.isAuthenticated()) {
            document.getElementById('login-container').classList.remove('hidden');
            return;
        }

        document.getElementById('login-container').classList.add('hidden');
        document.getElementById('app-container').classList.remove('hidden');
        this.setupSidebar();
        this.setupEventListeners();
        this.notifications.init();
        
        // Initial route
        const hash = window.location.hash.replace('#', '') || 'dashboard';
        this.navigate(hash);
    },

    initTheme() {
        const savedTheme = localStorage.getItem('sims_theme') || localStorage.getItem('theme') || localStorage.getItem('supplierTheme');
        const isDark = savedTheme === 'dark';
        if (isDark) {
            document.body.classList.add('dark');
            document.body.classList.add('dark-theme');
        } else {
            document.body.classList.remove('dark');
            document.body.classList.remove('dark-theme');
        }
        this.updateThemeIcon();
    },

    updateThemeIcon() {
        const themeBtns = [document.getElementById('themeToggle'), document.getElementById('loginThemeToggle')];
        const isDark = document.body.classList.contains('dark') || document.body.classList.contains('dark-theme');
        themeBtns.forEach(themeBtn => {
            if (!themeBtn) return;
            const i = themeBtn.querySelector('i');
            if (i) {
                i.className = isDark ? 'bx bx-sun' : 'bx bx-moon';
            }
            themeBtn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
        });
    },

    toggleTheme() {
        const isDark = document.body.classList.toggle('dark');
        document.body.classList.toggle('dark-theme', isDark);
        localStorage.setItem('sims_theme', isDark ? 'dark' : 'light');
        this.updateThemeIcon();
    },

    setupSidebar() {
        const user = Auth.getUser();
        if (!user) return;

        // Update sidebar and topbar names
        document.getElementById('display-name').textContent = user.username;
        document.getElementById('display-role').textContent = user.role;
        document.getElementById('topbar-display-name').textContent = user.username;
        document.getElementById('topbar-display-role').textContent = user.role;

        const navContainer = document.getElementById('sidebar-nav');
        navContainer.innerHTML = '<div class="nav-section-title">WORKSPACE</div>';

        this.routes.forEach(route => {
            if (route.roles.includes(user.role)) {
                // Add Management section title before reports
                if (route.path === 'reports') {
                    const mgmtTitle = document.createElement('div');
                    mgmtTitle.className = 'nav-section-title account-section';
                    mgmtTitle.textContent = 'MANAGEMENT';
                    navContainer.appendChild(mgmtTitle);
                }
                // Add Account section title before notifications
                if (route.path === 'notifications') {
                    const accTitle = document.createElement('div');
                    accTitle.className = 'nav-section-title account-section';
                    accTitle.textContent = 'ACCOUNT';
                    navContainer.appendChild(accTitle);
                }

                const a = document.createElement('button');
                a.className = 'nav-item';
                a.innerHTML = `<i class='bx ${route.icon}'></i><span>${route.label}</span>`;
                a.dataset.path = route.path;
                
                a.addEventListener('click', () => {
                    window.location.hash = route.path;
                    if (window.innerWidth <= 992) {
                        document.getElementById('sidebar').classList.remove('active');
                    }
                });

                navContainer.appendChild(a);
            }
        });
    },

    setupEventListeners() {
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.replace('#', '') || 'dashboard';
            this.navigate(hash);
        });

        // Theme toggle
        const themeBtn = document.getElementById('themeToggle');
        if (themeBtn) {
            this.updateThemeIcon();
            themeBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        // Sidebar toggle desktop
        const toggleBtn = document.getElementById('sidebarToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const sidebar = document.getElementById('sidebar');
                const main = document.querySelector('.main');
                sidebar.classList.toggle('collapsed');
                main.classList.toggle('expanded');
            });
        }

        // Mobile menu toggle
        const mobileBtn = document.getElementById('mobileMenu');
        if (mobileBtn) {
            mobileBtn.addEventListener('click', () => {
                document.getElementById('sidebar').classList.toggle('active');
            });
        }

        document.getElementById('logout-btn').addEventListener('click', () => {
            Auth.logout();
        });
    },

    navigate(path) {
        const user = Auth.getUser();
        if (!user) return;

        const route = this.routes.find(r => r.path === path);
        if (!route) {
            window.location.hash = 'dashboard';
            return;
        }

        if (!route.roles.includes(user.role)) {
            Utils.showToast("You don't have permission to view this page", "error");
            window.location.hash = 'dashboard';
            return;
        }

        // Update active nav
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        const activeNav = document.querySelector(`.nav-item[data-path="${path}"]`);
        if (activeNav) activeNav.classList.add('active');

        // Load page content
        const contentArea = document.getElementById('content-area');
        if (this.pages[path] && typeof this.pages[path].render === 'function') {
            contentArea.innerHTML = '';
            contentArea.appendChild(this.pages[path].render());
            
            // Add .page and .active classes to the returned container
            const child = contentArea.firstElementChild;
            if (child) {
                child.classList.add('page', 'active');
            }

            if (this.pages[path].init) {
                this.pages[path].init();
            }
        } else {
            contentArea.innerHTML = `<div class="page active">${Utils.emptyState('bx-wrench', 'Coming Soon', 'This module is under development')}</div>`;
        }

        // Keep unread notification count synchronized across page switches
        if (this.notifications && typeof this.notifications.updateUnreadCount === 'function') {
            this.notifications.updateUnreadCount();
        }
    },

    // Step 7C Notification Controller
    notifications: {
        unreadCount: 0,
        isOpen: false,
        isLoading: false,

        async init() {
            this.setupDropdownListeners();
            await this.updateUnreadCount();
        },

        setupDropdownListeners() {
            const bellBtn = document.getElementById('notificationButton');
            if (!bellBtn || bellBtn.dataset.listenerAttached) return;
            bellBtn.dataset.listenerAttached = 'true';

            bellBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            });

            // Close on click outside
            document.addEventListener('click', (e) => {
                const dropdown = document.getElementById('notificationDropdown');
                const bell = document.getElementById('notificationButton');
                if (this.isOpen && dropdown && !dropdown.contains(e.target) && !bell.contains(e.target)) {
                    this.closeDropdown();
                }
            });

            // Close on Escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.closeDropdown();
                }
            });
        },

        async updateUnreadCount() {
            if (!Auth.isAuthenticated()) return 0;
            try {
                const res = await Api.getUnreadNotificationCount();
                const count = res && res.unread_count !== undefined ? Number(res.unread_count) : 0;
                this.unreadCount = count;
                this.renderBadge(count);
                return count;
            } catch (err) {
                return 0;
            }
        },

        renderBadge(count) {
            const badge = document.getElementById('notification-badge');
            if (badge) {
                if (count > 0) {
                    badge.textContent = count > 99 ? '99+' : count;
                    badge.style.display = 'inline-flex';
                    badge.classList.remove('hidden');
                } else {
                    badge.textContent = '0';
                    badge.style.display = 'none';
                    badge.classList.add('hidden');
                }
            }
        },

        async toggleDropdown() {
            if (this.isOpen) {
                this.closeDropdown();
            } else {
                await this.openDropdown();
            }
        },

        async openDropdown() {
            const dropdown = document.getElementById('notificationDropdown');
            const bellBtn = document.getElementById('notificationButton');
            if (!dropdown) return;

            this.isOpen = true;
            dropdown.style.display = 'flex';
            if (bellBtn) {
                bellBtn.setAttribute('aria-expanded', 'true');
            }

            await this.loadRecent();
        },

        closeDropdown() {
            const dropdown = document.getElementById('notificationDropdown');
            const bellBtn = document.getElementById('notificationButton');
            if (!dropdown) return;

            this.isOpen = false;
            dropdown.style.display = 'none';
            if (bellBtn) {
                bellBtn.setAttribute('aria-expanded', 'false');
            }
        },

        async loadRecent() {
            const dropdown = document.getElementById('notificationDropdown');
            if (!dropdown) return;

            dropdown.innerHTML = `
                <div class="notif-dropdown-header">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <strong style="font-size: 14px; color: var(--text);">Notifications</strong>
                        <span class="notif-count-pill" id="dropdown-header-count">${this.unreadCount} unread</span>
                    </div>
                    <button type="button" class="btn btn-sm btn-text" id="dropdown-mark-all-btn" style="font-size: 12px; color: var(--primary); background: transparent; border: none; cursor: pointer; padding: 2px 6px; font-weight: 600;">
                        Mark all read
                    </button>
                </div>
                <div class="notif-dropdown-list" id="notif-dropdown-items">
                    <div style="padding: 30px 16px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 20px; display: block; margin-bottom: 6px;"></i>
                        Loading recent updates...
                    </div>
                </div>
                <div class="notif-dropdown-footer">
                    <button type="button" class="btn btn-text" id="dropdown-view-all-btn" style="width: 100%; font-size: 13px; font-weight: 600; color: var(--primary); background: transparent; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px;">
                        View All Notifications <i class='bx bx-chevron-right'></i>
                    </button>
                </div>
            `;

            const markAllBtn = dropdown.querySelector('#dropdown-mark-all-btn');
            if (markAllBtn) {
                markAllBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    await this.markAllRead();
                });
            }

            const viewAllBtn = dropdown.querySelector('#dropdown-view-all-btn');
            if (viewAllBtn) {
                viewAllBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.closeDropdown();
                    window.location.hash = 'notifications';
                });
            }

            try {
                const data = await Api.getNotifications('limit=6');
                const itemsContainer = dropdown.querySelector('#notif-dropdown-items');
                if (!itemsContainer) return;

                if (!data || data.length === 0) {
                    itemsContainer.innerHTML = `
                        <div style="padding: 36px 16px; text-align: center; color: var(--text-secondary);">
                            <i class='bx bx-bell-off' style="font-size: 28px; opacity: 0.5; display: block; margin-bottom: 8px;"></i>
                            <div style="font-size: 13px; font-weight: 600;">No notifications</div>
                            <div style="font-size: 12px; margin-top: 2px;">You're all caught up!</div>
                        </div>
                    `;
                    return;
                }

                itemsContainer.innerHTML = data.map(n => {
                    const isUnread = !n.is_read;
                    const dateFormatted = Utils.formatDate(n.created_at);
                    const prio = n.priority || 'Normal';
                    const isHighPrio = prio === 'High' || prio === 'Critical';

                    return `
                        <div class="notif-dropdown-item ${isUnread ? 'unread' : ''}" data-id="${n.notification_id}" data-ref-type="${n.reference_type || ''}" data-ref-id="${n.reference_id || ''}">
                            <div style="margin-top: 2px;">
                                <span style="width: 28px; height: 28px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-size: 14px; background: ${isHighPrio ? 'rgba(239, 68, 68, 0.12)' : 'rgba(37, 99, 235, 0.1)'}; color: ${isHighPrio ? '#dc2626' : '#2563eb'};">
                                    <i class='bx ${isHighPrio ? 'bx-error-circle' : 'bx-bell'}'></i>
                                </span>
                            </div>
                            <div style="flex: 1; min-width: 0;">
                                <div style="display: flex; justify-content: space-between; align-items: baseline; gap: 6px; margin-bottom: 2px;">
                                    <span style="font-size: 13px; font-weight: ${isUnread ? '700' : '600'}; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                        ${Utils.escapeHtml(n.title)}
                                    </span>
                                    <span style="font-size: 11px; color: var(--text-light); white-space: nowrap;">
                                        ${dateFormatted}
                                    </span>
                                </div>
                                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 4px;">
                                    ${Utils.escapeHtml(n.message)}
                                </div>
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <span style="font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 4px; background: ${isHighPrio ? 'rgba(239, 68, 68, 0.1)' : 'rgba(107, 114, 128, 0.1)'}; color: ${isHighPrio ? '#dc2626' : '#4b5563'};">
                                        ${Utils.escapeHtml(prio)}
                                    </span>
                                    ${n.reference_type ? `
                                        <span style="font-size: 10px; color: var(--primary); font-weight: 500;">
                                            <i class='bx bx-link-external'></i> ${Utils.escapeHtml(n.reference_type)} #${Utils.escapeHtml(n.reference_id || '')}
                                        </span>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');

                itemsContainer.querySelectorAll('.notif-dropdown-item').forEach(item => {
                    item.addEventListener('click', async () => {
                        const notifId = item.dataset.id;
                        const refType = item.dataset.refType;
                        const refId = item.dataset.refId;
                        this.closeDropdown();
                        await App.navigateToReference(refType, refId, notifId);
                    });
                });

            } catch (err) {
                const itemsContainer = dropdown.querySelector('#notif-dropdown-items');
                if (itemsContainer) {
                    itemsContainer.innerHTML = `
                        <div style="padding: 24px 16px; text-align: center; color: #dc2626; font-size: 12px;">
                            Failed to load recent notifications.
                        </div>
                    `;
                }
            }
        },

        async markAllRead() {
            try {
                const res = await Api.markAllNotificationsRead();
                const count = res && res.updated_count !== undefined ? res.updated_count : 0;
                Utils.showToast(`Marked ${count} notification${count === 1 ? '' : 's'} as read`, 'success');
                await this.updateUnreadCount();
                if (this.isOpen) {
                    await this.loadRecent();
                }
                if (window.location.hash.includes('notifications') && App.pages['notifications'] && App.pages['notifications'].loadNotifications) {
                    App.pages['notifications'].loadNotifications();
                }
            } catch (err) {
                Utils.showToast(err.message || 'Failed to mark all as read', 'error');
            }
        }
    },

    // Step 7C Safe Reference Navigation
    async navigateToReference(referenceType, referenceId, notificationId = null) {
        if (notificationId) {
            try {
                await Api.markNotificationRead(notificationId);
                await this.notifications.updateUnreadCount();
                if (window.location.hash.includes('notifications') && this.pages['notifications'] && this.pages['notifications'].loadNotifications) {
                    this.pages['notifications'].loadNotifications();
                }
            } catch (e) {
                // Ignore silent read errors during navigation
            }
        }

        const user = Auth.getUser();
        if (!user) return;

        if (!referenceType || !referenceId) {
            window.location.hash = 'notifications';
            return;
        }

        const refType = referenceType.trim();
        const refId = referenceId;

        if (refType === 'Shipment') {
            const shipmentRoute = this.routes.find(r => r.path === 'shipments');
            if (shipmentRoute && shipmentRoute.roles.includes(user.role)) {
                window.location.hash = 'shipments';
                Utils.showToast(`Navigated to Shipment #${refId}`, 'info');
                setTimeout(() => {
                    if (this.pages['shipments'] && typeof this.pages['shipments'].openShipmentDetailsModal === 'function') {
                        this.pages['shipments'].openShipmentDetailsModal(refId);
                    }
                }, 400);
            } else {
                Utils.showToast(`Shipment module is not accessible for role ${user.role}`, 'warning');
            }
        } else if (refType === 'PurchaseOrder') {
            const poRoute = this.routes.find(r => r.path === 'purchase-orders');
            if (poRoute && poRoute.roles.includes(user.role)) {
                window.location.hash = 'purchase-orders';
                Utils.showToast(`Navigated to Purchase Order #${refId}`, 'info');
                setTimeout(() => {
                    const searchInput = document.getElementById('po-search');
                    if (searchInput) {
                        searchInput.value = refId;
                        if (this.pages['purchase-orders'] && typeof this.pages['purchase-orders'].loadPurchaseOrders === 'function') {
                            this.pages['purchase-orders'].loadPurchaseOrders();
                        }
                    }
                }, 400);
            } else {
                Utils.showToast(`Purchase Orders are restricted to Managers, Owners, and Suppliers`, 'warning');
            }
        } else if (refType === 'Product') {
            const prodRoute = this.routes.find(r => r.path === 'products');
            if (prodRoute && prodRoute.roles.includes(user.role)) {
                window.location.hash = 'products';
                Utils.showToast(`Navigated to Product #${refId}`, 'info');
                setTimeout(() => {
                    const searchInput = document.getElementById('product-search');
                    if (searchInput) {
                        searchInput.value = refId;
                        if (this.pages['products'] && typeof this.pages['products'].loadProducts === 'function') {
                            this.pages['products'].search = String(refId);
                            this.pages['products'].loadProducts();
                        }
                    }
                }, 400);
            } else {
                Utils.showToast(`Products module is not accessible for role ${user.role}`, 'warning');
            }
        } else {
            window.location.hash = 'notifications';
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
