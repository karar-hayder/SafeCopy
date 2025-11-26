// SafeCopy Dashboard frontend logic for index.html

// Function to load mapping summary (for "Backup Mappings" dashboard card)
function loadMappingsSummary() {
    fetch('/get_mappings')
        .then(response => response.json())
        .then(data => {
            const summaryDiv = document.getElementById('mappingsSummary');
            if (data.mappings && data.mappings.length > 0) {
                const enabledCount = data.mappings.filter(m => m.enabled !== false).length;
                summaryDiv.innerHTML = `
                    <div class="summary-stat">
                        <strong>${data.mappings.length}</strong> total mapping(s)
                    </div>
                    <div class="summary-stat">
                        <strong>${enabledCount}</strong> enabled
                    </div>
                `;
            } else {
                summaryDiv.innerHTML = '<p style="color: #666;">No mappings configured</p>';
            }
        })
        .catch(error => {
            document.getElementById('mappingsSummary').innerHTML = '<p style="color: #e74c3c;">Error loading mappings</p>';
        });
}

// Function to load recent backup history (for "Recent Backups" dashboard card)
function loadBackupHistory() {
    fetch('/get_backup_history?limit=10')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const logDiv = document.getElementById('recentBackups');
                if (data.history && data.history.length > 0) {
                    logDiv.innerHTML = '';
                    data.history.forEach(entry => {
                        const div = document.createElement('div');
                        div.className = 'log-entry';
                        div.style.padding = '8px';
                        div.style.borderBottom = '1px solid #eee';
                        div.innerHTML = `
                            <strong>${new Date(entry.timestamp).toLocaleString()}</strong>
                            <span style="color: ${entry.success ? 'green' : 'red'}; margin-left: 10px;">
                                ${entry.success ? '✓' : '✗'}
                            </span>
                            ${entry.message}
                            ${entry.duration ? ` (${entry.duration.toFixed(2)}s)` : ''}
                        `;
                        logDiv.appendChild(div);
                    });
                } else {
                    logDiv.innerHTML = '<p style="color: #666;">No backup history available</p>';
                }
            }
        })
        .catch(error => {
            document.getElementById('recentBackups').innerHTML = '<p style="color: #e74c3c;">Error loading history</p>';
        });
}

// Function to check email notification status (for "System Status" card)
function checkEmailStatus() {
    fetch('/email_settings')
        .then(response => response.json())
        .then(data => {
            const emailStatus = document.getElementById('emailStatus');
            if (data.success && data.settings && data.settings.enabled) {
                emailStatus.textContent = 'Enabled';
                emailStatus.className = 'status-value status-success';
            } else {
                emailStatus.textContent = 'Disabled';
                emailStatus.className = 'status-value status-warning';
            }
        })
        .catch(() => {
            document.getElementById('emailStatus').textContent = 'Unknown';
        });
}

// Show/hide header actions if authentication required
function checkAuthStatus() {
    const headerActions = document.getElementById('headerActions');
    if (headerActions) {
        fetch('/get_mappings')
            .then(response => {
                if (response.ok || response.status !== 401) {
                    headerActions.style.display = 'flex';
                }
            })
            .catch(() => {
                headerActions.style.display = 'none';
            });
    }
}

// Utility to show or hide modal dialogs (i.e. backup progress)
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'block';
}

// Trigger all initial loads and auto-refresh for recent backups
window.addEventListener('DOMContentLoaded', function () {
    checkAuthStatus();
    loadMappingsSummary();
    loadBackupHistory();
    checkEmailStatus();
    setInterval(loadBackupHistory, 30000);
});

// Allow "Run Backup Now" button to start backup via API and show modal/progress
function runBackup() {
    showModal('backupProgressModal');
    const progressStatus = document.getElementById('progressStatus');
    const progressBar = document.getElementById('progressBar');
    progressStatus.textContent = 'Starting backup...';
    progressBar.style.width = '10%';

    // Fetch mappings, filter for enabled
    fetch('/get_mappings')
        .then(response => response.json())
        .then(data => {
            const mappings = (data.mappings || []).filter(m => m.enabled !== false);
            if (mappings.length === 0) {
                progressStatus.textContent = 'No enabled mappings to back up.';
                progressBar.style.width = '100%';
                setTimeout(() => hideModal('backupProgressModal'), 2000);
                return;
            }
            // Start backup via POST
            progressStatus.textContent = 'Running backup...';
            progressBar.style.width = '30%';
            return fetch('/run_backup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ mappings: mappings })
            })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        progressStatus.textContent = result.message || 'Backup completed successfully!';
                        progressBar.style.width = '100%';
                    } else {
                        progressStatus.textContent = result.error || 'Backup failed.';
                        progressBar.style.width = '100%';
                    }
                    // After short delay, hide modal and refresh history
                    setTimeout(() => {
                        hideModal('backupProgressModal');
                        loadBackupHistory();
                    }, 2000);
                })
                .catch(() => {
                    progressStatus.textContent = 'Backup failed due to network error.';
                    progressBar.style.width = '100%';
                    setTimeout(() => hideModal('backupProgressModal'), 2000);
                });
        })
        .catch(() => {
            progressStatus.textContent = 'Unable to load mappings or start backup.';
            progressBar.style.width = '100%';
            setTimeout(() => hideModal('backupProgressModal'), 2000);
        });
}
