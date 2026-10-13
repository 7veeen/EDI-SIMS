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
        { path: 'payments', icon: 'bx-credit-card-front', label: 'Invoices & Payments', roles: ['Owner', 'Manager', 'Supplier'] },
        { path: 'supplier-invoices', icon: 'bx-receipt', label: 'Invoices & Payments', roles: ['Owner', 'Manager', 'Supplier'], hidden: true },
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
        this.search.init();
        this.profileDropdown.init();
        
        // Initial route
        const hash = window.location.hash.replace('#', '') || 'dashboard';
        this.navigate(hash);
    },

    initTheme() {
        let savedTheme = null;
        try {
            savedTheme = localStorage.getItem('sims_theme') || localStorage.getItem('theme') || localStorage.getItem('supplierTheme');
        } catch (storageErr) {
            // Storage access denied or unavailable -> fall back to OS preference
            savedTheme = null;
        }

        let isDark = false;
        if (savedTheme === 'dark') {
            isDark = true;
        } else if (savedTheme === 'light') {
            isDark = false;
        } else {
            // Storage threw, missing, or invalid preference: safely query OS preference
            try {
                if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    isDark = true;
                }
            } catch (mediaErr) {
                isDark = false;
            }
        }

        document.documentElement.classList.toggle('dark', isDark);
        document.documentElement.classList.toggle('dark-theme', isDark);
        if (document.body) {
            document.body.classList.toggle('dark', isDark);
            document.body.classList.toggle('dark-theme', isDark);
        }
        this.updateThemeIcon();
    },

    updateThemeIcon() {
        const themeBtns = [
            document.getElementById('themeToggle'),
            document.getElementById('loginThemeToggle'),
            document.getElementById('profileThemeToggle')
        ];
        const isDark = document.documentElement.classList.contains('dark') || (document.body && document.body.classList.contains('dark'));
        themeBtns.forEach(themeBtn => {
            if (!themeBtn) return;
            const i = themeBtn.querySelector('i');
            if (i) {
                i.className = isDark ? 'bx bx-sun' : 'bx bx-moon';
            }
            themeBtn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
            themeBtn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        });
        const themeText = document.getElementById('profile-theme-text');
        if (themeText) {
            themeText.textContent = isDark ? 'Light Mode' : 'Dark Mode';
        }
    },

    toggleTheme() {
        const currentlyDark = document.documentElement.classList.contains('dark') || (document.body && document.body.classList.contains('dark'));
        const isDark = !currentlyDark;

        document.documentElement.classList.toggle('dark', isDark);
        document.documentElement.classList.toggle('dark-theme', isDark);
        if (document.body) {
            document.body.classList.toggle('dark', isDark);
            document.body.classList.toggle('dark-theme', isDark);
        }

        try {
            localStorage.setItem('sims_theme', isDark ? 'dark' : 'light');
        } catch (e) {}

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

        // Update profile dropdown header
        const dropName = document.getElementById('dropdown-user-name');
        const dropRole = document.getElementById('dropdown-user-role');
        if (dropName) dropName.textContent = user.username;
        if (dropRole) dropRole.textContent = user.role;

        const navContainer = document.getElementById('sidebar-nav');
        navContainer.innerHTML = '<div class="nav-section-title">WORKSPACE</div>';

        this.routes.forEach(route => {
            if (route.roles.includes(user.role) && !route.hidden) {
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

        // Global Keyboard Shortcut: Ctrl+K or Cmd+K
        window.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
                // Do not steal focus if an active modal overlay is open
                if (document.querySelector('.modal-overlay.active')) return;

                // Do not intercept if user is composing text in a textarea or editable element
                const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
                const isEditable = document.activeElement && (document.activeElement.isContentEditable || activeTag === 'textarea');
                if (isEditable) return;

                e.preventDefault();
                App.search.focus();
            }
        });

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
        const navLookupPath = path === 'supplier-invoices' ? 'payments' : path;
        const activeNav = document.querySelector(`.nav-item[data-path="${navLookupPath}"]`);
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

        init() {
            this.setupDropdownListeners();
            // Note: Initial unread count is authoritatively fetched by App.navigate() during initial route bootstrap
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

            // Close other topbar popups
            if (App.profileDropdown && App.profileDropdown.isOpen) {
                App.profileDropdown.close();
            }
            if (App.search && App.search.isOpen) {
                App.search.close();
            }

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

    // Improvement 4: Safe Reference Type Normalizer
    normalizeReferenceType(type) {
        if (!type || typeof type !== 'string') return null;
        const clean = type.trim().toUpperCase().replace(/[\s_\-]+/g, '');
        if (!clean) return null;

        if (clean === 'SHIPMENT') return 'SHIPMENT';
        if (clean === 'PURCHASEORDER' || clean === 'PO') return 'PURCHASEORDER';
        if (clean === 'PRODUCT') return 'PRODUCT';
        if (clean === 'QUOTATION' || clean === 'SUPPLIERQUOTATION') return 'QUOTATION';
        if (clean === 'STOCKREQUEST') return 'STOCKREQUEST';
        if (clean === 'STOCKTRANSACTION' || clean === 'TRANSACTION') return 'STOCKTRANSACTION';
        if (clean === 'INVOICE' || clean === 'SUPPLIERINVOICE') return 'INVOICE';
        if (clean === 'PAYMENT' || clean === 'SUPPLIERPAYMENT') return 'PAYMENT';

        return null;
    },

    // Improvement 4: Safe Reference Deep-Link Navigation
    async navigateToReference(referenceType, referenceId, notificationId = null) {
        // 1. Mark notification as read if a valid notification ID is provided
        if (notificationId) {
            try {
                const parsedNotifId = parseInt(notificationId, 10);
                if (!isNaN(parsedNotifId)) {
                    await Api.markNotificationRead(parsedNotifId);
                    await this.notifications.updateUnreadCount();
                    if (window.location.hash.includes('notifications') && this.pages['notifications'] && typeof this.pages['notifications'].loadNotifications === 'function') {
                        this.pages['notifications'].loadNotifications();
                    }
                }
            } catch (e) {
                // Ignore silent read errors during navigation
            }
        }

        const user = Auth.getUser();
        if (!user) return;

        // 2. Validate reference type and reference ID
        const normType = this.normalizeReferenceType(referenceType);

        if (!normType) {
            if (referenceType && String(referenceType).trim()) {
                Utils.showToast(`Direct link unavailable for reference type: ${referenceType}`, 'warning');
            }
            if (!window.location.hash || window.location.hash === '#') {
                window.location.hash = 'notifications';
            }
            return;
        }

        if (referenceId === null || referenceId === undefined || String(referenceId).trim() === '') {
            Utils.showToast(`Notification does not contain a valid record reference ID`, 'warning');
            return;
        }

        const rawRefId = String(referenceId).trim();
        const parsedId = isNaN(Number(rawRefId)) ? rawRefId : Number(rawRefId);

        // 3. Define target route and action mapping
        const configMap = {
            'SHIPMENT': {
                path: 'shipments',
                actionType: 'modal',
                modalFn: 'openShipmentDetailsModal',
                entityName: 'Shipment'
            },
            'PURCHASEORDER': {
                path: 'purchase-orders',
                actionType: 'modal',
                modalFn: 'viewPODetails',
                entityName: 'Purchase Order'
            },
            'PRODUCT': {
                path: 'products',
                actionType: 'modal',
                modalFn: 'showProductModal',
                entityName: 'Product'
            },
            'QUOTATION': {
                path: 'quotations',
                actionType: 'modal',
                modalFn: 'openQuotationDetailsModal',
                entityName: 'Quotation'
            },
            'STOCKREQUEST': {
                path: 'stock-requests',
                actionType: 'modal',
                modalFn: 'openDetailsModal',
                entityName: 'Stock Request'
            },
            'STOCKTRANSACTION': {
                path: 'stock-transactions',
                actionType: 'filter',
                inputId: 'tx-search-input',
                filterFn: 'applyFilters',
                entityName: 'Stock Transaction'
            },
            'INVOICE': {
                path: 'payments',
                actionType: 'modal',
                modalFn: 'viewInvoiceDetails',
                entityName: 'Invoice'
            },
            'PAYMENT': {
                path: 'payments',
                actionType: 'modal',
                modalFn: 'viewPaymentVoucher',
                entityName: 'Payment Voucher'
            }
        };

        const config = configMap[normType];
        if (!config) {
            Utils.showToast(`Direct link unavailable for reference type: ${referenceType}`, 'warning');
            return;
        }

        // 4. Role-based access verification against App.routes
        const route = this.routes.find(r => r.path === config.path);
        if (!route || !route.roles.includes(user.role)) {
            Utils.showToast(`${config.entityName} module is not accessible for role ${user.role}`, 'warning');
            return;
        }

        // 5. Navigate to destination route
        if (window.location.hash !== '#' + config.path) {
            window.location.hash = config.path;
        } else {
            const contentArea = document.getElementById('content-area');
            if (contentArea && contentArea.children.length === 0) {
                this.navigate(config.path);
            }
        }

        Utils.showToast(`Navigated to ${config.entityName} #${parsedId}`, 'info');

        // 6. Polling dispatcher: cleanly wait for target page controller & modal function to be ready
        let attempts = 0;
        const maxAttempts = 15;
        const dispatchInterval = 50;

        const executeTargetAction = () => {
            const page = this.pages[config.path];

            if (config.actionType === 'modal') {
                if (page && typeof page[config.modalFn] === 'function') {
                    try {
                        page[config.modalFn](parsedId);
                    } catch (err) {
                        console.error(`[Deep-Link Error] Failed to open modal for ${config.entityName}:`, err);
                    }
                    return;
                }
            } else if (config.actionType === 'filter') {
                const searchInput = document.getElementById(config.inputId);
                if (page && searchInput && typeof page[config.filterFn] === 'function') {
                    try {
                        searchInput.value = String(parsedId);
                        page[config.filterFn]();
                    } catch (err) {
                        console.error(`[Deep-Link Error] Failed to filter ${config.entityName}:`, err);
                    }
                    return;
                }
            }

            if (attempts < maxAttempts) {
                attempts++;
                setTimeout(executeTargetAction, dispatchInterval);
            } else {
                console.warn(`[Deep-Link Warning] Could not invoke action for ${config.entityName} #${parsedId} after ${maxAttempts * dispatchInterval}ms`);
            }
        };

        setTimeout(executeTargetAction, 100);
    },

    getRouteForReference(normType) {
        const map = {
            'SHIPMENT': 'shipments',
            'PURCHASEORDER': 'purchase-orders',
            'PRODUCT': 'products',
            'QUOTATION': 'quotations',
            'STOCKREQUEST': 'stock-requests',
            'STOCKTRANSACTION': 'stock-transactions',
            'INVOICE': 'payments',
            'PAYMENT': 'payments'
        };
        return map[normType] || null;
    },

    // Global Search Controller
    search: {
        isOpen: false,
        debounceTimer: null,
        selectedIndex: -1,
        currentResults: [],

        init() {
            const input = document.getElementById('globalSearch');
            const clearBtn = document.getElementById('globalSearchClear');
            if (!input || input.dataset.listenerAttached) return;
            input.dataset.listenerAttached = 'true';

            input.addEventListener('input', () => {
                const q = input.value.trim();
                if (clearBtn) clearBtn.style.display = q ? 'inline-flex' : 'none';
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.performSearch(q);
                }, 160);
            });

            input.addEventListener('focus', () => {
                const q = input.value.trim();
                if (q) this.performSearch(q);
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.moveSelection(1);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.moveSelection(-1);
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    this.selectCurrent();
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    this.close();
                    input.blur();
                }
            });

            if (clearBtn) {
                clearBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    input.value = '';
                    clearBtn.style.display = 'none';
                    this.close();
                    input.focus();
                });
            }

            // Dismiss on outside click
            document.addEventListener('click', (e) => {
                const container = document.getElementById('globalSearchContainer');
                if (this.isOpen && container && !container.contains(e.target)) {
                    this.close();
                }
            });
        },

        focus() {
            const input = document.getElementById('globalSearch');
            if (input) {
                input.focus();
                input.select();
                const q = input.value.trim();
                if (q) this.performSearch(q);
            }
        },

        close() {
            const resultsContainer = document.getElementById('globalSearchResults');
            const input = document.getElementById('globalSearch');
            if (resultsContainer) resultsContainer.style.display = 'none';
            if (input) input.setAttribute('aria-expanded', 'false');
            this.isOpen = false;
            this.selectedIndex = -1;
            this.currentResults = [];
        },

        performSearch(query) {
            const resultsContainer = document.getElementById('globalSearchResults');
            const input = document.getElementById('globalSearch');
            if (!resultsContainer || !input) return;

            const cleanQuery = (query || '').trim().toLowerCase();
            if (!cleanQuery) {
                this.close();
                return;
            }

            const user = Auth.getUser();
            if (!user) return;

            const results = [];

            // 1. Role-Filtered Route Search
            const matchingRoutes = App.routes.filter(r => {
                if (!r.roles.includes(user.role) || r.hidden) return false;
                return r.label.toLowerCase().includes(cleanQuery) || r.path.toLowerCase().includes(cleanQuery);
            });

            matchingRoutes.forEach(r => {
                results.push({
                    type: 'route',
                    title: r.label,
                    desc: `Navigate to ${r.label}`,
                    icon: r.icon || 'bx-right-arrow-alt',
                    action: () => {
                        window.location.hash = r.path;
                    }
                });
            });

            // 2. Entity Reference Handling (Prefix Patterns)
            const entityMatch = cleanQuery.match(/^([a-z]+)[\s\-_#]*([0-9]+)$/i);
            if (entityMatch) {
                const prefix = entityMatch[1].toUpperCase();
                const recordId = parseInt(entityMatch[2], 10);
                const normType = App.normalizeReferenceType(prefix);

                if (normType && !isNaN(recordId)) {
                    const targetPath = App.getRouteForReference(normType);
                    const routeDef = App.routes.find(r => r.path === targetPath);

                    if (routeDef && routeDef.roles.includes(user.role)) {
                        // Present result only as navigation to the relevant module (clearly distinguished from verified records)
                        results.unshift({
                            type: 'reference-nav',
                            normType: normType,
                            recordId: recordId,
                            title: `Navigate to ${routeDef.label} (Ref: ${prefix}-${recordId})`,
                            desc: `Go to ${routeDef.label} module (unverified reference #${recordId})`,
                            icon: routeDef.icon || 'bx-right-arrow-alt',
                            action: () => {
                                window.location.hash = targetPath;
                            }
                        });

                        // Attempt authorization-aware verification if a suitable lookup exists
                        this.tryVerifyEntityRecord(normType, recordId, cleanQuery);
                    }
                }
            }

            this.currentResults = results;
            this.selectedIndex = results.length > 0 ? 0 : -1;
            this.renderResults(results, cleanQuery);
        },

        async tryVerifyEntityRecord(normType, recordId, query) {
            const user = Auth.getUser();
            if (!user) return;

            let lookupPromise = null;
            if (normType === 'PURCHASEORDER') {
                lookupPromise = Api.get(`/purchase-orders/${recordId}`);
            } else if (normType === 'INVOICE') {
                lookupPromise = Api.get(`/invoices/${recordId}`);
            } else if (normType === 'SHIPMENT') {
                lookupPromise = Api.get(`/shipments/${recordId}`);
            }

            if (!lookupPromise) {
                // No suitable single-record lookup exists for this entity type (e.g. Stock Requests, Quotations)
                // Result remains module navigation only, clearly distinguished from verified records
                return;
            }

            try {
                const data = await lookupPromise;
                const input = document.getElementById('globalSearch');
                const activeQuery = input ? input.value.trim().toLowerCase() : '';
                if (activeQuery !== query) return;

                let verifiedInfo = null;
                if (normType === 'PURCHASEORDER' && data && data.purchase_order) {
                    const po = data.purchase_order;
                    verifiedInfo = {
                        label: `Purchase Order #${recordId}`,
                        status: po.status || 'Active',
                        details: `Status: ${po.status || 'Active'} • Total: ₹${Number(po.total_amount || 0).toFixed(2)}`
                    };
                } else if (normType === 'INVOICE' && data && (data.invoice || data.id)) {
                    const inv = data.invoice || data;
                    verifiedInfo = {
                        label: `Invoice #${recordId}`,
                        status: inv.status || 'Active',
                        details: `Status: ${inv.status || 'Active'} • Amount: ₹${Number(inv.total_amount || 0).toFixed(2)}`
                    };
                } else if (normType === 'SHIPMENT' && data && data.shipment) {
                    const shp = data.shipment;
                    verifiedInfo = {
                        label: `Shipment #${recordId}`,
                        status: shp.status || 'Active',
                        details: `Status: ${shp.status || 'Active'} • Tracking: ${shp.tracking_number || 'N/A'}`
                    };
                }

                if (verifiedInfo) {
                    // Replace unverified reference-nav with verified record
                    this.currentResults = this.currentResults.filter(r => !(r.type === 'reference-nav' && r.normType === normType && r.recordId === recordId));
                    this.currentResults.unshift({
                        type: 'verified-record',
                        title: `Verified ${verifiedInfo.label}`,
                        desc: `${verifiedInfo.details} — Open verified details`,
                        icon: 'bx-check-shield',
                        action: async () => {
                            await App.navigateToReference(normType, recordId);
                        }
                    });
                    this.selectedIndex = 0;
                    this.renderResults(this.currentResults, query);
                }
            } catch (err) {
                // Record does not exist (404), access denied (403), or lookup failed.
                // Do NOT fabricate record details or claim record existence.
                // The item remains unverified module navigation only.
            }
        },

        formatEntityLabel(normType) {
            const map = {
                'PURCHASEORDER': 'Purchase Order',
                'SHIPMENT': 'Shipment',
                'INVOICE': 'Invoice',
                'PAYMENT': 'Payment Voucher',
                'QUOTATION': 'Quotation',
                'STOCKREQUEST': 'Stock Request',
                'STOCKTRANSACTION': 'Stock Transaction',
                'PRODUCT': 'Product'
            };
            return map[normType] || normType;
        },

        renderResults(results, query) {
            const container = document.getElementById('globalSearchResults');
            const input = document.getElementById('globalSearch');
            if (!container || !input) return;

            this.isOpen = true;
            container.style.display = 'flex';
            input.setAttribute('aria-expanded', 'true');

            if (results.length === 0) {
                container.innerHTML = `
                    <div class="search-empty-state">
                        <i class='bx bx-search-alt' style="font-size: 24px; opacity: 0.5; display: block; margin-bottom: 6px;"></i>
                        <div>No results found for "${Utils.escapeHtml(query)}"</div>
                        <div style="font-size: 11px; margin-top: 4px; color: var(--text-light);">Try searching for modules (e.g. "inventory", "reports") or records (e.g. "PO-12")</div>
                    </div>
                `;
                return;
            }

            let html = '';
            const verifiedResults = results.filter(r => r.type === 'verified-record');
            const refNavResults = results.filter(r => r.type === 'reference-nav');
            const routeResults = results.filter(r => r.type === 'route');

            if (verifiedResults.length > 0) {
                html += `<div class="search-result-group-title">Verified Records</div>`;
                verifiedResults.forEach(r => {
                    const globalIdx = results.indexOf(r);
                    html += this.renderResultItemHtml(r, globalIdx);
                });
            }

            if (refNavResults.length > 0) {
                html += `<div class="search-result-group-title">Module Navigation (Reference Pattern)</div>`;
                refNavResults.forEach(r => {
                    const globalIdx = results.indexOf(r);
                    html += this.renderResultItemHtml(r, globalIdx);
                });
            }

            if (routeResults.length > 0) {
                html += `<div class="search-result-group-title">Modules &amp; Pages</div>`;
                routeResults.forEach(r => {
                    const globalIdx = results.indexOf(r);
                    html += this.renderResultItemHtml(r, globalIdx);
                });
            }

            container.innerHTML = html;

            container.querySelectorAll('.search-result-item').forEach(itemEl => {
                const idx = parseInt(itemEl.dataset.index, 10);
                itemEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.executeResult(idx);
                });
            });

            this.updateActiveItemVisual();
        },

        renderResultItemHtml(r, idx) {
            const isSelected = idx === this.selectedIndex;
            return `
                <div class="search-result-item ${isSelected ? 'active' : ''}" data-index="${idx}" role="option" aria-selected="${isSelected}">
                    <i class='bx ${r.icon}'></i>
                    <div class="item-details">
                        <span class="item-title">${Utils.escapeHtml(r.title)}</span>
                        <span class="item-desc">${Utils.escapeHtml(r.desc)}</span>
                    </div>
                    <i class='bx bx-chevron-right' style="font-size: 16px; color: var(--text-light);"></i>
                </div>
            `;
        },

        moveSelection(direction) {
            if (!this.isOpen || this.currentResults.length === 0) return;
            this.selectedIndex += direction;
            if (this.selectedIndex < 0) {
                this.selectedIndex = this.currentResults.length - 1;
            } else if (this.selectedIndex >= this.currentResults.length) {
                this.selectedIndex = 0;
            }
            this.updateActiveItemVisual();
        },

        updateActiveItemVisual() {
            const container = document.getElementById('globalSearchResults');
            if (!container) return;
            const items = container.querySelectorAll('.search-result-item');
            items.forEach((item, idx) => {
                const isSel = idx === this.selectedIndex;
                item.classList.toggle('active', isSel);
                item.setAttribute('aria-selected', isSel ? 'true' : 'false');
                if (isSel) {
                    item.scrollIntoView({ block: 'nearest' });
                }
            });
        },

        selectCurrent() {
            if (this.selectedIndex >= 0 && this.selectedIndex < this.currentResults.length) {
                this.executeResult(this.selectedIndex);
            }
        },

        executeResult(idx) {
            const res = this.currentResults[idx];
            if (res && typeof res.action === 'function') {
                this.close();
                res.action();
            }
        }
    },

    // User Profile Dropdown Controller
    profileDropdown: {
        isOpen: false,

        init() {
            const btn = document.getElementById('topProfileBtn');
            if (!btn || btn.dataset.listenerAttached) return;
            btn.dataset.listenerAttached = 'true';

            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggle();
            });

            // Change password button click
            const changePassBtn = document.getElementById('change-password-btn');
            if (changePassBtn) {
                changePassBtn.addEventListener('click', () => {
                    this.close();
                });
            }

            // Profile theme toggle
            const profileThemeBtn = document.getElementById('profileThemeToggle');
            if (profileThemeBtn) {
                profileThemeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    App.toggleTheme();
                });
            }

            // Logout button click
            const logoutBtn = document.getElementById('profile-logout-btn');
            if (logoutBtn) {
                logoutBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.close();
                    Auth.logout();
                });
            }

            // Close on outside click
            document.addEventListener('click', (e) => {
                const wrapper = document.getElementById('topProfileWrapper');
                if (this.isOpen && wrapper && !wrapper.contains(e.target)) {
                    this.close();
                }
            });

            // Close on Escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.close();
                    btn.focus();
                }
            });
        },

        toggle() {
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        },

        open() {
            const dropdown = document.getElementById('profileDropdown');
            const btn = document.getElementById('topProfileBtn');
            if (!dropdown || !btn) return;

            // Mutual exclusion: close other popups
            if (App.notifications && App.notifications.isOpen) {
                App.notifications.closeDropdown();
            }
            if (App.search && App.search.isOpen) {
                App.search.close();
            }

            const user = Auth.getUser();
            if (user) {
                const nameEl = document.getElementById('dropdown-user-name');
                const roleEl = document.getElementById('dropdown-user-role');
                if (nameEl) nameEl.textContent = user.username || 'User';
                if (roleEl) roleEl.textContent = user.role || 'Role';
            }

            this.isOpen = true;
            dropdown.style.display = 'flex';
            btn.setAttribute('aria-expanded', 'true');
        },

        close() {
            const dropdown = document.getElementById('profileDropdown');
            const btn = document.getElementById('topProfileBtn');
            if (!dropdown) return;

            this.isOpen = false;
            dropdown.style.display = 'none';
            if (btn) btn.setAttribute('aria-expanded', 'false');
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
