// stock-requests.js

App.pages['stock-requests'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">WORKSPACE</span>
                    <h1>Stock Requests</h1>
                    <p>Review requests and submit quotation details.</p>
                </div>
                <button class="btn" style="background: white; border: 1px solid var(--border); color: var(--text);">
                    <i class='bx bx-export'></i> Export CSV
                </button>
            </div>

            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <div class="search-box input-with-icon" style="flex: 1;">
                    <i class='bx bx-search'></i>
                    <input type="text" id="search-requests" placeholder="Search request, product..." style="width: 100%;">
                </div>
                <div style="display: flex; gap: 1rem;">
                    <select class="input-with-icon" style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px;">
                        <option>All Status</option>
                    </select>
                    <select class="input-with-icon" style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px;">
                        <option>All Priority</option>
                    </select>
                    <select class="input-with-icon" style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px;">
                        <option>Latest first</option>
                    </select>
                </div>
            </div>

            <div class="card table-responsive" style="margin-top: 1.5rem;">
                <div style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 13px; font-weight: 600;">4 Requests <span style="color: var(--text-light); font-weight: normal; margin-left: 8px;">Updated just now</span></span>
                    <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px 10px;"><i class='bx bx-filter'></i> Save Filter</button>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="width: 40px;"><input type="checkbox"></th>
                            <th>REQUEST ID</th>
                            <th>PRODUCT</th>
                            <th>QUANTITY</th>
                            <th>REQUIRED DATE</th>
                            <th>PRIORITY</th>
                            <th>STATUS</th>
                            <th>ACTION</th>
                        </tr>
                    </thead>
                    <tbody id="stock-requests-tbody">
                        <tr><td colspan="8" style="text-align:center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;

        this.fetchStockRequests(container.querySelector('#stock-requests-tbody'));

        return container;
    },

    async fetchStockRequests(tbody) {
        try {
            // Using the team2 purchase-orders endpoint for now
            const response = await Api.get('/purchase-orders/');
            tbody.innerHTML = '';
            
            if (response.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No stock requests found.</td></tr>';
                return;
            }

            response.forEach(req => {
                const tr = document.createElement('tr');
                
                // Priority logic based on expected delivery date
                let priority = 'Medium';
                let priorityColor = 'var(--yellow)';
                let priorityBg = 'var(--yellow-light)';
                
                const statusColor = req.status === 'Pending' ? 'var(--yellow)' : (req.status === 'Approved' ? 'var(--green)' : 'var(--blue)');
                const statusBg = req.status === 'Pending' ? 'var(--yellow-light)' : (req.status === 'Approved' ? 'var(--green-light)' : 'var(--blue-light)');

                tr.innerHTML = `
                    <td><input type="checkbox"></td>
                    <td>
                        <div style="font-weight: 600;">SR-${new Date(req.order_date).getFullYear()}-${req.purchase_order_id.toString().padStart(4, '0')}</div>
                        <div style="font-size: 12px; color: var(--text-light);">Received today</div>
                    </td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="width: 30px; height: 30px; border-radius: 6px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">
                                ${req.product_name ? req.product_name.substring(0,2).toUpperCase() : 'PR'}
                            </div>
                            <span>${req.product_name || 'Unknown Product'}</span>
                        </div>
                    </td>
                    <td>${req.quantity || 0} pcs</td>
                    <td>
                        <div>${req.expected_delivery || 'N/A'}</div>
                        <div style="font-size: 11px; color: var(--red);">Action required</div>
                    </td>
                    <td><span class="badge" style="background: ${priorityBg}; color: ${priorityColor}; font-size: 11px !important;">${priority}</span></td>
                    <td><span class="badge" style="background: ${statusBg}; color: ${statusColor}; font-size: 11px !important;">${req.status === 'Pending' ? 'Awaiting response' : req.status}</span></td>
                    <td>
                        <button class="btn" style="background: var(--primary-light); color: var(--primary); padding: 5px 12px; font-size: 12px;" onclick="App.pages['stock-requests'].respond(${req.purchase_order_id})">Respond</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:red;">Error loading requests</td></tr>';
        }
    },
    
    respond(id) {
        alert("Respond modal for Request ID: " + id);
    }
};
