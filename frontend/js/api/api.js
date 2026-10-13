// api.js

const API_BASE_URL = 'http://127.0.0.1:5000/api';

const Api = {
    // In-flight request tracker for safe concurrent GET deduplication
    _inFlightRequests: new Map(),

    clearInFlightRequests() {
        if (this._inFlightRequests) {
            this._inFlightRequests.clear();
        }
    },

    request(endpoint, options = {}) {
        const token = (typeof localStorage !== 'undefined')
            ? (localStorage.getItem('sims_token') || localStorage.getItem('sims_access_token'))
            : null;
        const method = (options.method || 'GET').toUpperCase();

        // Only deduplicate safe idempotent read requests (GET, HEAD)
        // Never deduplicate mutation requests (POST, PUT, PATCH, DELETE)
        const isSafeMethod = method === 'GET' || method === 'HEAD';
        const dedupKey = isSafeMethod ? `${method}:${token || 'anon'}:${endpoint}` : null;

        if (dedupKey && this._inFlightRequests.has(dedupKey)) {
            return this._inFlightRequests.get(dedupKey);
        }

        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            method,
            headers
        };

        const executeFetch = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
                
                // Handle 401 Unauthorized globally, except for login
                if (response.status === 401 && !endpoint.includes('/auth/login')) {
                    if (typeof Auth !== 'undefined' && typeof Auth.logout === 'function') {
                        Auth.logout();
                    }
                    throw new Error("Session expired. Please login again.");
                }

                const data = await response.json().catch(() => null);

                if (!response.ok) {
                    // If it's a 403, 400, 423, etc.
                    const errorMessage = data?.error || `Error: ${response.status} ${response.statusText}`;
                    throw { status: response.status, message: errorMessage };
                }

                return data;
            } catch (error) {
                if (error && error.status !== undefined) {
                    throw error;
                }
                throw { status: 0, message: error?.message || "Network error or server is unreachable." };
            } finally {
                // Ensure entry is immediately removed upon resolution or rejection
                if (dedupKey) {
                    this._inFlightRequests.delete(dedupKey);
                }
            }
        };

        const requestPromise = executeFetch();

        if (dedupKey) {
            this._inFlightRequests.set(dedupKey, requestPromise);
        }

        return requestPromise;
    },

    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    patch(endpoint, data) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    // Notification helpers (Step 7A)
    async getNotifications(params = '') {
        const query = params ? `?${params}` : '';
        return this.get(`/notifications/${query}`);
    },

    async getNotification(id) {
        return this.get(`/notifications/${id}`);
    },

    async getUnreadNotificationCount() {
        return this.get('/notifications/unread-count');
    },

    async markNotificationRead(id) {
        return this.patch(`/notifications/${id}/read`);
    },

    async markAllNotificationsRead() {
        return this.patch('/notifications/read-all');
    },

    // Reports helpers (Phase 2)
    async getReports() {
        return this.get('/reports/');
    },

    async getReport(id) {
        return this.get(`/reports/${id}`);
    },

    async getReportStatus() {
        return this.get('/reports/status');
    },

    async generateReport(data) {
        return this.post('/reports/generate', data);
    },

    // Invoices helpers (Phase 3)
    async getInvoices(params = '') {
        let query = '';
        if (typeof params === 'string') {
            query = params ? `?${params}` : '';
        } else if (params && typeof params === 'object') {
            const searchParams = new URLSearchParams();
            Object.entries(params).forEach(([key, val]) => {
                if (val !== undefined && val !== null && val !== '') {
                    searchParams.append(key, val);
                }
            });
            const qStr = searchParams.toString();
            query = qStr ? `?${qStr}` : '';
        }
        return this.get(`/invoices${query}`);
    },

    async getInvoice(id) {
        return this.get(`/invoices/${id}`);
    },

    async submitInvoice(data) {
        return this.post('/invoices', data);
    },

    async approveInvoice(id) {
        return this.patch(`/invoices/${id}/approve`, {});
    },

    async rejectInvoice(id, rejection_reason) {
        return this.patch(`/invoices/${id}/reject`, { rejection_reason });
    },

    async cancelInvoice(id, reason = '') {
        return this.patch(`/invoices/${id}/cancel`, { reason });
    },

    async getInvoicePayments(id) {
        return this.get(`/invoices/${id}/payments`);
    },

    // Payments helpers (Phase 3)
    async getPayments(params = '') {
        let query = '';
        if (typeof params === 'string') {
            query = params ? `?${params}` : '';
        } else if (params && typeof params === 'object') {
            const searchParams = new URLSearchParams();
            Object.entries(params).forEach(([key, val]) => {
                if (val !== undefined && val !== null && val !== '') {
                    searchParams.append(key, val);
                }
            });
            const qStr = searchParams.toString();
            query = qStr ? `?${qStr}` : '';
        }
        return this.get(`/payments${query}`);
    },

    async getPayment(id) {
        return this.get(`/payments/${id}`);
    },

    async recordPayment(data) {
        return this.post('/payments', data);
    }
};
