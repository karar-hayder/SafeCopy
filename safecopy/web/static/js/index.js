// index.js - Dashboard specific logic

function loadMappingsSummary() {
  fetch("/get_mappings")
    .then((response) => response.json())
    .then((data) => {
      const summaryDiv = document.getElementById("mappingsSummary");
      if (!summaryDiv) return;
      const resData = data.data || {};
      window.mappings = resData.mappings || [];
      const mappings = window.mappings;
      if (mappings.length > 0) {
        const enabledCount = mappings.filter((m) => m.enabled !== false).length;
        summaryDiv.innerHTML = `
                <div class="summary-stat"><strong>${mappings.length}</strong> total mapping(s)</div>
                <div class="summary-stat"><strong>${enabledCount}</strong> enabled</div>
            `;
      } else {
        summaryDiv.innerHTML =
          '<p style="color: #666;">No mappings configured</p>';
      }
    })
    .catch((error) => {
      console.error("Error loading mappings summary:", error);
      const summaryDiv = document.getElementById("mappingsSummary");
      if (summaryDiv)
        summaryDiv.innerHTML =
          '<p style="color: #e74c3c;">Error loading mappings</p>';
    });
}

function loadBackupHistory() {
  fetch("/get_backup_history?limit=10")
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        const logDiv = document.getElementById("recentBackups");
        if (!logDiv) return;
        const resData = data.data || {};
        const history = resData.history || [];
        if (history.length > 0) {
          logDiv.innerHTML = "";
          history.forEach((entry) => {
            const div = document.createElement("div");
            div.className = "log-entry";
            div.style.padding = "8px";
            div.style.borderBottom = "1px solid #eee";
            div.innerHTML = `
                        <strong>${new Date(entry.timestamp).toLocaleString()}</strong>
                        <span style="color: ${entry.success ? "green" : "red"}; margin-left: 10px;">
                            ${entry.success ? "✓" : "✗"}
                        </span>
                        ${entry.message}
                        ${entry.duration ? ` (${entry.duration.toFixed(2)}s)` : ""}
                    `;
            logDiv.appendChild(div);
          });
        } else {
          logDiv.innerHTML =
            '<p style="color: #666;">No backup history available</p>';
        }
      }
    })
    .catch((error) => {
      console.error("Error loading history:", error);
      const logDiv = document.getElementById("recentBackups");
      if (logDiv)
        logDiv.innerHTML =
          '<p style="color: #e74c3c;">Error loading history</p>';
    });
}

function checkEmailStatus() {
  fetch("/email_settings")
    .then((response) => response.json())
    .then((data) => {
      const emailStatus = document.getElementById("emailStatus");
      if (!emailStatus) return;
      const resData = data.data || {};
      const settings = resData.settings || {};
      if (data.success && settings.enabled) {
        emailStatus.textContent = "Enabled";
        emailStatus.className = "status-value status-success";
      } else {
        emailStatus.textContent = "Disabled";
        emailStatus.className = "status-value status-warning";
      }
    })
    .catch(() => {
      const emailStatus = document.getElementById("emailStatus");
      if (emailStatus) emailStatus.textContent = "Unknown";
    });
}

window.addEventListener("DOMContentLoaded", function () {
  loadMappingsSummary();
  loadBackupHistory();
  checkEmailStatus();
  setInterval(loadBackupHistory, 30000);
});

// Use global runBackup from script.js, but we need to override it if we want custom dashboard behavior
// Actually, runBackup in script.js is generic enough.
