// dashboard.js

App.pages['dashboard'] = {
    render() {
        const user = Auth.getUser();
        const username = user ? user.username : 'User';
        const role = user ? user.role : 'Role';

        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">${role.toUpperCase()} PORTAL</span>
                    <h1>Good morning, ${username} 👋</h1>
                    <p>Here's an overview of your operations.</p>
                </div>
            </div>

            <div id="dashboard-stats" class="stats-grid">
                <!-- Dynamically populated based on role -->
            </div>
            
            <div id="dashboard-specific-content" style="margin-top: 30px;">
                <!-- Additional dashboard widgets loaded via API -->
            </div>
        `;
        return container;
    },

    async init() {
        const user = Auth.getUser();
        if (!user) return;

        const statsContainer = document.getElementById('dashboard-stats');
        const contentContainer = document.getElementById('dashboard-specific-content');

        const updateUsernameHtml = `
            <div class="section-title" style="margin-top: 40px;">
                <div>
                    <h3>Account Settings</h3>
                    <p>Manage your profile information</p>
                </div>
            </div>
            <div class="card" style="background: var(--white); padding: 24px; border-radius: var(--radius); border: 1px solid var(--border);">
                <div style="display: flex; flex-direction: column; gap: 0.85rem;">
                    <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                        <input type="text" id="new-username-input" class="input" value="${Utils.escapeHtml(user.username || '')}" placeholder="Current Username" disabled style="max-width: 300px; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); width: 100%; background: #f8fafc; color: var(--text-secondary); cursor: not-allowed;">
                        <button class="btn" id="btn-change-username" disabled style="padding: 12px 24px; opacity: 0.6; cursor: not-allowed;">Change Username</button>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text-secondary);">
                        <i class='bx bx-info-circle' style="color: var(--primary); font-size: 1.1rem; flex-shrink: 0;"></i>
                        <span>Username changes are currently managed by an administrator. Please contact your administrator for assistance.</span>
                    </div>
                </div>
            </div>
        `;

        if (user.role === 'Employee') {
            try {
                const data = await Api.get('/dashboard/employee');
                
                statsContainer.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-top">
                            <span>Total Products</span>
                            <div class="stat-icon blue"><i class='bx bx-package'></i></div>
                        </div>
                        <h2>${data.total_products || 0}</h2>
                    </div>
                    <div class="stat-card">
                        <div class="stat-top">
                            <span>Inventory Alerts</span>
                            <div class="stat-icon yellow"><i class='bx bx-error'></i></div>
                        </div>
                        <h2>${data.low_stock_products ? data.low_stock_products.length : 0}</h2>
                        <div class="stat-bottom warning-text">
                            <i class='bx bx-time'></i> Needs attention
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-top">
                            <span>Stock Ins</span>
                            <div class="stat-icon green"><i class='bx bx-transfer'></i></div>
                        </div>
                        <h2>${data.stock_in || 0}</h2>
                    </div>
                `;

                contentContainer.innerHTML = `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem;">
                        <!-- Low Stock Table -->
                        <div>
                            <div class="section-title">
                                <div>
                                    <h3>Low Stock Products</h3>
                                    <p>Products that require immediate restocking</p>
                                </div>
                            </div>
                            <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">NAME</th>
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">QTY</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.low_stock_products && data.low_stock_products.length > 0 
                                            ? data.low_stock_products.map(p => `
                                                <tr style="border-bottom: 1px solid #edf0ef;">
                                                    <td style="padding: 16px; font-weight: 600;">${Utils.escapeHtml(p.product_name)}</td>
                                                    <td style="padding: 16px; color: var(--red); font-weight: 700;">${p.quantity_available}</td>
                                                </tr>
                                            `).join('')
                                            : '<tr><td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">No low stock alerts.</td></tr>'
                                        }
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- My Tasks -->
                        <div>
                            <div class="section-title">
                                <div>
                                    <h3>My Tasks & Alerts</h3>
                                    <p>Your pending notifications</p>
                                </div>
                            </div>
                            <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">TASK</th>
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">DATE</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.tasks && data.tasks.length > 0 
                                            ? data.tasks.map(t => `
                                                <tr style="border-bottom: 1px solid #edf0ef;">
                                                    <td style="padding: 16px;">
                                                        <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(t.title)}</div>
                                                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${Utils.escapeHtml(t.message)}</div>
                                                    </td>
                                                    <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${new Date(t.created_at).toLocaleDateString()}</td>
                                                </tr>
                                            `).join('')
                                            : '<tr><td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">You have no pending tasks! 🎉</td></tr>'
                                        }
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    ${updateUsernameHtml}
                `;
            } catch (err) {}
        } else if (user.role === 'Supplier') {
            try {
                // Using mock data or real data from /dashboard/supplier
                // For now, simulating the layout exactly as in Screenshot 3.
                statsContainer.style.gridTemplateColumns = 'repeat(4, 1fr)';
                statsContainer.innerHTML = `
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Open Requests</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">04</div>
                                <div style="font-size: 12px; color: var(--green);"><i class='bx bx-trending-up'></i> +2 since yesterday</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center;"><i class='bx bx-clipboard'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Pending Quotations</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">02</div>
                                <div style="font-size: 12px; color: var(--yellow);"><i class='bx bx-time'></i> 1 expires today</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--yellow-light); color: var(--yellow); display: flex; align-items: center; justify-content: center;"><i class='bx bx-file'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Active POs</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">07</div>
                                <div style="font-size: 12px; color: var(--blue);"><i class='bx bx-package'></i> 5 in progress</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--blue-light); color: var(--blue); display: flex; align-items: center; justify-content: center;"><i class='bx bx-briefcase'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Pending Payments</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">₹2.84L</div>
                                <div style="font-size: 12px; color: var(--yellow);"><i class='bx bx-info-circle'></i> 2 invoices due</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--purple-light); color: var(--purple); display: flex; align-items: center; justify-content: center;"><i class='bx bx-rupee'></i></div>
                        </div>
                    </div>
                    <!-- Second row of stats -->
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 10px;">On-time Delivery</div>
                        <div style="font-size: 24px; font-weight: 700; margin-bottom: 10px;">96.4%</div>
                        <div style="width: 100%; height: 4px; background: var(--border); border-radius: 2px;">
                            <div style="width: 96.4%; height: 100%; background: var(--primary); border-radius: 2px;"></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 10px;">Quotation Acceptance</div>
                        <div style="font-size: 24px; font-weight: 700; margin-bottom: 10px;">91.8%</div>
                        <div style="width: 100%; height: 4px; background: var(--border); border-radius: 2px;">
                            <div style="width: 91.8%; height: 100%; background: var(--primary); border-radius: 2px;"></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 10px;">Order Acceptance</div>
                        <div style="font-size: 24px; font-weight: 700; margin-bottom: 10px;">98.1%</div>
                        <div style="width: 100%; height: 4px; background: var(--border); border-radius: 2px;">
                            <div style="width: 98.1%; height: 100%; background: var(--primary); border-radius: 2px;"></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 10px;">Profile Completion</div>
                        <div style="font-size: 24px; font-weight: 700; margin-bottom: 10px;">92%</div>
                        <div style="width: 100%; height: 4px; background: var(--border); border-radius: 2px;">
                            <div style="width: 92%; height: 100%; background: var(--primary); border-radius: 2px;"></div>
                        </div>
                    </div>
                `;

                contentContainer.innerHTML = `
                    <div style="background: var(--yellow-light); border: 1px solid var(--yellow); padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; gap: 15px; align-items: flex-start;">
                            <i class='bx bx-error' style="color: var(--yellow); font-size: 24px;"></i>
                            <div>
                                <h4 style="color: var(--text); margin-bottom: 5px;">4 stock requests need your response</h4>
                                <p style="color: var(--text-secondary); font-size: 14px;">Some requests have approaching deadlines.</p>
                            </div>
                        </div>
                        <button class="btn" style="color: var(--yellow); font-weight: 600; padding: 0;">Review now <i class='bx bx-right-arrow-alt'></i></button>
                    </div>

                    <div class="section-title">
                        <div>
                            <h3>Quick Actions</h3>
                            <p>Frequently used supplier operations</p>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem;">
                        <div class="card" style="padding: 1.5rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center;"><i class='bx bx-reply'></i></div>
                                <div>
                                    <div style="font-weight: 600; font-size: 13px;">Respond to Request</div>
                                    <div style="font-size: 11px; color: var(--text-light);">4 requests pending</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light);"></i>
                        </div>
                        <div class="card" style="padding: 1.5rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--yellow-light); color: var(--yellow); display: flex; align-items: center; justify-content: center;"><i class='bx bx-file-blank'></i></div>
                                <div>
                                    <div style="font-weight: 600; font-size: 13px;">Create Quotation</div>
                                    <div style="font-size: 11px; color: var(--text-light);">Prepare new quotation</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light);"></i>
                        </div>
                        <div class="card" style="padding: 1.5rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--blue-light); color: var(--blue); display: flex; align-items: center; justify-content: center;"><i class='bx bx-bell'></i></div>
                                <div>
                                    <div style="font-weight: 600; font-size: 13px;">Notifications</div>
                                    <div style="font-size: 11px; color: var(--text-light);">View alerts</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light);"></i>
                        </div>
                        <div class="card" style="padding: 1.5rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--purple-light); color: var(--purple); display: flex; align-items: center; justify-content: center;"><i class='bx bx-receipt'></i></div>
                                <div>
                                    <div style="font-weight: 600; font-size: 13px;">Check Payments</div>
                                    <div style="font-size: 11px; color: var(--text-light);">₹2.84L pending</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light);"></i>
                        </div>
                    </div>
                `;
            } catch (err) {}
        } else if (user.role === 'Manager') {
            try {
                const data = await Api.get('/dashboard/manager');
                
                statsContainer.style.gridTemplateColumns = 'repeat(4, 1fr)';
                statsContainer.innerHTML = `
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Active POs</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.active_pos || 0}</div>
                                <div style="font-size: 12px; color: var(--blue);"><i class='bx bx-trending-up'></i> In Progress</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--blue-light); color: var(--blue); display: flex; align-items: center; justify-content: center;"><i class='bx bx-briefcase'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Pending PO Value</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">₹${data.pending_po_value ? data.pending_po_value.toLocaleString() : '0'}</div>
                                <div style="font-size: 12px; color: var(--purple);"><i class='bx bx-time'></i> Awaiting fulfillment</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--purple-light); color: var(--purple); display: flex; align-items: center; justify-content: center;"><i class='bx bx-rupee'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Low Stock Alerts</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.low_stock_count || 0}</div>
                                <div style="font-size: 12px; color: var(--red);"><i class='bx bx-error'></i> Requires action</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--red-light); color: var(--red); display: flex; align-items: center; justify-content: center;"><i class='bx bx-box'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">30-Day Movement</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.recent_stock_movement || 0}</div>
                                <div style="font-size: 12px; color: var(--green);"><i class='bx bx-transfer'></i> Total units transacted</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center;"><i class='bx bx-line-chart'></i></div>
                        </div>
                    </div>
                `;

                contentContainer.innerHTML = `
                    <div class="section-title">
                        <div>
                            <h3>Recent Stock Transactions</h3>
                            <p>Latest movements across the warehouse</p>
                        </div>
                    </div>
                    <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden; margin-bottom: 2rem;">
                        <table style="width: 100%; text-align: left; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">PRODUCT</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">TYPE</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">QUANTITY</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">DATE</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.recent_transactions && data.recent_transactions.length > 0 
                                    ? data.recent_transactions.map(t => `
                                        <tr style="border-bottom: 1px solid #edf0ef;">
                                            <td style="padding: 16px; font-weight: 600;">${Utils.escapeHtml(t.product_name)}</td>
                                            <td style="padding: 16px;">
                                                <span class="badge" style="background: var(${t.transaction_type === 'STOCK_IN' ? '--green-light' : '--red-light'}); color: var(${t.transaction_type === 'STOCK_IN' ? '--green' : '--red'}); font-weight: 600;">
                                                    ${t.transaction_type}
                                                </span>
                                            </td>
                                            <td style="padding: 16px; font-weight: 700;">${t.quantity}</td>
                                            <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${new Date(t.transaction_date).toLocaleDateString()}</td>
                                        </tr>
                                    `).join('')
                                    : '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">No recent transactions.</td></tr>'
                                }
                            </tbody>
                        </table>
                    </div>
                    ${updateUsernameHtml}
                `;
            } catch (err) {}
        } else if (user.role === 'Owner') {
            try {
                const data = await Api.get('/dashboard/owner');
                
                statsContainer.style.gridTemplateColumns = 'repeat(4, 1fr)';
                statsContainer.innerHTML = `
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Total Users</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.total_users || 0}</div>
                                <div style="font-size: 12px; color: var(--blue);"><i class='bx bx-group'></i> Active Accounts</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--blue-light); color: var(--blue); display: flex; align-items: center; justify-content: center;"><i class='bx bx-user-pin'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Registered Suppliers</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.total_suppliers || 0}</div>
                                <div style="font-size: 12px; color: var(--green);"><i class='bx bx-buildings'></i> Network Partners</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center;"><i class='bx bx-network-chart'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Total Products</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.total_products || 0}</div>
                                <div style="font-size: 12px; color: var(--purple);"><i class='bx bx-category'></i> Catalog Size</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--purple-light); color: var(--purple); display: flex; align-items: center; justify-content: center;"><i class='bx bx-category-alt'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Inventory Value</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">₹${data.total_inventory_value ? data.total_inventory_value.toLocaleString() : '0'}</div>
                                <div style="font-size: 12px; color: var(--yellow);"><i class='bx bx-line-chart'></i> Current Asset Worth</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--yellow-light); color: var(--yellow); display: flex; align-items: center; justify-content: center;"><i class='bx bx-rupee'></i></div>
                        </div>
                    </div>
                `;

                contentContainer.innerHTML = `
                    <div class="section-title">
                        <div>
                            <h3>Recent System Audit Logs</h3>
                            <p>Global security and activity monitoring</p>
                        </div>
                    </div>
                    <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden; margin-bottom: 2rem;">
                        <table style="width: 100%; text-align: left; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">USER</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">ACTION</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">DETAILS</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">TIME</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.recent_audits && data.recent_audits.length > 0 
                                    ? data.recent_audits.map(a => `
                                        <tr style="border-bottom: 1px solid #edf0ef;">
                                            <td style="padding: 16px; font-weight: 600;">
                                                <div style="display: flex; align-items: center; gap: 8px;">
                                                    <div style="width: 24px; height: 24px; border-radius: 50%; background: var(--bg); display: flex; align-items: center; justify-content: center; font-size: 12px; color: var(--text-secondary);"><i class='bx bx-user'></i></div>
                                                    ${Utils.escapeHtml(a.username)}
                                                </div>
                                            </td>
                                            <td style="padding: 16px; font-weight: 600;">${Utils.escapeHtml(a.action)}</td>
                                            <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${Utils.escapeHtml(a.details)}</td>
                                            <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${new Date(a.timestamp).toLocaleString()}</td>
                                        </tr>
                                    `).join('')
                                    : '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">No recent audit logs.</td></tr>'
                                }
                            </tbody>
                        </table>
                    </div>
                    ${updateUsernameHtml}
                `;
            } catch (err) {}
        }

        // Attach event listener for change username (informational advisory; API managed by admin)
        const btnChangeUsername = document.getElementById('btn-change-username');
        if (btnChangeUsername) {
            btnChangeUsername.addEventListener('click', (e) => {
                e.preventDefault();
                Utils.showToast("Username changes are currently managed by an administrator. Please contact your administrator for assistance.", "info");
            });
        }
    }
};
