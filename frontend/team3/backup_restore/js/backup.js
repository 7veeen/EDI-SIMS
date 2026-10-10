const backupTableBody = document.getElementById("backup-table-body");
const createBackupButton = document.getElementById("create-backup-btn");
const refreshButton = document.getElementById("refresh-btn");

function getBackupList(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.backups)) return data.backups;
    if (Array.isArray(data?.history)) return data.history;
    return [];
}

function applyRolePermissions() {
    const allowed = typeof canManageBackups === "function" && canManageBackups();
    document.querySelectorAll("[data-role-action='manage']").forEach(button => {
        button.hidden = !allowed;
    });
}

function makeCell(value, className = "") {
    const cell = document.createElement("td");
    if (className) cell.className = className;
    cell.textContent = value === null || value === undefined || value === "" ? "-" : String(value);
    return cell;
}

function displayBackups(backups) {
    if (!backupTableBody) return;
    backupTableBody.replaceChildren();
    if (!backups.length) {
        const row = document.createElement("tr");
        const cell = makeCell("No backups found.", "empty-row");
        cell.colSpan = 7;
        row.appendChild(cell);
        backupTableBody.appendChild(row);
        return;
    }

    const canManage = canManageBackups();
    backups.forEach(backup => {
        const row = document.createElement("tr");
        row.append(
            makeCell(backup.backup_id),
            makeCell(backup.backup_name, "backup-name"),
            makeCell(backup.backup_type),
            makeCell(formatDate(backup.backup_date)),
            makeCell(formatFileSize(backup.backup_size))
        );
        const statusCell = document.createElement("td");
        const badge = document.createElement("span");
        const status = String(backup.status || "Unknown");
        badge.className = `status ${status.toLowerCase() === "success" ? "status-success" : "status-failed"}`;
        badge.textContent = status;
        statusCell.appendChild(badge);
        row.appendChild(statusCell);

        const actionCell = document.createElement("td");
        const actions = document.createElement("div");
        actions.className = "action-buttons";
        const id = Number(backup.backup_id);
        const addAction = (label, action, className) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = `action-btn ${className}`;
            button.textContent = label;
            button.dataset.action = action;
            button.dataset.backupId = String(id);
            if (["restore", "delete"].includes(action)) button.hidden = !canManage;
            actions.appendChild(button);
        };
        if (Number.isSafeInteger(id) && id > 0) {
            addAction("View", "view", "view-btn");
            addAction("Download", "download", "download-btn");
            addAction("Restore", "restore", "restore-btn");
            addAction("Delete", "delete", "delete-btn");
        }
        actionCell.appendChild(actions);
        row.appendChild(actionCell);
        backupTableBody.appendChild(row);
    });
}

function updateSummary(backups) {
    document.getElementById("total-backups").textContent = String(backups.length);
    const latest = [...backups].sort((a, b) => new Date(b.backup_date) - new Date(a.backup_date))[0];
    document.getElementById("latest-backup").textContent = latest ? formatDate(latest.backup_date) : "No backup";
    document.getElementById("backup-status").textContent = latest ? (latest.status || "Unknown") : "No Backups";
}

async function loadBackups() {
    showLoading("Loading backup history...");
    hideError();
    try {
        const backups = getBackupList(await apiGet("/api/backups"));
        displayBackups(backups);
        updateSummary(backups);
    } catch (error) {
        showError(error.message || "Unable to load backup history.");
    } finally {
        hideLoading();
    }
}

async function createBackup() {
    if (!confirmAction("Create a new full backup now?")) return;
    createBackupButton.disabled = true;
    showLoading("Creating backup...");
    hideError();
    hideSuccess();
    try {
        const result = await apiPost("/api/backups");
        showSuccess(result.message || "Backup created successfully.");
        await loadBackups();
    } catch (error) {
        showError(error.message || "Unable to create backup.");
    } finally {
        hideLoading();
        createBackupButton.disabled = false;
    }
}

async function viewBackup(backupId) {
    showLoading("Loading backup details...");
    hideError();
    try {
        const data = await apiGet(`/api/backups/${backupId}`);
        const backup = data.backup || data;
        alert([
            `Backup ID: ${backup.backup_id ?? "-"}`,
            `Backup Name: ${backup.backup_name ?? "-"}`,
            `Backup Type: ${backup.backup_type ?? "-"}`,
            `Backup Date: ${formatDate(backup.backup_date)}`,
            `Backup Size: ${formatFileSize(backup.backup_size)}`,
            `Status: ${backup.status ?? "-"}`,
            `Created By: ${backup.created_by ?? "-"}`
        ].join("\n"));
    } catch (error) {
        showError(error.message || "Unable to load backup details.");
    } finally {
        hideLoading();
    }
}

if (createBackupButton) createBackupButton.addEventListener("click", createBackup);
if (refreshButton) refreshButton.addEventListener("click", loadBackups);
if (backupTableBody) {
    backupTableBody.addEventListener("click", event => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;
        const id = Number(button.dataset.backupId);
        if (button.dataset.action === "view") viewBackup(id);
        if (button.dataset.action === "download") downloadBackup(id);
        if (button.dataset.action === "restore") openRestoreModal(id);
        if (button.dataset.action === "delete") openDeleteModal(id);
    });
}
document.addEventListener("DOMContentLoaded", loadBackups);
