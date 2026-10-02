// View: System Section (Audit Logs, Backup Center, System Status, Users & Roles, Settings)
const SystemView = {
  // 1. Audit Logs View
  renderAuditLogs() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Security Audit Logs</h2>
              <p>Immutable forensic record of all entity mutations, action types, and origin IP addresses</p>
            </div>
            <div class="action-controls">
              <button class="btn-secondary" onclick="App.exportAuditLogs()">
                ${Icons.download} Export Logs
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search audit logs..." oninput="App.filterTable(this, 'table-audit')"/>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-audit">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Log ID</th>
                  <th>User / Actor</th>
                  <th>Action</th>
                  <th>Target Table</th>
                  <th>Record ID</th>
                  <th>Origin IP</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                ${Store.auditLogs.map(l => {
                  let actionClass = "active";
                  if (l.action === "UPDATE") actionClass = "lowstock";
                  if (l.action === "DELETE") actionClass = "cancel";

                  return `
                    <tr>
                      <td><input type="checkbox" class="table-checkbox" /></td>
                      <td><code>LOG-#${l.log_id}</code></td>
                      <td><strong>${l.user}</strong></td>
                      <td><span class="status-pill ${actionClass}">${l.action}</span></td>
                      <td><code>"${l.table}"</code></td>
                      <td>#${l.record_id}</td>
                      <td><code>${l.ip}</code></td>
                      <td style="color: #64748b;">${l.time}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.auditLogs.length} of ${Store.auditLogs.length} entries</div>
            <div class="pagination-controls">
              <button class="page-btn">${Icons.chevronLeft}</button>
              <button class="page-btn active">1</button>
              <button class="page-btn">${Icons.chevronRight}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  // 2. Backup Center View
  renderBackups() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Database Backup Center</h2>
              <p>Point-in-time complete JSON database dumps for disaster recovery and offline compliance</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.triggerNewBackup()">
                ${Icons.backups} Create Full Backup
              </button>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-backups">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Backup File Name</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Initiated By</th>
                  <th>Date & Time</th>
                  <th>Status</th>
                  <th style="text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${Store.backups.map(b => `
                  <tr>
                    <td><input type="checkbox" class="table-checkbox" /></td>
                    <td>
                      <div class="entity-cell">
                        <div class="entity-icon-avatar" style="background: rgba(16, 185, 129, 0.12); color: #059669;">
                          ${Icons.backups}
                        </div>
                        <div>
                          <div class="entity-name">${b.backup_name}</div>
                          <div class="entity-sub">JSON Relational Dump</div>
                        </div>
                      </div>
                    </td>
                    <td><span class="status-pill role">${b.backup_type}</span></td>
                    <td><strong>${b.backup_size}</strong></td>
                    <td>${b.created_by}</td>
                    <td style="color: #64748b;">${b.date}</td>
                    <td><span class="status-pill active">${b.status}</span></td>
                    <td style="text-align: right;">
                      <button class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="App.downloadBackup('${b.backup_name}')">
                        ${Icons.download} Download
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  },

  // 3. System Status View
  renderSystemStatus() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>System Module Health & Telemetry</h2>
              <p>Real-time status monitoring of core micro-services and database sync integrity</p>
            </div>
          </div>

          <div style="padding: 24px;">
            <div class="kpi-grid" style="grid-template-columns: repeat(2, 1fr); margin-bottom: 0;">
              ${Store.systemStatus.map(s => `
                <div style="border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 18px; background: #ffffff;">
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <div class="pulse-dot"></div>
                      <strong style="font-size: 15px;">${s.module_name}</strong>
                    </div>
                    <span class="status-pill active">${s.status}</span>
                  </div>
                  <p style="font-size: 12.5px; color: var(--text-muted); margin-bottom: 12px;">${s.message}</p>
                  <div>
                    <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; font-weight: 600;">
                      <span>Operational Health</span>
                      <span>${s.progress}%</span>
                    </div>
                    <div style="height: 6px; width: 100%; background: #e2e8f0; border-radius: 9999px; overflow: hidden;">
                      <div style="height: 100%; width: ${s.progress}%; background: #10b981; border-radius: 9999px;"></div>
                    </div>
                  </div>
                  <div style="margin-top: 10px; font-size: 10.5px; color: #94a3b8;">Synchronized: ${s.updated_at}</div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      </div>
    `;
  },

  // 4. Users & Roles View
  renderUsers() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>User Accounts & Governance</h2>
              <p>System access control, RBAC role assignments, and account active state management</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-add-user')">
                ${Icons.plus} Onboard New User
              </button>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-users">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>User Details</th>
                  <th>Email Address</th>
                  <th>Assigned Role</th>
                  <th>Account Status</th>
                  <th style="text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${Store.users.map(u => `
                  <tr>
                    <td><input type="checkbox" class="table-checkbox" /></td>
                    <td>
                      <div class="entity-cell">
                        <div class="entity-icon-avatar" style="background: rgba(59, 130, 246, 0.12); color: #2563eb;">
                          ${u.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div class="entity-name">${u.username}</div>
                          <div class="entity-sub">ID: #${u.user_id}</div>
                        </div>
                      </div>
                    </td>
                    <td>${u.email}</td>
                    <td><span class="status-pill role">${u.role}</span></td>
                    <td><span class="status-pill ${u.status === 'Active' ? 'active' : 'cancel'}">${u.status}</span></td>
                    <td style="text-align: right;">
                      <button class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="App.toggleUserStatus(${u.user_id})">
                        Toggle Status
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  },

  // 5. Settings View
  renderSettings() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>System Settings & Configuration</h2>
              <p>API endpoint bindings, inventory safety thresholds, and developer preferences</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.saveSettings()">Save Configuration</button>
            </div>
          </div>

          <div style="padding: 24px; max-width: 650px;">
            <div class="form-group">
              <label>Backend API Base URL</label>
              <input type="text" id="setting-api-url" class="form-control" value="${Store.settings.apiUrl}" />
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Default Flask WSGI server port: <code>http://127.0.0.1:5000</code></div>
            </div>

            <div class="form-group">
              <label>Global Low-Stock Reorder Threshold</label>
              <input type="number" id="setting-threshold" class="form-control" value="${Store.settings.lowStockThreshold}" />
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Items with stock less than or equal to this limit trigger warnings.</div>
            </div>

            <div class="form-group">
              <label>Currency Display Symbol</label>
              <select id="setting-currency" class="form-control">
                <option value="INR" selected>INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
              </select>
            </div>

            <div class="form-group" style="margin-top: 24px; padding: 16px; background-color: #f8fafc; border: 1px solid var(--border-color); border-radius: var(--radius-md);">
              <label style="color: var(--text-main); font-weight: 700;">Active JWT Session Token</label>
              <div style="font-size: 11px; color: var(--text-muted); word-break: break-all; font-family: monospace; padding: 8px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; margin-top: 6px;">
                ${API.getToken() || "No token stored. Login via API to store live token."}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }
};

