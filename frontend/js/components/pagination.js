// pagination.js - Standard Table & List Pagination Component for SIMS

const PaginationComponent = {
    /**
     * Render HTML markup for table pagination matching the SIMS design system.
     * @param {Object} options
     * @param {number} options.total - Total number of matching records
     * @param {number} options.page - Current 1-based page number
     * @param {number} options.pageSize - Items per page
     * @param {number} options.totalPages - Total calculated pages
     * @param {string} options.label - Noun for records (e.g. 'items', 'orders', 'shipments')
     * @param {string} options.onPageChangeName - Global function call name, e.g. "App.pages['inventory'].goToPage"
     * @returns {string} HTML string
     */
    render({ total = 0, page = 1, pageSize = 20, totalPages = 1, label = 'records', onPageChangeName = '' }) {
        if (!total || total <= 0) {
            return `
                <div class="table-pagination">
                    <div class="pagination-info">Showing 0 ${Utils.escapeHtml(label)}</div>
                    <div class="pagination-controls"></div>
                </div>
            `;
        }

        const currentPage = Math.max(1, parseInt(page, 10) || 1);
        const size = Math.max(1, parseInt(pageSize, 10) || 20);
        const pages = Math.max(1, parseInt(totalPages, 10) || Math.ceil(total / size));
        const start = (currentPage - 1) * size + 1;
        const end = Math.min(currentPage * size, total);

        let controlsHtml = `
            <button type="button" class="pagination-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="${onPageChangeName}(${currentPage - 1})" title="Previous Page">
                <i class='bx bx-chevron-left'></i> Previous
            </button>
        `;

        for (let p = 1; p <= pages; p++) {
            if (p === 1 || p === pages || (p >= currentPage - 1 && p <= currentPage + 1)) {
                controlsHtml += `
                    <button type="button" class="pagination-btn ${p === currentPage ? 'active' : ''}" onclick="${onPageChangeName}(${p})" title="Page ${p}">
                        ${p}
                    </button>
                `;
            } else if (p === currentPage - 2 || p === currentPage + 2) {
                controlsHtml += `<span style="padding: 0 4px; color: var(--text-light, #94a3b8); user-select: none;">...</span>`;
            }
        }

        controlsHtml += `
            <button type="button" class="pagination-btn" ${currentPage >= pages ? 'disabled' : ''} onclick="${onPageChangeName}(${currentPage + 1})" title="Next Page">
                Next <i class='bx bx-chevron-right'></i>
            </button>
        `;

        return `
            <div class="table-pagination">
                <div class="pagination-info">Showing ${start}–${end} of ${total} ${Utils.escapeHtml(label)}</div>
                <div class="pagination-controls">${controlsHtml}</div>
            </div>
        `;
    }
};

window.PaginationComponent = PaginationComponent;
