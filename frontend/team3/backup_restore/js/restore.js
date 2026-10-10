let selectedBackupId = null;
let restoreDryRunSuccessful = false;

const restoreBackupName = document.getElementById("restore-backup-name");
const restoreBackupDate = document.getElementById("restore-backup-date");
const restoreButton = document.getElementById("actual-restore-btn");
const dryRunButton = document.getElementById("dry-run-btn");
const restoreResult = document.getElementById("restore-result");

function showRestoreResult(message, isError = false, results = null) {
    if (!restoreResult) return;
    restoreResult.replaceChildren();
    const summary = document.createElement("p");
    summary.textContent = message;
    restoreResult.appendChild(summary);
    if (Array.isArray(results) && results.length) {
        const list = document.createElement("ul");
        results.forEach(item => {
            const entry = document.createElement("li");
            entry.textContent = `${item.table || "Table"}: ${item.records ?? item.records_processed ?? 0} records (${item.status || "planned"})`;
            list.appendChild(entry);
        });
        restoreResult.appendChild(list);
    }
    restoreResult.classList.toggle("restore-error", isError);
    restoreResult.classList.toggle("restore-success", !isError);
    restoreResult.classList.remove("hidden");
}

function hideRestoreResult() {
    if (!restoreResult) return;
    restoreResult.replaceChildren();
    restoreResult.classList.add("hidden");
    restoreResult.classList.remove("restore-error", "restore-success");
}

async function openRestoreModal(backupId) {
    selectedBackupId = backupId;
    restoreDryRunSuccessful = false;
    if (restoreButton) restoreButton.disabled = true;
    hideRestoreResult();
    hideError();
    showLoading("Loading backup information...");
    try {
        const data = await apiGet(`/api/backups/${backupId}`);
        const backup = data.backup || data;
        restoreBackupName.textContent = backup.backup_name || "-";
        restoreBackupDate.textContent = formatDate(backup.backup_date);
        openModal("restore-modal");
    } catch (error) {
        showError(error.message || "Unable to load backup information.");
    } finally {
        hideLoading();
    }
}

async function runRestoreDryRun() {
    if (!selectedBackupId) return;
    restoreDryRunSuccessful = false;
    restoreButton.disabled = true;
    dryRunButton.disabled = true;
    showLoading("Validating backup...");
    hideRestoreResult();
    try {
        const result = await apiPost(`/api/backups/${selectedBackupId}/restore`, { dry_run: true });
        if (result.valid !== true || result.dry_run !== true) {
            throw new Error(result.message || "Backup validation did not succeed.");
        }
        restoreDryRunSuccessful = true;
        showRestoreResult(result.message || "Dry run completed successfully.", false, result.restore_order);
        restoreButton.disabled = false;
    } catch (error) {
        showRestoreResult(error.message || "Backup validation failed.", true);
    } finally {
        hideLoading();
        dryRunButton.disabled = false;
    }
}

async function performRestore() {
    if (!selectedBackupId || !restoreDryRunSuccessful) {
        showRestoreResult("Run a successful dry run before restoring.", true);
        return;
    }
    if (!confirmAction(`Confirm actual restore of ${restoreBackupName.textContent}? Existing records with matching IDs may be updated.`)) return;
    restoreButton.disabled = true;
    dryRunButton.disabled = true;
    showLoading("Restoring backup...");
    hideRestoreResult();
    try {
        const result = await apiPost(`/api/backups/${selectedBackupId}/restore`, { dry_run: false });
        showRestoreResult(result.message || "Backup restored successfully.", false, result.results);
        restoreDryRunSuccessful = false;
        await loadBackups();
    } catch (error) {
        showRestoreResult(error.message || "Backup restore failed.", true);
    } finally {
        hideLoading();
        dryRunButton.disabled = false;
        restoreButton.disabled = !restoreDryRunSuccessful;
    }
}

function closeRestoreModal() {
    selectedBackupId = null;
    restoreDryRunSuccessful = false;
    if (restoreButton) restoreButton.disabled = true;
    hideRestoreResult();
    closeModal("restore-modal");
}

if (dryRunButton) dryRunButton.addEventListener("click", runRestoreDryRun);
if (restoreButton) restoreButton.addEventListener("click", performRestore);
document.querySelectorAll('[data-modal="restore-modal"]').forEach(button => {
    button.addEventListener("click", closeRestoreModal);
});
