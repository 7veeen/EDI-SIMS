async function downloadBackup(backupId) {
    showLoading("Preparing backup download...");
    hideError();
    try {
        const response = await apiFetch(`/api/backups/${backupId}/download`, { method: "GET" });
        if (!response.ok) {
            let data = {};
            try { data = await response.json(); } catch (_error) { /* response may not be JSON */ }
            throw new ApiError(messageForStatus(response.status, data.error || data.message), response.status);
        }

        const blob = await response.blob();
        const disposition = response.headers.get("Content-Disposition") || "";
        const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
        const filename = match ? decodeURIComponent(match[1] || match[2]) : `backup_${backupId}.json`;
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        showSuccess("Backup downloaded successfully.");
    } catch (error) {
        showError(error.message || "Unable to download the backup.");
    } finally {
        hideLoading();
    }
}
