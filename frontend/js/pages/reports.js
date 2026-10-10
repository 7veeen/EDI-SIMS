// reports.js

App.pages['reports'] = {
    allReports: [],
    filteredReports: [],
    searchQuery: '',
    startDate: '',
    endDate: '',
    snapshotFilter: 'all',
    sortField: 'report_id',
    sortDirection: 'desc',
    currentPage: 1,
    pageSize: 10,

    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
                <div id="inventory-status" style="display:flex; align-items:center; gap: 0.5rem">
                    <span class="status-badge status-pending">Checking Inventory Status...</span>
                </div>
                <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;">
                    <button class="btn btn-secondary" id="btn-export-csv" title="Download current live inventory balance as CSV">
                        <i class='bx bx-download'></i> Export CSV (Current Balance)
                    </button>
                    <button class="btn btn-primary" id="btn-generate-report">
                        <i class='bx bx-plus-circle'></i> Generate Report
                    </button>
                </div>
            </div>

            <!-- Summary Metric Cards (Phase 3) -->
            <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 16px 0;">
                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Total Reports</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-file'></i>
                        </div>
                    </div>
                    <div id="stat-total-reports" style="font-size: 24px; font-weight: 700; color: var(--text); line-height: 1.2;">--</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">All historical records</div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Saved Snapshots</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #ecfdf5; color: #059669; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-check-shield'></i>
                        </div>
                    </div>
                    <div id="stat-saved-snapshots" style="font-size: 24px; font-weight: 700; color: #059669; line-height: 1.2;">--</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Point-in-time data saved</div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Legacy Reports</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #fffbeb; color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-time-five'></i>
                        </div>
                    </div>
                    <div id="stat-legacy-reports" style="font-size: 24px; font-weight: 700; color: #d97706; line-height: 1.2;">--</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Metadata only (pre-Phase 2)</div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Matching View</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #f5f3ff; color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-filter-alt'></i>
                        </div>
                    </div>
                    <div id="stat-matching-reports" style="font-size: 24px; font-weight: 700; color: #7c3aed; line-height: 1.2;">--</div>
                    <div id="stat-matching-subtext" style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Current table view</div>
                </div>
            </div>

            <!-- Search, Date Filter, and Controls Toolbar (Phase 3) -->
            <div class="card" style="margin-bottom: 16px; padding: 14px 16px; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); display: flex; flex-direction: column; gap: 10px;">
                <div style="display: flex; gap: 10px; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                    <!-- Search Input -->
                    <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border); border-radius: 8px; flex: 1; min-width: 240px; max-width: 380px; display: flex; align-items: center; padding: 0 10px; height: 38px;">
                        <i class='bx bx-search' style="color: var(--text-secondary); font-size: 18px; margin-right: 6px;"></i>
                        <input type="text" id="reports-search" placeholder="Search by name, type, ID, creator..." style="background: transparent; border: none; outline: none; width: 100%; font-size: 13.5px; color: var(--text);">
                        <button id="btn-clear-search" style="display: none; background: transparent; border: none; cursor: pointer; color: var(--text-secondary); font-size: 18px; padding: 0 4px;" title="Clear search">&times;</button>
                    </div>

                    <!-- Date Range Filter -->
                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                        <div style="display: flex; align-items: center; gap: 4px;">
                            <label for="report-start-date" style="font-size: 12.5px; font-weight: 500; color: var(--text-secondary);">From:</label>
                            <input type="date" id="report-start-date" class="input" style="padding: 5px 8px; font-size: 12.5px; border: 1px solid var(--border); border-radius: 6px; background: var(--white); height: 36px;">
                        </div>
                        <div style="display: flex; align-items: center; gap: 4px;">
                            <label for="report-end-date" style="font-size: 12.5px; font-weight: 500; color: var(--text-secondary);">To:</label>
                            <input type="date" id="report-end-date" class="input" style="padding: 5px 8px; font-size: 12.5px; border: 1px solid var(--border); border-radius: 6px; background: var(--white); height: 36px;">
                        </div>
                        <button class="btn btn-outline" id="btn-apply-dates" style="height: 36px; padding: 0 12px; font-size: 12.5px; display: inline-flex; align-items: center; gap: 4px; border-radius: 6px;">
                            <i class='bx bx-calendar'></i> Filter Date
                        </button>
                    </div>

                    <!-- Snapshot Filter, Page Size & Reset -->
                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                        <select id="report-snapshot-filter" class="filter-select" style="height: 36px; font-size: 12.5px; border-radius: 6px; padding: 0 8px;">
                            <option value="all">All Snapshots</option>
                            <option value="saved">Saved Only</option>
                            <option value="legacy">Legacy Only</option>
                        </select>
                        <select id="report-page-size" class="filter-select" style="height: 36px; font-size: 12.5px; border-radius: 6px; padding: 0 8px;">
                            <option value="10">10 / page</option>
                            <option value="25">25 / page</option>
                            <option value="50">50 / page</option>
                        </select>
                        <button class="btn btn-secondary" id="btn-reset-filters" style="height: 36px; padding: 0 12px; font-size: 12.5px; display: inline-flex; align-items: center; gap: 4px; border-radius: 6px;" title="Reset all search, date, and snapshot filters">
                            <i class='bx bx-reset'></i> Reset Filters
                        </button>
                    </div>
                </div>

                <!-- Active Filters Pill Banner -->
                <div id="active-filters-pill" style="display: none; align-items: center; gap: 8px; font-size: 12px; padding: 6px 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; color: #166534;">
                    <i class='bx bx-filter-alt'></i>
                    <span id="active-filters-desc">Filters Active</span>
                    <button id="btn-pill-clear" style="margin-left: auto; background: none; border: none; color: #dc2626; font-size: 12px; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 2px;">
                        <i class='bx bx-x'></i> Clear All
                    </button>
                </div>
            </div>
            
            <!-- Reports Table with Sortable Columns (Phase 3) -->
            <div class="glass-panel table-container">
                <table id="reports-table">
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="report_id" title="Click to sort by ID" style="cursor: pointer; user-select: none;">
                                ID <i class='bx bx-sort-down' id="sort-icon-report_id"></i>
                            </th>
                            <th class="sortable" data-sort="report_name" title="Click to sort by Report Name" style="cursor: pointer; user-select: none;">
                                Report Name <i class='bx bx-sort' id="sort-icon-report_name"></i>
                            </th>
                            <th class="sortable" data-sort="report_type" title="Click to sort by Type" style="cursor: pointer; user-select: none;">
                                Type <i class='bx bx-sort' id="sort-icon-report_type"></i>
                            </th>
                            <th class="sortable" data-sort="generated_by" title="Click to sort by Creator" style="cursor: pointer; user-select: none;">
                                Generated By <i class='bx bx-sort' id="sort-icon-generated_by"></i>
                            </th>
                            <th class="sortable" data-sort="generated_on" title="Click to sort by Date" style="cursor: pointer; user-select: none;">
                                Generated On <i class='bx bx-sort' id="sort-icon-generated_on"></i>
                            </th>
                            <th class="sortable" data-sort="has_snapshot" title="Click to sort by Snapshot" style="cursor: pointer; user-select: none;">
                                Snapshot <i class='bx bx-sort' id="sort-icon-has_snapshot"></i>
                            </th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>

                <!-- Pagination Bar (Phase 3) -->
                <div class="table-pagination" id="reports-pagination">
                    <div class="pagination-info" id="reports-pagination-info">Showing 0 of 0 reports</div>
                    <div class="pagination-controls" id="reports-pagination-controls"></div>
                </div>
            </div>
        `;
        return container;
    },

    async init() {
        this.checkInventoryStatus();
        this.loadReports();

        document.getElementById('btn-generate-report')?.addEventListener('click', () => {
            this.openGenerateReportModal();
        });

        document.getElementById('btn-export-csv')?.addEventListener('click', () => {
            this.exportCsv();
        });

        // Search input handling with live filtering
        const searchInput = document.getElementById('reports-search');
        const clearSearchBtn = document.getElementById('btn-clear-search');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.searchQuery = e.target.value;
                    if (clearSearchBtn) {
                        clearSearchBtn.style.display = this.searchQuery ? 'inline-block' : 'none';
                    }
                    this.currentPage = 1;
                    this.applyFiltersAndSort();
                }, 150);
            });
        }
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                if (searchInput) searchInput.value = '';
                clearSearchBtn.style.display = 'none';
                this.searchQuery = '';
                this.currentPage = 1;
                this.applyFiltersAndSort();
            });
        }

        // Date filter button
        document.getElementById('btn-apply-dates')?.addEventListener('click', () => {
            this.applyDateFilter();
        });

        // Date input Enter key support
        ['report-start-date', 'report-end-date'].forEach(id => {
            document.getElementById(id)?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.applyDateFilter();
                }
            });
        });

        // Snapshot filter dropdown
        document.getElementById('report-snapshot-filter')?.addEventListener('change', (e) => {
            this.snapshotFilter = e.target.value;
            this.currentPage = 1;
            this.applyFiltersAndSort();
        });

        // Page size dropdown
        document.getElementById('report-page-size')?.addEventListener('change', (e) => {
            this.pageSize = Number(e.target.value) || 10;
            this.currentPage = 1;
            this.applyFiltersAndSort();
        });

        // Reset filters button & pill clear button
        document.getElementById('btn-reset-filters')?.addEventListener('click', () => {
            this.resetFilters();
        });
        document.getElementById('btn-pill-clear')?.addEventListener('click', () => {
            this.resetFilters();
        });

        // Sortable headers click handling
        document.querySelectorAll('#reports-table th.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const field = th.dataset.sort;
                if (!field) return;
                if (this.sortField === field) {
                    this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortField = field;
                    this.sortDirection = (field === 'report_id' || field === 'generated_on') ? 'desc' : 'asc';
                }
                this.currentPage = 1;
                this.applyFiltersAndSort();
            });
        });

        // Pagination controls click handling
        const paginationControls = document.getElementById('reports-pagination-controls');
        if (paginationControls) {
            paginationControls.addEventListener('click', (e) => {
                const btn = e.target.closest('.pagination-btn');
                if (!btn || btn.disabled) return;
                if (btn.id === 'btn-page-prev') {
                    this.goToPage(this.currentPage - 1);
                } else if (btn.id === 'btn-page-next') {
                    this.goToPage(this.currentPage + 1);
                } else if (btn.dataset.page) {
                    this.goToPage(Number(btn.dataset.page));
                }
            });
        }

        // Table View Details button event delegation
        const table = document.getElementById('reports-table');
        if (table) {
            table.addEventListener('click', (e) => {
                const btn = e.target.closest('.btn-view-report');
                if (btn) {
                    const id = btn.getAttribute('data-id');
                    if (id) {
                        this.viewReportDetails(id);
                    }
                }
            });
        }
    },

    async checkInventoryStatus() {
        const statusEl = document.getElementById('inventory-status');
        try {
            const data = (typeof Api.getReportStatus === 'function')
                ? await Api.getReportStatus()
                : await Api.get('/reports/status');
            
            let statusClass = 'status-active';
            if (data.status !== 'READY') statusClass = 'status-pending';

            statusEl.innerHTML = `
                <span class="status-badge ${statusClass}">Inventory: ${data.status}</span>
                <span style="font-size: 0.85rem; color: var(--gray)">${data.message || ''}</span>
            `;
        } catch (error) {
            statusEl.innerHTML = `<span class="status-badge status-inactive">Status Unavailable</span>`;
        }
    },

    async loadReports() {
        const tbody = document.querySelector('#reports-table tbody');
        try {
            const data = (typeof Api.getReports === 'function')
                ? await Api.getReports()
                : await Api.get('/reports/');
            this.allReports = Array.isArray(data) ? data : [];
            this.applyFiltersAndSort();
        } catch (error) {
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-danger" style="text-align: center;">Failed to load reports: ${Utils.escapeHtml(error.message || 'Error')}</td></tr>`;
            }
        }
    },

    applyDateFilter() {
        const startInput = document.getElementById('report-start-date');
        const endInput = document.getElementById('report-end-date');
        const startVal = startInput ? startInput.value : '';
        const endVal = endInput ? endInput.value : '';

        if (startVal && endVal && startVal > endVal) {
            Utils.showToast("Start date cannot be after end date.", "warning");
            return;
        }

        this.startDate = startVal;
        this.endDate = endVal;
        this.currentPage = 1;
        this.applyFiltersAndSort();
    },

    resetFilters() {
        this.searchQuery = '';
        this.startDate = '';
        this.endDate = '';
        this.snapshotFilter = 'all';
        this.sortField = 'report_id';
        this.sortDirection = 'desc';
        this.currentPage = 1;

        const searchInput = document.getElementById('reports-search');
        if (searchInput) searchInput.value = '';
        const clearBtn = document.getElementById('btn-clear-search');
        if (clearBtn) clearBtn.style.display = 'none';
        const startInput = document.getElementById('report-start-date');
        if (startInput) startInput.value = '';
        const endInput = document.getElementById('report-end-date');
        if (endInput) endInput.value = '';
        const snapSelect = document.getElementById('report-snapshot-filter');
        if (snapSelect) snapSelect.value = 'all';

        this.applyFiltersAndSort();
    },

    isAnyFilterActive() {
        return Boolean(
            (this.searchQuery && this.searchQuery.trim()) ||
            this.startDate ||
            this.endDate ||
            (this.snapshotFilter && this.snapshotFilter !== 'all')
        );
    },

    applyFiltersAndSort() {
        let list = [...this.allReports];

        // 1. Search Query
        if (this.searchQuery && this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase().trim();
            list = list.filter(r => {
                const idStr = String(r.report_id);
                const nameStr = (r.report_name || '').toLowerCase();
                const typeStr = (r.report_type || '').toLowerCase();
                const userStr = (r.generated_by_username || '').toLowerCase();
                const userIdStr = String(r.generated_by || '');
                return idStr.includes(q) ||
                       nameStr.includes(q) ||
                       typeStr.includes(q) ||
                       userStr.includes(q) ||
                       userIdStr.includes(q);
            });
        }

        // 2. Date Range Filter
        if (this.startDate) {
            const start = new Date(this.startDate + 'T00:00:00');
            if (!isNaN(start.getTime())) {
                list = list.filter(r => {
                    if (!r.generated_on) return false;
                    const d = new Date(r.generated_on);
                    return !isNaN(d.getTime()) && d >= start;
                });
            }
        }

        if (this.endDate) {
            const end = new Date(this.endDate + 'T23:59:59.999');
            if (!isNaN(end.getTime())) {
                list = list.filter(r => {
                    if (!r.generated_on) return false;
                    const d = new Date(r.generated_on);
                    return !isNaN(d.getTime()) && d <= end;
                });
            }
        }

        // 3. Snapshot Filter
        if (this.snapshotFilter === 'saved') {
            list = list.filter(r => Boolean(r.has_snapshot));
        } else if (this.snapshotFilter === 'legacy') {
            list = list.filter(r => !r.has_snapshot);
        }

        // 4. Sorting
        list.sort((a, b) => {
            let valA, valB;
            if (this.sortField === 'report_id') {
                valA = Number(a.report_id) || 0;
                valB = Number(b.report_id) || 0;
                return this.sortDirection === 'asc' ? valA - valB : valB - valA;
            } else if (this.sortField === 'generated_on') {
                valA = a.generated_on ? new Date(a.generated_on).getTime() : 0;
                valB = b.generated_on ? new Date(b.generated_on).getTime() : 0;
                return this.sortDirection === 'asc' ? valA - valB : valB - valA;
            } else if (this.sortField === 'has_snapshot') {
                valA = a.has_snapshot ? 1 : 0;
                valB = b.has_snapshot ? 1 : 0;
                return this.sortDirection === 'asc' ? valA - valB : valB - valA;
            } else if (this.sortField === 'generated_by') {
                valA = (a.generated_by_username || String(a.generated_by) || '').toLowerCase();
                valB = (b.generated_by_username || String(b.generated_by) || '').toLowerCase();
                const cmp = valA.localeCompare(valB);
                return this.sortDirection === 'asc' ? cmp : -cmp;
            } else {
                valA = (a[this.sortField] || '').toLowerCase();
                valB = (b[this.sortField] || '').toLowerCase();
                const cmp = valA.localeCompare(valB);
                return this.sortDirection === 'asc' ? cmp : -cmp;
            }
        });

        this.filteredReports = list;

        // Clamp current page
        const totalPages = Math.ceil(this.filteredReports.length / this.pageSize) || 1;
        if (this.currentPage > totalPages) {
            this.currentPage = totalPages;
        }
        if (this.currentPage < 1) {
            this.currentPage = 1;
        }

        this.updateSummaryCards();
        this.updateActiveFilterBanner();
        this.updateSortHeaders();
        this.renderTablePage();
        this.renderPagination();
    },

    updateSummaryCards() {
        const totalEl = document.getElementById('stat-total-reports');
        const savedEl = document.getElementById('stat-saved-snapshots');
        const legacyEl = document.getElementById('stat-legacy-reports');
        const matchEl = document.getElementById('stat-matching-reports');
        const matchSubEl = document.getElementById('stat-matching-subtext');

        const total = this.allReports.length;
        const saved = this.allReports.filter(r => r.has_snapshot).length;
        const legacy = this.allReports.filter(r => !r.has_snapshot).length;
        const matching = this.filteredReports.length;

        if (totalEl) totalEl.textContent = total.toLocaleString();
        if (savedEl) savedEl.textContent = saved.toLocaleString();
        if (legacyEl) legacyEl.textContent = legacy.toLocaleString();
        if (matchEl) matchEl.textContent = matching.toLocaleString();

        const isFiltered = this.isAnyFilterActive();
        if (matchSubEl) {
            matchSubEl.textContent = isFiltered ? 'Matches active filters' : 'All reports showing';
        }
    },

    updateActiveFilterBanner() {
        const pillEl = document.getElementById('active-filters-pill');
        const descEl = document.getElementById('active-filters-desc');
        if (!pillEl || !descEl) return;

        if (!this.isAnyFilterActive()) {
            pillEl.style.display = 'none';
            return;
        }

        const parts = [];
        if (this.searchQuery && this.searchQuery.trim()) {
            parts.push(`Search: "${Utils.escapeHtml(this.searchQuery.trim())}"`);
        }
        if (this.startDate && this.endDate) {
            parts.push(`Date: ${this.startDate} to ${this.endDate}`);
        } else if (this.startDate) {
            parts.push(`From: ${this.startDate}`);
        } else if (this.endDate) {
            parts.push(`To: ${this.endDate}`);
        }
        if (this.snapshotFilter === 'saved') {
            parts.push(`Saved Only`);
        } else if (this.snapshotFilter === 'legacy') {
            parts.push(`Legacy Only`);
        }

        descEl.innerHTML = `<strong>Active Filters:</strong> ${parts.join(' &bull; ')}`;
        pillEl.style.display = 'flex';
    },

    updateSortHeaders() {
        document.querySelectorAll('#reports-table th.sortable').forEach(th => {
            const field = th.dataset.sort;
            const icon = th.querySelector('i');
            if (!icon) return;
            if (field === this.sortField) {
                th.classList.add('sorted');
                if (this.sortDirection === 'asc') {
                    icon.className = 'bx bx-sort-up';
                } else {
                    icon.className = 'bx bx-sort-down';
                }
            } else {
                th.classList.remove('sorted');
                icon.className = 'bx bx-sort';
            }
        });
    },

    renderTablePage() {
        const tbody = document.querySelector('#reports-table tbody');
        if (!tbody) return;

        if (this.allReports.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">No reports generated yet.</td></tr>`;
            return;
        }

        if (this.filteredReports.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2.5rem 1rem; color: var(--gray);">
                        <i class='bx bx-search-alt' style="font-size: 2.5rem; display: block; margin-bottom: 0.5rem; color: var(--text-secondary);"></i>
                        <strong style="font-size: 1rem; color: var(--text);">No matching reports found</strong>
                        <p style="margin: 0.25rem 0 0.75rem 0; font-size: 0.85rem;">No reports match your current search query or date range filters.</p>
                        <button class="btn btn-sm btn-outline" id="btn-empty-clear-filters">
                            <i class='bx bx-reset'></i> Reset Filters
                        </button>
                    </td>
                </tr>
            `;
            document.getElementById('btn-empty-clear-filters')?.addEventListener('click', () => {
                this.resetFilters();
            });
            return;
        }

        const startIdx = (this.currentPage - 1) * this.pageSize;
        const endIdx = startIdx + this.pageSize;
        const pageItems = this.filteredReports.slice(startIdx, endIdx);

        tbody.innerHTML = pageItems.map(r => {
            let typeBadgeStyle = 'background: rgba(37, 99, 235, 0.1); color: #2563eb; font-weight: 600; padding: 2px 8px; border-radius: 4px;';
            if (r.report_type === 'Stock Transactions') {
                typeBadgeStyle = 'background: rgba(124, 58, 237, 0.1); color: #7c3aed; font-weight: 600; padding: 2px 8px; border-radius: 4px;';
            } else if (r.report_type === 'Purchase Orders') {
                typeBadgeStyle = 'background: rgba(5, 150, 105, 0.1); color: #059669; font-weight: 600; padding: 2px 8px; border-radius: 4px;';
            } else if (r.report_type === 'Quotations') {
                typeBadgeStyle = 'background: rgba(217, 119, 6, 0.1); color: #d97706; font-weight: 600; padding: 2px 8px; border-radius: 4px;';
            } else if (r.report_type === 'Supplier Performance') {
                typeBadgeStyle = 'background: rgba(14, 165, 233, 0.1); color: #0284c7; font-weight: 600; padding: 2px 8px; border-radius: 4px;';
            } else if (r.report_type === 'Audit Trail') {
                typeBadgeStyle = 'background: rgba(71, 85, 105, 0.1); color: #334155; font-weight: 600; padding: 2px 8px; border-radius: 4px;';
            }

            return `
            <tr>
                <td><strong>#${r.report_id}</strong></td>
                <td><strong>${Utils.escapeHtml(r.report_name)}</strong></td>
                <td><span class="badge" style="position: relative; top:0; ${typeBadgeStyle}">${Utils.escapeHtml(r.report_type)}</span></td>
                <td>${Utils.escapeHtml(r.generated_by_username || ('User #' + r.generated_by))}</td>
                <td>${Utils.formatDate(r.generated_on)}</td>
                <td>
                    ${r.has_snapshot ? 
                        '<span class="status-badge status-active" style="font-size: 0.75rem;"><i class="bx bx-check"></i> Saved</span>' : 
                        '<span class="status-badge status-inactive" style="font-size: 0.75rem;"><i class="bx bx-time-five"></i> Legacy</span>'}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline btn-view-report" data-id="${r.report_id}" title="View Report Details">
                        <i class='bx bx-show'></i> View Details
                    </button>
                </td>
            </tr>
            `;
        }).join('');
    },

    renderPagination() {
        const infoEl = document.getElementById('reports-pagination-info');
        const controlsEl = document.getElementById('reports-pagination-controls');
        if (!infoEl || !controlsEl) return;

        const total = this.filteredReports.length;
        if (total === 0) {
            infoEl.textContent = 'Showing 0 of 0 reports';
            controlsEl.innerHTML = '';
            return;
        }

        const start = (this.currentPage - 1) * this.pageSize + 1;
        const end = Math.min(this.currentPage * this.pageSize, total);
        const totalPages = Math.ceil(total / this.pageSize) || 1;

        infoEl.textContent = `Showing ${start}–${end} of ${total} reports`;

        let html = `
            <button class="pagination-btn" id="btn-page-prev" ${this.currentPage <= 1 ? 'disabled' : ''} title="Previous Page">
                <i class='bx bx-chevron-left'></i> Prev
            </button>
        `;

        for (let p = 1; p <= totalPages; p++) {
            if (p === 1 || p === totalPages || (p >= this.currentPage - 1 && p <= this.currentPage + 1)) {
                html += `
                    <button class="pagination-btn ${p === this.currentPage ? 'active' : ''}" data-page="${p}">
                        ${p}
                    </button>
                `;
            } else if (p === this.currentPage - 2 || p === this.currentPage + 2) {
                html += `<span style="padding: 0 4px; color: var(--text-light);">...</span>`;
            }
        }

        html += `
            <button class="pagination-btn" id="btn-page-next" ${this.currentPage >= totalPages ? 'disabled' : ''} title="Next Page">
                Next <i class='bx bx-chevron-right'></i>
            </button>
        `;

        controlsEl.innerHTML = html;
    },

    goToPage(p) {
        const totalPages = Math.ceil(this.filteredReports.length / this.pageSize) || 1;
        if (p < 1 || p > totalPages || p === this.currentPage) return;
        this.currentPage = p;
        this.renderTablePage();
        this.renderPagination();
    },

    openGenerateReportModal() {
        const todayStr = new Date().toISOString().slice(0, 10);
        Modal.create({
            id: 'modal-generate-report',
            title: 'Generate New Report',
            content: `
                <div style="display: flex; flex-direction: column; gap: 1.25rem;">
                    <div>
                        <label for="gen-report-type" style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.4rem; color: var(--text);">
                            Report Type <span class="text-danger">*</span>
                        </label>
                        <select id="gen-report-type" class="filter-select" style="width: 100%; padding: 0.6rem 0.75rem; border-radius: 6px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 0.9rem;">
                            <option value="Inventory" selected>Inventory</option>
                            <option value="Stock Transactions">Stock Transactions</option>
                            <option value="Purchase Orders">Purchase Orders</option>
                            <option value="Quotations">Quotations</option>
                            <option value="Supplier Performance">Supplier Performance</option>
                            <option value="Audit Trail">Audit Trail</option>
                        </select>
                        <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
                            Select the module data to capture for this historical point-in-time snapshot.
                        </p>
                    </div>

                    <div>
                        <label for="gen-report-name" style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.4rem; color: var(--text);">
                            Report Name <span class="text-danger">*</span>
                        </label>
                        <input type="text" id="gen-report-name" value="Inventory Snapshot - ${todayStr}" placeholder="Enter report name..." style="width: 100%; padding: 0.6rem 0.75rem; border-radius: 6px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 0.9rem; box-sizing: border-box;">
                    </div>

                    <div style="background: rgba(37, 99, 235, 0.06); border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 6px; padding: 0.85rem 1rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45;">
                        <i class='bx bx-info-circle' style="color: var(--primary); margin-right: 0.25rem;"></i>
                        A point-in-time snapshot will be captured and immutably preserved in the report archive.
                    </div>
                </div>
            `,
            footer: `
                <div style="display: flex; justify-content: flex-end; gap: 0.75rem; width: 100%;">
                    <button type="button" class="btn btn-outline" id="btn-cancel-generate">Cancel</button>
                    <button type="button" class="btn btn-primary" id="btn-submit-generate">
                        <i class='bx bx-check'></i> Generate &amp; Save Snapshot
                    </button>
                </div>
            `,
            onOpen: (modalEl, closeModal) => {
                const typeSelect = modalEl.querySelector('#gen-report-type');
                const nameInput = modalEl.querySelector('#gen-report-name');
                const cancelBtn = modalEl.querySelector('#btn-cancel-generate');
                const submitBtn = modalEl.querySelector('#btn-submit-generate');

                cancelBtn?.addEventListener('click', closeModal);

                // Auto-update report name placeholder when type changes
                typeSelect?.addEventListener('change', () => {
                    const selType = typeSelect.value;
                    if (nameInput) {
                        if (selType === 'Inventory') {
                            nameInput.value = `Inventory Snapshot - ${todayStr}`;
                        } else if (selType === 'Stock Transactions') {
                            nameInput.value = `Stock Transactions Snapshot - ${todayStr}`;
                        } else if (selType === 'Purchase Orders') {
                            nameInput.value = `Purchase Orders Snapshot - ${todayStr}`;
                        } else if (selType === 'Quotations') {
                            nameInput.value = `Quotations Snapshot - ${todayStr}`;
                        } else if (selType === 'Supplier Performance') {
                            nameInput.value = `Supplier Performance Snapshot - ${todayStr}`;
                        } else if (selType === 'Audit Trail') {
                            nameInput.value = `Audit Trail Snapshot - ${todayStr}`;
                        }
                    }
                });

                submitBtn?.addEventListener('click', async () => {
                    const reportType = typeSelect?.value || 'Inventory';
                    const reportName = nameInput?.value?.trim();

                    if (!reportName) {
                        Utils.showToast('Please provide a report name', 'warning');
                        nameInput?.focus();
                        return;
                    }

                    submitBtn.disabled = true;
                    submitBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Generating...`;

                    try {
                        const payload = {
                            report_name: reportName,
                            report_type: reportType
                        };

                        const data = (typeof Api.generateReport === 'function')
                            ? await Api.generateReport(payload)
                            : await Api.post('/reports/generate', payload);

                        Utils.showToast(data.message || 'Report generated successfully', 'success');
                        closeModal();
                        await this.loadReports();
                    } catch (error) {
                        if (error.status === 423) {
                            Utils.showToast("Report generation is temporarily unavailable while the module is updating.", "warning");
                        } else {
                            Utils.showToast(error.message || "Failed to generate report", "error");
                        }
                    } finally {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = `<i class='bx bx-check'></i> Generate &amp; Save Snapshot`;
                    }
                });
            }
        });
    },

    async generateReport(type = 'Inventory') {
        this.openGenerateReportModal();
    },

    async exportCsv() {
        const btn = document.getElementById('btn-export-csv');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Exporting...`;
        }

        try {
            const token = localStorage.getItem('sims_token') || localStorage.getItem('sims_access_token');
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`${API_BASE_URL}/reports/export?report_type=Inventory`, {
                headers
            });

            if (response.status === 401) {
                Auth.logout();
                Utils.showToast("Session expired. Please login again.", "error");
                return;
            }

            if (response.status === 403) {
                Utils.showToast("Access denied: You do not have permission to export reports.", "error");
                return;
            }

            if (response.status === 423) {
                const errData = await response.json().catch(() => ({}));
                Utils.showToast(errData.message || "Report export is locked while inventory is being updated.", "warning");
                return;
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || `Export failed with status ${response.status}`);
            }

            const blob = await response.blob();
            
            // Extract filename from Content-Disposition header if available
            let filename = `current_inventory_report_${new Date().toISOString().slice(0, 10)}.csv`;
            const disposition = response.headers.get('Content-Disposition');
            if (disposition && disposition.includes('filename=')) {
                const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) {
                    filename = match[1].replace(/['"]/g, '').trim();
                }
            }

            // Create download link and trigger download
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(blobUrl);
            a.remove();

            Utils.showToast("Current inventory report CSV downloaded successfully.", "success");
        } catch (error) {
            Utils.showToast(error.message || "Failed to export report CSV", "error");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i class='bx bx-download'></i> Export CSV (Current Balance)`;
            }
        }
    },

    async viewReportDetails(reportId) {
        Modal.create({
            id: `modal-report-detail-${reportId}`,
            title: `Report Details — #${reportId}`,
            content: `
                <div id="report-modal-content-area" style="min-height: 200px;">
                    <div style="text-align: center; padding: 2.5rem 1rem;">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 2.5rem; color: var(--primary);"></i>
                        <p style="margin-top: 0.75rem; color: var(--gray); font-size: 0.95rem;">Loading historical report snapshot...</p>
                    </div>
                </div>
            `,
            footer: `
                <div id="modal-report-footer-actions" style="display: flex; justify-content: space-between; align-items: center; width: 100%; flex-wrap: wrap; gap: 0.5rem;">
                    <div id="modal-export-buttons-group" style="display: flex; gap: 0.5rem; flex-wrap: wrap;"></div>
                    <button type="button" class="btn btn-outline" id="modal-close-report-btn">Close</button>
                </div>
            `,
            onOpen: async (modalEl, closeModal) => {
                modalEl.querySelector('#modal-close-report-btn')?.addEventListener('click', closeModal);
                const contentBox = modalEl.querySelector('.modal-content');
                if (contentBox) {
                    contentBox.style.width = 'min(980px, 95vw)';
                    contentBox.style.maxWidth = '980px';
                }

                try {
                    const data = (typeof Api.getReport === 'function')
                        ? await Api.getReport(reportId)
                        : await Api.get(`/reports/${reportId}`);
                    const container = modalEl.querySelector('#report-modal-content-area');
                    if (!container) return;

                    const exportGroup = modalEl.querySelector('#modal-export-buttons-group');
                    if (exportGroup) {
                        if (data.has_snapshot && data.snapshot) {
                            exportGroup.innerHTML = `
                                <button type="button" class="btn btn-secondary" id="modal-export-csv-btn" title="Download historical snapshot as CSV">
                                    <i class='bx bx-download'></i> Export Snapshot CSV
                                </button>
                                <button type="button" class="btn btn-secondary" id="modal-export-pdf-btn" title="Download historical snapshot as PDF">
                                    <i class='bx bxs-file-pdf' style="color: #dc2626;"></i> Export PDF
                                </button>
                            `;
                            modalEl.querySelector('#modal-export-csv-btn')?.addEventListener('click', () => {
                                this.exportSnapshotCsv(reportId, data.report_name);
                            });
                            modalEl.querySelector('#modal-export-pdf-btn')?.addEventListener('click', () => {
                                this.exportSnapshotPdf(reportId, data.report_name);
                            });
                        } else {
                            exportGroup.innerHTML = '';
                        }
                    }

                    let html = `
                        <div style="background: var(--surface); padding: 1.25rem; border-radius: 8px; margin-bottom: 1.5rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; border: 1px solid var(--border);">
                            <div>
                                <div style="font-size: 0.75rem; color: var(--gray); text-transform: uppercase; letter-spacing: 0.5px;">Report Name</div>
                                <div style="font-weight: 600; font-size: 1.05rem; margin-top: 3px;">${Utils.escapeHtml(data.report_name || '')}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: var(--gray); text-transform: uppercase; letter-spacing: 0.5px;">Type</div>
                                <div style="margin-top: 3px;"><span class="badge" style="background: #e0e0e0; color: #333; font-weight: 500;">${Utils.escapeHtml(data.report_type || '')}</span></div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: var(--gray); text-transform: uppercase; letter-spacing: 0.5px;">Generated By</div>
                                <div style="font-weight: 500; margin-top: 3px;">${Utils.escapeHtml(data.generated_by_username || ('User #' + data.generated_by))}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: var(--gray); text-transform: uppercase; letter-spacing: 0.5px;">Generated On</div>
                                <div style="font-weight: 500; margin-top: 3px;">${Utils.formatDate(data.generated_on)}</div>
                            </div>
                        </div>
                    `;

                    if (!data.has_snapshot || !data.snapshot) {
                        html += `
                            <div style="background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; padding: 1.5rem; text-align: center; color: #92400e; margin: 1.5rem 0;">
                                <i class='bx bx-info-circle' style="font-size: 2.25rem; margin-bottom: 0.5rem; display: block; color: #f59e0b;"></i>
                                <h4 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; font-weight: 600;">Historical Snapshot Unavailable</h4>
                                <p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">
                                    ${Utils.escapeHtml(data.message || 'Historical snapshot data is unavailable for this report.')}
                                </p>
                                <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #78350f;">
                                    This report record was created prior to Phase 2 snapshot persistence. The system preserves verified creation metadata without fabricating historical inventory data.
                                </p>
                            </div>
                        `;
                    } else {
                        const items = Array.isArray(data.snapshot) ? data.snapshot : [];
                        const repType = data.report_type || 'Inventory';

                        if (items.length === 0) {
                            html += `
                                <div style="text-align: center; padding: 2.5rem 1rem; color: var(--gray);">
                                    <i class='bx bx-box' style="font-size: 2.5rem; margin-bottom: 0.5rem; display: block;"></i>
                                    <p>Saved snapshot contains 0 records.</p>
                                </div>
                            `;
                        } else if (repType === 'Inventory') {
                            const totalItems = items.length;
                            const totalQty = items.reduce((sum, it) => sum + (Number(it.quantity_available) || 0), 0);
                            const totalVal = items.reduce((sum, it) => sum + (Number(it.inventory_value) || 0), 0);
                            const lowStockCount = items.filter(it => it.stock_status === 'LOW STOCK').length;

                            html += `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Products</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalItems}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Units</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalQty.toLocaleString()}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Inventory Value</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">$${totalVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Low Stock Alerts</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: ${lowStockCount > 0 ? '#dc2626' : '#059669'};">${lowStockCount}</div>
                                    </div>
                                </div>

                                <div class="table-container" style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px;">
                                    <table style="width: 100%; font-size: 0.875rem;">
                                        <thead>
                                            <tr style="position: sticky; top: 0; background: var(--surface); z-index: 1;">
                                                <th>Product</th>
                                                <th>SKU</th>
                                                <th>Category</th>
                                                <th style="text-align: right;">Qty</th>
                                                <th style="text-align: right;">Reorder</th>
                                                <th style="text-align: right;">Unit Price</th>
                                                <th style="text-align: right;">Inv Value</th>
                                                <th>Stock Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${items.map(it => {
                                                const isLow = it.stock_status === 'LOW STOCK';
                                                return `
                                                    <tr>
                                                        <td><strong>${Utils.escapeHtml(it.product_name || '')}</strong></td>
                                                        <td><code>${Utils.escapeHtml(it.sku || '')}</code></td>
                                                        <td>${Utils.escapeHtml(it.category_name || 'Uncategorized')}</td>
                                                        <td style="text-align: right; font-weight: 600;">${Number(it.quantity_available || 0).toLocaleString()}</td>
                                                        <td style="text-align: right; color: var(--gray);">${Number(it.reorder_level || 0).toLocaleString()}</td>
                                                        <td style="text-align: right;">$${Number(it.unit_price || 0).toFixed(2)}</td>
                                                        <td style="text-align: right; font-weight: 600;">$${Number(it.inventory_value || 0).toFixed(2)}</td>
                                                        <td>
                                                            <span class="status-badge ${isLow ? 'status-inactive' : 'status-active'}" style="font-size: 0.7rem; padding: 2px 6px;">
                                                                ${isLow ? 'LOW STOCK' : 'IN STOCK'}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            `;
                        } else if (repType === 'Stock Transactions') {
                            const totalTx = items.length;
                            const stockInUnits = items.reduce((sum, it) => {
                                const t = (it.transaction_type || '').toUpperCase();
                                return sum + (t === 'STOCK_IN' || t === 'IN' ? (Number(it.quantity) || 0) : 0);
                            }, 0);
                            const stockOutUnits = items.reduce((sum, it) => {
                                const t = (it.transaction_type || '').toUpperCase();
                                return sum + (t === 'STOCK_OUT' || t === 'OUT' ? (Number(it.quantity) || 0) : 0);
                            }, 0);
                            const netUnits = stockInUnits - stockOutUnits;

                            html += `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Transactions</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalTx.toLocaleString()}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Stock In</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">+${stockInUnits.toLocaleString()}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Stock Out</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #dc2626;">-${stockOutUnits.toLocaleString()}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Net Movement</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: ${netUnits >= 0 ? '#059669' : '#dc2626'};">${netUnits >= 0 ? '+' : ''}${netUnits.toLocaleString()}</div>
                                    </div>
                                </div>

                                <div class="table-container" style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px;">
                                    <table style="width: 100%; font-size: 0.875rem;">
                                        <thead>
                                            <tr style="position: sticky; top: 0; background: var(--surface); z-index: 1;">
                                                <th>ID</th>
                                                <th>Date &amp; Time</th>
                                                <th>Product</th>
                                                <th>Type</th>
                                                <th style="text-align: right;">Quantity</th>
                                                <th>Performed By</th>
                                                <th>Reference</th>
                                                <th>Notes</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${items.map(it => {
                                                const isStockIn = (it.transaction_type || '').toUpperCase() === 'STOCK_IN';
                                                return `
                                                    <tr>
                                                        <td><strong>#${it.transaction_id}</strong></td>
                                                        <td>${Utils.formatDate(it.transaction_date)}</td>
                                                        <td>
                                                            <strong>${Utils.escapeHtml(it.product_name || '')}</strong>
                                                            <div style="font-size: 0.75rem; color: var(--gray); font-family: monospace;">${Utils.escapeHtml(it.sku || '')}</div>
                                                        </td>
                                                        <td>
                                                            <span class="status-badge ${isStockIn ? 'status-active' : 'status-inactive'}" style="font-size: 0.7rem; padding: 2px 6px;">
                                                                ${Utils.escapeHtml(it.transaction_type || '')}
                                                            </span>
                                                        </td>
                                                        <td style="text-align: right; font-weight: 600; color: ${isStockIn ? '#059669' : '#dc2626'};">
                                                            ${isStockIn ? '+' : '-'}${Number(it.quantity || 0).toLocaleString()}
                                                        </td>
                                                        <td>${Utils.escapeHtml(it.performed_by || '—')}</td>
                                                        <td>
                                                            ${it.shipment_number ? `<span style="font-size: 0.75rem; font-family: monospace; color: var(--primary);"><i class='bx bx-car'></i> ${Utils.escapeHtml(it.shipment_number)}</span>` : ''}
                                                            ${it.purchase_order_id ? `<span style="font-size: 0.75rem; font-family: monospace; color: var(--text-secondary);"><i class='bx bx-receipt'></i> PO #${it.purchase_order_id}</span>` : ''}
                                                            ${!it.shipment_number && !it.purchase_order_id ? '—' : ''}
                                                        </td>
                                                        <td style="font-size: 0.8rem; color: var(--text-secondary);">${Utils.escapeHtml(it.notes || '—')}</td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            `;
                        } else if (repType === 'Purchase Orders') {
                            const totalPOs = items.length;
                            const totalVal = items.reduce((sum, it) => sum + (Number(it.total_amount) || 0), 0);
                            const acceptedCount = items.filter(it => ['Accepted', 'Completed', 'Delivered'].includes(it.status)).length;
                            const pendingCount = items.filter(it => it.status === 'Pending' || it.status === 'Created').length;

                            html += `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total POs</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalPOs}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total PO Value</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">$${totalVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Accepted / Completed</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">${acceptedCount}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Pending / Created</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #d97706;">${pendingCount}</div>
                                    </div>
                                </div>

                                <div class="table-container" style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px;">
                                    <table style="width: 100%; font-size: 0.875rem;">
                                        <thead>
                                            <tr style="position: sticky; top: 0; background: var(--surface); z-index: 1;">
                                                <th>PO Ref</th>
                                                <th>Order Date</th>
                                                <th>Supplier</th>
                                                <th>Status</th>
                                                <th style="text-align: right;">Items</th>
                                                <th style="text-align: right;">Total Amount</th>
                                                <th>Ordered By</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${items.map(po => {
                                                let statusClass = 'status-pending';
                                                if (['Accepted', 'Completed', 'Delivered'].includes(po.status)) statusClass = 'status-active';
                                                if (po.status === 'Rejected') statusClass = 'status-inactive';

                                                const poItems = Array.isArray(po.items) ? po.items : [];
                                                const itemSummary = poItems.map(pi => `${pi.quantity}x ${Utils.escapeHtml(pi.product_name || '')}`).join(', ');

                                                return `
                                                    <tr>
                                                        <td><strong>${Utils.escapeHtml(po.reference_number || ('PO-' + po.purchase_order_id))}</strong></td>
                                                        <td>${po.order_date ? Utils.escapeHtml(po.order_date) : '—'}</td>
                                                        <td>
                                                            <strong>${Utils.escapeHtml(po.supplier_name || '')}</strong>
                                                            ${po.contact_person ? `<div style="font-size: 0.75rem; color: var(--gray);">${Utils.escapeHtml(po.contact_person)}</div>` : ''}
                                                        </td>
                                                        <td>
                                                            <span class="status-badge ${statusClass}" style="font-size: 0.7rem; padding: 2px 6px;">
                                                                ${Utils.escapeHtml(po.status || 'Created')}
                                                            </span>
                                                        </td>
                                                        <td style="text-align: right;">
                                                            <strong>${po.item_count || poItems.length}</strong>
                                                            ${itemSummary ? `<div style="font-size: 0.7rem; color: var(--text-secondary); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${itemSummary}">${itemSummary}</div>` : ''}
                                                        </td>
                                                        <td style="text-align: right; font-weight: 600; color: #059669;">
                                                            $${Number(po.total_amount || 0).toFixed(2)}
                                                        </td>
                                                        <td>${Utils.escapeHtml(po.ordered_by_username || ('User #' + po.ordered_by))}</td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            `;
                        } else if (repType === 'Quotations') {
                            const totalQuotations = items.length;
                            const totalVal = items.reduce((sum, q) => sum + (Number(q.total_amount) || 0), 0);
                            const approvedCount = items.filter(q => ['Approved', 'Accepted'].includes(q.status)).length;
                            const pendingCount = items.filter(q => ['Pending', 'Submitted', 'Under Review', 'Draft'].includes(q.status)).length;
                            const rejectedCount = items.filter(q => ['Rejected', 'Expired'].includes(q.status)).length;

                            html += `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Quotations</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalQuotations}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Quoted Value</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">$${totalVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Approved / Accepted</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">${approvedCount}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Pending Review</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #d97706;">${pendingCount}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Rejected / Expired</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #dc2626;">${rejectedCount}</div>
                                    </div>
                                </div>

                                <div class="table-container" style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px;">
                                    <table style="width: 100%; font-size: 0.875rem;">
                                        <thead>
                                            <tr style="position: sticky; top: 0; background: var(--surface); z-index: 1;">
                                                <th>Quotation Ref</th>
                                                <th>Date</th>
                                                <th>Supplier</th>
                                                <th>Status</th>
                                                <th>PO Ref</th>
                                                <th style="text-align: right;">Line Items</th>
                                                <th style="text-align: right;">Total Amount</th>
                                                <th>Approver / Creator</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${items.map(q => {
                                                let statusClass = 'status-pending';
                                                if (['Approved', 'Accepted'].includes(q.status)) statusClass = 'status-active';
                                                if (['Rejected', 'Expired'].includes(q.status)) statusClass = 'status-inactive';

                                                const qItems = Array.isArray(q.items) ? q.items : [];
                                                const itemSummary = qItems.map(qi => `${qi.quoted_quantity || 0}x ${Utils.escapeHtml(qi.product_name || '')} @ $${Number(qi.unit_price || 0).toFixed(2)}`).join(', ');

                                                return `
                                                    <tr>
                                                        <td><strong>${Utils.escapeHtml(q.quotation_number || ('QT-' + q.quotation_id))}</strong></td>
                                                        <td>${q.quotation_date ? Utils.escapeHtml(q.quotation_date) : '—'}</td>
                                                        <td>
                                                            <strong>${Utils.escapeHtml(q.supplier_name || '')}</strong>
                                                            ${q.contact_person ? `<div style="font-size: 0.75rem; color: var(--gray);">${Utils.escapeHtml(q.contact_person)}</div>` : ''}
                                                        </td>
                                                        <td>
                                                            <span class="status-badge ${statusClass}" style="font-size: 0.7rem; padding: 2px 6px;">
                                                                ${Utils.escapeHtml(q.status || 'Pending')}
                                                            </span>
                                                            ${q.rejection_reason ? `<div style="font-size: 0.7rem; color: #dc2626; margin-top: 2px;">${Utils.escapeHtml(q.rejection_reason)}</div>` : ''}
                                                        </td>
                                                        <td>
                                                            ${q.purchase_order_id ? `<span style="font-size: 0.75rem; font-family: monospace; color: var(--primary);"><i class='bx bx-receipt'></i> PO #${q.purchase_order_id}</span>` : '—'}
                                                        </td>
                                                        <td style="text-align: right;">
                                                            <strong>${q.item_count || qItems.length}</strong>
                                                            ${itemSummary ? `<div style="font-size: 0.7rem; color: var(--text-secondary); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${itemSummary}">${itemSummary}</div>` : ''}
                                                        </td>
                                                        <td style="text-align: right; font-weight: 600; color: #059669;">
                                                            $${Number(q.total_amount || 0).toFixed(2)}
                                                        </td>
                                                        <td style="font-size: 0.8rem;">
                                                            ${q.approved_by_username ? `<div><i class='bx bx-check-circle' style='color:#059669;'></i> ${Utils.escapeHtml(q.approved_by_username)}</div>` : ''}
                                                            ${q.ordered_by_username ? `<div style="color: var(--text-secondary);"><i class='bx bx-user'></i> ${Utils.escapeHtml(q.ordered_by_username)}</div>` : ''}
                                                            ${!q.approved_by_username && !q.ordered_by_username ? '—' : ''}
                                                        </td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            `;
                        } else if (repType === 'Supplier Performance') {
                            const totalSuppliers = items.length;
                            const totalPOVal = items.reduce((sum, s) => sum + (Number(s.total_order_value) || 0), 0);
                            const totalPOs = items.reduce((sum, s) => sum + (Number(s.total_purchase_orders) || 0), 0);
                            const totalQuotes = items.reduce((sum, s) => sum + (Number(s.total_quotations) || 0), 0);

                            html += `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Evaluated Suppliers</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalSuppliers}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Aggregate PO Value</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">$${totalPOVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Purchase Orders</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalPOs}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Quotations</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #0284c7;">${totalQuotes}</div>
                                    </div>
                                </div>

                                <div class="table-container" style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px;">
                                    <table style="width: 100%; font-size: 0.85rem;">
                                        <thead>
                                            <tr style="position: sticky; top: 0; background: var(--surface); z-index: 1;">
                                                <th>Supplier</th>
                                                <th style="text-align: right;">PO Orders &amp; Value</th>
                                                <th style="text-align: right;">PO Acceptance</th>
                                                <th style="text-align: right;">Quotations</th>
                                                <th style="text-align: right;">Response &amp; Approval</th>
                                                <th>Delivery Performance</th>
                                                <th>Avg Delay</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${items.map(s => {
                                                const poAccStr = s.po_acceptance_rate !== null ? `${s.po_acceptance_rate}%` : 'N/A';
                                                const qRespStr = s.quotation_response_rate !== null ? `${s.quotation_response_rate}%` : 'N/A';
                                                const qAppStr = s.quotation_approval_rate !== null ? `${s.quotation_approval_rate}%` : 'N/A';
                                                
                                                let delivStr = '<span style="color: var(--gray);">Unscheduled</span>';
                                                if (s.on_time_delivery_rate !== null) {
                                                    const delivColor = s.on_time_delivery_rate >= 80 ? '#059669' : (s.on_time_delivery_rate >= 50 ? '#d97706' : '#dc2626');
                                                    delivStr = `<strong style="color: ${delivColor};">${s.on_time_delivery_rate}% on-time</strong> <span style="font-size: 0.7rem; color: var(--text-secondary);">(${s.on_time_deliveries}/${s.measurable_deliveries})</span>`;
                                                }

                                                let delayStr = '—';
                                                if (s.avg_delivery_delay_days !== null) {
                                                    if (s.avg_delivery_delay_days <= 0) {
                                                        delayStr = `<span style="color: #059669; font-weight: 600;">${Math.abs(s.avg_delivery_delay_days)}d early</span>`;
                                                    } else {
                                                        delayStr = `<span style="color: #dc2626; font-weight: 600;">+${s.avg_delivery_delay_days}d late</span>`;
                                                    }
                                                }

                                                return `
                                                    <tr>
                                                        <td>
                                                            <strong>${Utils.escapeHtml(s.supplier_name || '')}</strong>
                                                            <div style="font-size: 0.75rem; color: var(--gray);">
                                                                <span class="status-badge ${s.status === 'Active' ? 'status-active' : 'status-inactive'}" style="font-size: 0.65rem; padding: 1px 4px;">${Utils.escapeHtml(s.status || 'Active')}</span>
                                                                ${s.contact_person ? ` &bull; ${Utils.escapeHtml(s.contact_person)}` : ''}
                                                            </div>
                                                        </td>
                                                        <td style="text-align: right;">
                                                            <strong>${s.total_purchase_orders || 0} POs</strong>
                                                            <div style="font-size: 0.75rem; color: #059669; font-weight: 600;">$${Number(s.total_order_value || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                                        </td>
                                                        <td style="text-align: right;">
                                                            <strong style="color: ${s.po_acceptance_rate >= 70 ? '#059669' : '#d97706'};">${poAccStr}</strong>
                                                            <div style="font-size: 0.7rem; color: var(--text-secondary);">${s.accepted_purchase_orders || 0} acc / ${s.rejected_purchase_orders || 0} rej</div>
                                                        </td>
                                                        <td style="text-align: right;">
                                                            <strong>${s.total_quotations || 0} quotes</strong>
                                                            <div style="font-size: 0.75rem; color: #0284c7; font-weight: 600;">$${Number(s.total_quoted_value || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                                        </td>
                                                        <td style="text-align: right;">
                                                            <div>Resp: <strong>${qRespStr}</strong></div>
                                                            <div style="font-size: 0.7rem; color: var(--text-secondary);">Appr: <strong>${qAppStr}</strong></div>
                                                        </td>
                                                        <td>
                                                            <div>${delivStr}</div>
                                                            <div style="font-size: 0.7rem; color: var(--text-secondary);">${s.delivered_shipments || 0} of ${s.total_shipments || 0} delivered</div>
                                                        </td>
                                                        <td>
                                                            <div>${delayStr}</div>
                                                        </td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>

                                <div style="margin-top: 1rem; background: rgba(14, 165, 233, 0.05); border: 1px solid rgba(14, 165, 233, 0.2); border-radius: 6px; padding: 0.75rem 1rem; font-size: 0.75rem; color: var(--text-secondary); line-height: 1.5;">
                                    <div style="font-weight: 600; color: var(--text); margin-bottom: 0.25rem;"><i class='bx bx-info-circle' style="color: #0284c7;"></i> Performance Metric Explanations:</div>
                                    <div>&bull; <strong>PO Acceptance Rate:</strong> Accepted and Delivered POs &divide; Total POs.</div>
                                    <div>&bull; <strong>Quotation Response Rate:</strong> Responded Quotes &divide; Total Quotes. <strong>Approval Rate:</strong> Approved Quotes &divide; Responded Quotes.</div>
                                    <div>&bull; <strong>On-Time Delivery Rate:</strong> Deliveries on or before expected delivery date &divide; Measurable Deliveries (with recorded planned dates). Deliveries lacking planned dates are marked <em>Unscheduled</em> to prevent bias.</div>
                                </div>
                            `;
                        } else if (repType === 'Audit Trail') {
                            const totalEvents = items.length;
                            const uniqueActors = new Set(items.map(ev => ev.user_id).filter(Boolean)).size;
                            const entityTypes = new Set(items.map(ev => ev.table_name).filter(Boolean)).size;

                            html += `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Total Events</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: var(--text);">${totalEvents}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Active Actors</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #2563eb;">${uniqueActors}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Entity Tables</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #7c3aed;">${entityTypes}</div>
                                    </div>
                                    <div class="glass-panel" style="padding: 0.75rem 1rem; border-radius: 6px; text-align: center;">
                                        <div style="font-size: 0.75rem; color: var(--gray);">Logged Outcome</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">Verified Success</div>
                                    </div>
                                </div>

                                <div class="table-container" style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px;">
                                    <table style="width: 100%; font-size: 0.85rem;">
                                        <thead>
                                            <tr style="position: sticky; top: 0; background: var(--surface); z-index: 1;">
                                                <th style="width: 60px;">Event ID</th>
                                                <th>Timestamp</th>
                                                <th>Actor</th>
                                                <th>Action</th>
                                                <th>Entity</th>
                                                <th>Record ID</th>
                                                <th>Description</th>
                                                <th>Outcome</th>
                                                <th>IP Address</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${items.map(ev => {
                                                let actColor = '#2563eb';
                                                const a = (ev.action || '').toUpperCase();
                                                if (a === 'DELETE') actColor = '#dc2626';
                                                else if (a === 'UPDATE') actColor = '#d97706';
                                                else if (a === 'INSERT' || a === 'CREATE') actColor = '#059669';

                                                return `
                                                    <tr>
                                                        <td><strong>#${ev.log_id || 'N/A'}</strong></td>
                                                        <td>${Utils.escapeHtml(ev.action_time ? Utils.formatDate(ev.action_time) : 'N/A')}</td>
                                                        <td><strong>${Utils.escapeHtml(ev.actor_username || ('User #' + (ev.user_id || 'N/A')))}</strong></td>
                                                        <td>
                                                            <span class="badge" style="background: rgba(0,0,0,0.06); color: ${actColor}; font-weight: 600; padding: 2px 6px; border-radius: 4px;">
                                                                ${Utils.escapeHtml(ev.action || 'UNKNOWN')}
                                                            </span>
                                                        </td>
                                                        <td><code>${Utils.escapeHtml(ev.table_name || 'General')}</code></td>
                                                        <td>${ev.record_id ? '#' + ev.record_id : '<span style="color:var(--gray)">N/A</span>'}</td>
                                                        <td>${Utils.escapeHtml(ev.description || '-')}</td>
                                                        <td><span class="status-badge status-active" style="font-size: 0.65rem; padding: 1px 5px;">${Utils.escapeHtml(ev.outcome || 'Success')}</span></td>
                                                        <td style="font-family: monospace; font-size: 0.75rem; color: var(--gray);">${Utils.escapeHtml(ev.ip_address || 'N/A')}</td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            `;
                        }
                    }

                    container.innerHTML = html;
                } catch (err) {
                    const container = modalEl.querySelector('#report-modal-content-area');
                    if (container) {
                        container.innerHTML = `
                            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 1.5rem; text-align: center; color: #b91c1c;">
                                <i class='bx bx-error-circle' style="font-size: 2.25rem; margin-bottom: 0.5rem; display: block;"></i>
                                <h4 style="margin: 0 0 0.5rem 0; font-size: 1.05rem;">Failed to Load Report Details</h4>
                                <p style="margin: 0; font-size: 0.9rem;">${Utils.escapeHtml(err.message || 'Unable to retrieve report details.')}</p>
                            </div>
                        `;
                    }
                }
            }
        });
    },

    async exportSnapshotCsv(reportId, reportName) {
        const btn = document.getElementById('modal-export-csv-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Exporting...`;
        }

        try {
            const token = localStorage.getItem('sims_token') || localStorage.getItem('sims_access_token');
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`${API_BASE_URL}/reports/${reportId}/export/csv`, {
                headers
            });

            if (response.status === 401) {
                Auth.logout();
                Utils.showToast("Session expired. Please login again.", "error");
                return;
            }

            if (response.status === 403) {
                Utils.showToast("Access denied: You do not have permission to export this report.", "error");
                return;
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.message || errData.error || `Export failed with status ${response.status}`);
            }

            const blob = await response.blob();
            let filename = `report_${reportId}_snapshot.csv`;
            const disposition = response.headers.get('Content-Disposition');
            if (disposition && disposition.includes('filename=')) {
                const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) {
                    filename = match[1].replace(/['"]/g, '').trim();
                }
            }

            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(blobUrl);
            a.remove();

            Utils.showToast("Historical snapshot CSV downloaded successfully.", "success");
        } catch (error) {
            Utils.showToast(error.message || "Failed to export historical snapshot CSV", "error");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i class='bx bx-download'></i> Export Snapshot CSV`;
            }
        }
    },

    async exportSnapshotPdf(reportId, reportName) {
        const btn = document.getElementById('modal-export-pdf-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Generating PDF...`;
        }

        try {
            const token = localStorage.getItem('sims_token') || localStorage.getItem('sims_access_token');
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`${API_BASE_URL}/reports/${reportId}/export/pdf`, {
                headers
            });

            if (response.status === 401) {
                Auth.logout();
                Utils.showToast("Session expired. Please login again.", "error");
                return;
            }

            if (response.status === 403) {
                Utils.showToast("Access denied: You do not have permission to export this report.", "error");
                return;
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.message || errData.error || `PDF generation failed with status ${response.status}`);
            }

            const blob = await response.blob();
            let filename = `report_${reportId}_snapshot.pdf`;
            const disposition = response.headers.get('Content-Disposition');
            if (disposition && disposition.includes('filename=')) {
                const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) {
                    filename = match[1].replace(/['"]/g, '').trim();
                }
            }

            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(blobUrl);
            a.remove();

            Utils.showToast("Historical snapshot PDF downloaded successfully.", "success");
        } catch (error) {
            Utils.showToast(error.message || "Failed to export historical snapshot PDF", "error");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i class='bx bxs-file-pdf' style="color: #dc2626;"></i> Export PDF`;
            }
        }
    }
};
