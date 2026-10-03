// app.js

const App = {
    pages: {},
    
    routes: [
        { path: 'dashboard', icon: 'bx-grid-alt', label: 'Dashboard', roles: ['Owner', 'Manager', 'Employee', 'Supplier'] },
        { path: 'stock-requests', icon: 'bx-git-pull-request', label: 'Stock Requests', roles: ['Supplier'] },
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
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
