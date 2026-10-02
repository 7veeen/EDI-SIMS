// system-status.js

App.pages['system-status'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1.25rem; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
                <div>
                    <h2 style="margin: 0; font-size: 1.35rem; display: flex; align-items: center; gap: 0.6rem;">
                        <i class='bx bx-pulse' style="color: var(--primary);"></i> System Health & Monitoring
                    </h2>
                    <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; color: var(--gray);">
                        Real-time infrastructure health, database latency benchmarks, and subsystem telemetry
                    </p>
                </div>
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div id="system-overall-badge">
                        <span class="status-badge status-pending"><i class='bx bx-loader-alt bx-spin'></i> Probing Health...</span>
                    </div>
                    <button class="btn btn-secondary" id="btn-refresh-status" style="display: flex; align-items: center; gap: 0.4rem;">
                        <i class='bx bx-refresh'></i> Refresh
                    </button>
                </div>
            </div>

            <!-- Health Summary Metric Cards -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem;" id="health-metric-cards">
                <div class="glass-panel" id="card-overall" style="padding: 1.25rem; border-radius: 10px; border-left: 4px solid #10b981;">
                    <div style="display: flex; justify-content: space-between; align-items: center; color: var(--gray); font-size: 0.85rem;">
                        <span>OVERALL SYSTEM</span>
                        <i class='bx bx-shield-quarter' style="font-size: 1.2rem;"></i>
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 1.4rem; font-weight: 700;" id="val-overall">--</div>
                    <div style="font-size: 0.8rem; color: var(--gray); margin-top: 0.25rem;" id="sub-overall">Evaluating...</div>
                </div>

                <div class="glass-panel" id="card-backend" style="padding: 1.25rem; border-radius: 10px; border-left: 4px solid #3b82f6;">
                    <div style="display: flex; justify-content: space-between; align-items: center; color: var(--gray); font-size: 0.85rem;">
                        <span>BACKEND API</span>
                        <i class='bx bx-server' style="font-size: 1.2rem;"></i>
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 1.4rem; font-weight: 700;" id="val-backend">--</div>
                    <div style="font-size: 0.8rem; color: var(--gray); margin-top: 0.25rem;" id="sub-backend">Uptime: --</div>
                </div>

                <div class="glass-panel" id="card-database" style="padding: 1.25rem; border-radius: 10px; border-left: 4px solid #8b5cf6;">
                    <div style="display: flex; justify-content: space-between; align-items: center; color: var(--gray); font-size: 0.85rem;">
                        <span>DATABASE ENGINE</span>
                        <i class='bx bx-data' style="font-size: 1.2rem;"></i>
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 1.4rem; font-weight: 700;" id="val-database">--</div>
                    <div style="font-size: 0.8rem; color: var(--gray); margin-top: 0.25rem;" id="sub-database">Connectivity: --</div>
                </div>

                <div class="glass-panel" id="card-latency" style="padding: 1.25rem; border-radius: 10px; border-left: 4px solid #10b981;">
                    <div style="display: flex; justify-content: space-between; align-items: center; color: var(--gray); font-size: 0.85rem;">
                        <span>QUERY LATENCY</span>
                        <i class='bx bx-timer' style="font-size: 1.2rem;"></i>
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 1.4rem; font-weight: 700;" id="val-latency">-- ms</div>
                    <div style="font-size: 0.8rem; color: var(--gray); margin-top: 0.25rem;" id="sub-latency">Benchmark benchmark</div>
                </div>
            </div>

            <!-- Performance Warning Banner (Displayed separately from connectivity & backend status) -->
            <div id="perf-warning-banner" class="glass-panel" style="display: none; padding: 1rem 1.25rem; border-radius: 8px; background: rgba(245, 158, 11, 0.08); border-left: 4px solid #f59e0b; margin-bottom: 1.5rem; align-items: center; gap: 0.85rem;">
                <i class='bx bx-error-circle' style="font-size: 1.6rem; color: #f59e0b; flex-shrink: 0;"></i>
                <div style="font-size: 0.9rem; color: #92400e;">
                    <strong>Performance Advisory:</strong> Database query response time (<span id="banner-latency-ms">--</span>) exceeds the documented benchmark threshold (500 ms). Database connectivity is active, but response latency is elevated.
                </div>
            </div>

            <!-- Monitored Subsystems & Inventory Module Health -->
            <div class="glass-panel table-container" style="padding: 1.25rem; border-radius: 10px; margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h3 style="margin: 0; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;">
                            <i class='bx bx-chip'></i> Subsystem Health & Module Telemetry
                        </h3>
                        <p style="margin: 0.2rem 0 0 0; font-size: 0.8rem; color: var(--gray);">
                            Real-time synchronization status from the SystemStatus registry
                        </p>
                    </div>
                    <span style="font-size: 0.75rem; color: var(--gray);" id="last-updated-text"></span>
                </div>

                <table id="subsystems-table" style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Module Name</th>
                            <th>Status</th>
                            <th>Progress</th>
                            <th>Telemetry Message</th>
                            <th>Last Updated</th>
                        </tr>
                    </thead>
                    <tbody id="subsystems-tbody">
                        <tr><td colspan="5" style="text-align: center; padding: 1.5rem;">Loading subsystem status...</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Server Telemetry Metadata -->
            <div class="glass-panel" style="padding: 1.25rem; border-radius: 10px; font-size: 0.85rem; color: var(--gray);">
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                    <div><strong>API Endpoint:</strong> <code>GET /api/status/health</code></div>
                    <div><strong>Server Timestamp:</strong> <span id="telemetry-timestamp">--</span></div>
                    <div><strong>Process Uptime:</strong> <span id="telemetry-uptime">--</span></div>
                </div>
            </div>
        `;
        return container;
    },

    async init() {
        this.loadSystemHealth();

        document.getElementById('btn-refresh-status')?.addEventListener('click', () => {
            this.loadSystemHealth();
        });
    },

    formatUptime(seconds) {
        if (!seconds && seconds !== 0) return 'N/A';
        const d = Math.floor(seconds / 86400);
        const h = Math.floor((seconds % 86400) / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        const parts = [];
        if (d > 0) parts.push(`${d}d`);
        if (h > 0 || d > 0) parts.push(`${h}h`);
        if (m > 0 || h > 0 || d > 0) parts.push(`${m}m`);
        parts.push(`${s}s`);
        return parts.join(' ');
    },

    async loadSystemHealth() {
        const btnRefresh = document.getElementById('btn-refresh-status');
        if (btnRefresh) {
            btnRefresh.disabled = true;
            btnRefresh.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Checking...`;
        }

        const badgeContainer = document.getElementById('system-overall-badge');
        const cardOverall = document.getElementById('card-overall');
        const valOverall = document.getElementById('val-overall');
        const subOverall = document.getElementById('sub-overall');
        const valBackend = document.getElementById('val-backend');
        const subBackend = document.getElementById('sub-backend');
        const valDatabase = document.getElementById('val-database');
        const subDatabase = document.getElementById('sub-database');
        const cardLatency = document.getElementById('card-latency');
        const valLatency = document.getElementById('val-latency');
        const subLatency = document.getElementById('sub-latency');
        const banner = document.getElementById('perf-warning-banner');
        const bannerLatency = document.getElementById('banner-latency-ms');
        const tbody = document.getElementById('subsystems-tbody');
        const lastUpdated = document.getElementById('last-updated-text');
        const metaTimestamp = document.getElementById('telemetry-timestamp');
        const metaUptime = document.getElementById('telemetry-uptime');

        try {
            const token = localStorage.getItem('sims_token') || localStorage.getItem('sims_access_token');
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`${API_BASE_URL}/status/health`, { headers });

            if (response.status === 401) {
                Auth.logout();
                Utils.showToast("Session expired. Please log in again.", "error");
                return;
            }

            if (response.status === 403) {
                Utils.showToast("Access denied: Health monitoring is restricted to Owner and Manager.", "error");
                if (tbody) {
                    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--red);">Access denied. You do not have permission to view health telemetry.</td></tr>`;
                }
                return;
            }

            const data = await response.json().catch(() => null);

            if (!data) {
                throw new Error("Invalid or empty response from health monitoring service.");
            }

            const isHealthy = data.overall_status === 'HEALTHY';
            const dbConnected = data.database?.status === 'CONNECTED';
            const rawLatency = data.database?.latency_ms;
            const hasLatency = rawLatency !== null && rawLatency !== undefined && !isNaN(Number(rawLatency));
            const formattedLatency = hasLatency ? Number(rawLatency).toFixed(2) : null;
            const perfWarning = data.database?.performance_warning ?? data.performance_warning ?? false;
            const dbPerf = data.database?.performance || (hasLatency && Number(rawLatency) > 500 ? 'ELEVATED' : 'NORMAL');

            // Overall status badge & card
            if (badgeContainer) {
                if (isHealthy) {
                    badgeContainer.innerHTML = `<span class="status-badge status-active"><i class='bx bx-check-circle'></i> SYSTEM HEALTHY</span>`;
                } else {
                    badgeContainer.innerHTML = `<span class="status-badge status-pending"><i class='bx bx-error-circle'></i> SYSTEM DEGRADED</span>`;
                }
            }

            if (valOverall) {
                valOverall.textContent = data.overall_status || 'UNKNOWN';
                valOverall.style.color = isHealthy ? '#10b981' : '#f59e0b';
            }
            if (cardOverall) {
                cardOverall.style.borderLeftColor = isHealthy ? '#10b981' : '#f59e0b';
            }
            if (subOverall) {
                if (isHealthy) {
                    subOverall.textContent = 'All services & latency operational';
                } else if (!dbConnected) {
                    subOverall.textContent = 'Database offline';
                } else if (perfWarning) {
                    subOverall.textContent = 'Elevated database latency';
                } else {
                    subOverall.textContent = 'Subsystem attention required';
                }
            }

            // Backend API Card
            if (valBackend) {
                valBackend.textContent = data.backend?.status || 'UNKNOWN';
                valBackend.style.color = data.backend?.status === 'UP' ? '#10b981' : '#ef4444';
            }
            if (subBackend) {
                subBackend.textContent = `Uptime: ${this.formatUptime(data.uptime_seconds)}`;
            }

            // Database Engine Card (Kept separate from performance!)
            if (valDatabase) {
                valDatabase.textContent = data.database?.status || 'DISCONNECTED';
                valDatabase.style.color = dbConnected ? '#10b981' : '#ef4444';
            }
            if (subDatabase) {
                subDatabase.textContent = dbConnected ? 'PostgreSQL Active' : 'Connection failed';
            }

            // Database Query Latency Card (Evaluated against documented 500ms threshold)
            if (valLatency) {
                valLatency.textContent = formattedLatency !== null ? `${formattedLatency} ms` : 'N/A';
                if (hasLatency) {
                    if (perfWarning || dbPerf === 'ELEVATED') {
                        valLatency.style.color = '#f59e0b';
                        if (cardLatency) cardLatency.style.borderLeftColor = '#f59e0b';
                    } else {
                        valLatency.style.color = '#10b981';
                        if (cardLatency) cardLatency.style.borderLeftColor = '#10b981';
                    }
                } else {
                    valLatency.style.color = '#ef4444';
                    if (cardLatency) cardLatency.style.borderLeftColor = '#ef4444';
                }
            }
            if (subLatency) {
                if (hasLatency) {
                    if (perfWarning || dbPerf === 'ELEVATED') {
                        subLatency.textContent = 'Elevated latency (> 500 ms warning)';
                        subLatency.style.color = '#b45309';
                    } else {
                        subLatency.textContent = 'Normal latency (≤ 500 ms)';
                        subLatency.style.color = 'var(--gray)';
                    }
                } else {
                    subLatency.textContent = 'Benchmark unavailable';
                    subLatency.style.color = 'var(--gray)';
                }
            }

            // Performance Warning Banner (Displayed separately from connectivity & backend status)
            if (banner) {
                if (perfWarning) {
                    banner.style.display = 'flex';
                    if (bannerLatency) bannerLatency.textContent = formattedLatency !== null ? `${formattedLatency} ms` : '--';
                } else {
                    banner.style.display = 'none';
                }
            }

            // Subsystems Table
            if (tbody) {
                const modules = data.modules || [];
                if (modules.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--gray);">No subsystem telemetry recorded.</td></tr>`;
                } else {
                    tbody.innerHTML = modules.map(m => {
                        let badgeClass = 'status-active';
                        if (m.status !== 'READY') badgeClass = 'status-pending';

                        const formattedDate = m.updated_at ? Utils.formatDate(m.updated_at) : 'N/A';

                        return `
                            <tr>
                                <td><strong>${Utils.escapeHtml(m.name || 'Unknown')}</strong></td>
                                <td><span class="status-badge ${badgeClass}">${Utils.escapeHtml(m.status || 'UNKNOWN')}</span></td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                                        <div style="background: #e2e8f0; border-radius: 4px; height: 8px; width: 80px; overflow: hidden;">
                                            <div style="background: var(--primary); height: 100%; width: ${m.progress || 0}%;"></div>
                                        </div>
                                        <span style="font-size: 0.8rem; color: var(--gray);">${m.progress || 0}%</span>
                                    </div>
                                </td>
                                <td><span style="font-size: 0.85rem; color: var(--gray);">${Utils.escapeHtml(m.message || '')}</span></td>
                                <td><span style="font-size: 0.85rem; color: var(--gray);">${formattedDate}</span></td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            // Metadata footer
            const now = new Date();
            if (lastUpdated) lastUpdated.textContent = `Last checked: ${now.toLocaleTimeString()}`;
            if (metaTimestamp) metaTimestamp.textContent = data.checked_at || now.toISOString();
            if (metaUptime) metaUptime.textContent = `${this.formatUptime(data.uptime_seconds)} (${data.uptime_seconds || 0}s)`;

        } catch (error) {
            if (badgeContainer) {
                badgeContainer.innerHTML = `<span class="status-badge status-inactive"><i class='bx bx-wifi-off'></i> BACKEND OFFLINE</span>`;
            }
            if (valOverall) {
                valOverall.textContent = 'UNREACHABLE';
                valOverall.style.color = '#ef4444';
            }
            if (cardOverall) cardOverall.style.borderLeftColor = '#ef4444';
            if (subOverall) subOverall.textContent = 'Server unreachable';
            if (valBackend) {
                valBackend.textContent = 'DOWN';
                valBackend.style.color = '#ef4444';
            }
            if (valDatabase) {
                valDatabase.textContent = 'UNKNOWN';
                valDatabase.style.color = '#ef4444';
            }
            if (valLatency) {
                valLatency.textContent = 'N/A';
                valLatency.style.color = '#ef4444';
            }
            if (cardLatency) cardLatency.style.borderLeftColor = '#ef4444';
            if (banner) banner.style.display = 'none';
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--red);">Unable to contact health telemetry service: ${Utils.escapeHtml(error.message || 'Network error')}</td></tr>`;
            }
            Utils.showToast("Failed to fetch system health telemetry", "error");
        } finally {
            if (btnRefresh) {
                btnRefresh.disabled = false;
                btnRefresh.innerHTML = `<i class='bx bx-refresh'></i> Refresh`;
            }
        }
    }
};
