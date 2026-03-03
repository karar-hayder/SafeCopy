// settings.js - Logic for settings.html

// Utility: Safe getElementById
function $(id) {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`Element with id '${id}' not found.`);
  }
  return el;
}

// Email settings functions
function toggleEmailSettings() {
  const enabledEl = $("emailEnabled");
  const settingsEl = $("emailSettings");
  if (enabledEl && settingsEl) {
    settingsEl.style.display = enabledEl.checked ? "block" : "none";
  }
}

function saveEmailSettings() {
  const smtpServer = $("smtpServer") ? $("smtpServer").value : "";
  const smtpPort = $("smtpPort") ? parseInt($("smtpPort").value) : 0;
  const smtpUsername = $("smtpUsername") ? $("smtpUsername").value : "";
  const smtpPassword = $("smtpPassword") ? $("smtpPassword").value : "";
  const fromEmail = $("fromEmail") ? $("fromEmail").value : "";
  const toEmail = $("toEmail") ? $("toEmail").value : "";
  const useTLS = $("useTLS") ? $("useTLS").checked : false;
  const enabled = $("emailEnabled") ? $("emailEnabled").checked : false;

  const settings = {
    smtp_server: smtpServer,
    smtp_port: smtpPort,
    smtp_username: smtpUsername,
    smtp_password: smtpPassword,
    from_email: fromEmail,
    to_email: toEmail,
    use_tls: useTLS,
    enabled: enabled,
  };

  fetch("/email_settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Email settings saved successfully!", "success");
      } else {
        showNotification(
          "Error saving email settings: " +
            (data.error || "Unknown server error"),
          "danger",
        );
      }
    })
    .catch((error) => {
      showNotification(
        "Network error saving email settings: " + error,
        "danger",
      );
    });
}

function loadEmailSettings() {
  fetch("/email_settings")
    .then((response) => response.json())
    .then((data) => {
      const resData = data.data || {};
      if (data.success && resData.settings) {
        const s = resData.settings;
        if ($("emailEnabled")) $("emailEnabled").checked = s.enabled || false;
        if ($("smtpServer")) $("smtpServer").value = s.smtp_server || "";
        if ($("smtpPort")) $("smtpPort").value = s.smtp_port || 587;
        if ($("smtpUsername")) $("smtpUsername").value = s.smtp_username || "";
        if ($("fromEmail")) $("fromEmail").value = s.from_email || "";
        if ($("toEmail")) $("toEmail").value = s.to_email || "";
        if ($("useTLS")) $("useTLS").checked = s.use_tls !== false;
        toggleEmailSettings();
      }
    });
}

// Schedule management functions
function showAddScheduleModal() {
  fetch("/get_mappings")
    .then((response) => response.json())
    .then((data) => {
      const select = $("scheduleMapping");
      if (!select) return;
      select.innerHTML = "";
      const resData = data.data || {};
      if (!resData.mappings || resData.mappings.length === 0) {
        showNotification(
          "No mappings available. Please create a mapping first.",
          "warning",
        );
        return;
      }
      const validMappings = resData.mappings.filter(
        (m) => m.uuid !== undefined && m.uuid !== null && m.uuid !== "",
      );
      if (validMappings.length === 0) {
        showNotification(
          "No valid mappings found. Please save your mappings first.",
          "warning",
        );
        return;
      }
      validMappings.forEach((m) => {
        const option = document.createElement("option");
        option.value = m.uuid;
        option.textContent = m.source + " -> " + m.destination;
        select.appendChild(option);
      });

      if ($("scheduleType")) $("scheduleType").value = "daily";
      if ($("scheduleValue")) $("scheduleValue").value = "";
      updateScheduleInput();

      const modal = $("addScheduleModal");
      if (modal) {
        showModal(modal);
      }
    })
    .catch((error) => {
      console.error("Error loading mappings for schedules:", error);
      showNotification("Error loading mappings: " + error.message, "danger");
    });
}

function updateScheduleInput() {
  const type = $("scheduleType") ? $("scheduleType").value : "";
  const label = $("scheduleValueLabel");
  const input = $("scheduleValue");
  const help = $("scheduleHelp");
  if (!label || !input || !help) return;
  const configs = {
    daily: {
      label: "Time (HH:MM):",
      placeholder: "14:30",
      help: "Enter time in 24-hour format (e.g., 14:30)",
    },
    weekly: {
      label: "Day and Time (day HH:MM):",
      placeholder: "monday 09:00",
      help: "Enter day name and time (e.g., monday 09:00)",
    },
    monthly: {
      label: "Day and Time (DD HH:MM):",
      placeholder: "1 00:00",
      help: "Enter day of month and time (e.g., 1 00:00 for 1st at midnight)",
    },
    interval: {
      label: "Interval (minutes):",
      placeholder: "60",
      help: "Enter number of minutes between backups",
    },
    minutes: {
      label: "Interval (minutes):",
      placeholder: "60",
      help: "Enter number of minutes between backups",
    },
    hourly: {
      label: "Hourly Offset (MM):",
      placeholder: "00",
      help: "Enter minute offset for hourly backup (e.g., 00 for top of the hour)",
    },
  };

  const config = configs[type] || configs.daily;
  label.textContent = config.label;
  input.placeholder = config.placeholder;
  help.textContent = config.help;

  // Toggle input visibility for hourly if needed, or keep it for offset
  input.style.display = "block";
}

function saveSchedule() {
  const mappingId = $("scheduleMapping") ? $("scheduleMapping").value : "";
  const scheduleType = $("scheduleType") ? $("scheduleType").value : "";
  const scheduleValue = $("scheduleValue")
    ? $("scheduleValue").value.trim()
    : "";

  if (!mappingId || !scheduleValue) {
    showNotification("Please fill in all fields", "warning");
    return;
  }
  // Validate schedule value format
  const validators = {
    daily: (v) => /^\d{1,2}:\d{2}$/.test(v),
    weekly: (v) =>
      /^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+\d{1,2}:\d{2}$/i.test(
        v,
      ),
    monthly: (v) => /^\d{1,2}\s+\d{1,2}:\d{2}$/.test(v),
    interval: (v) => !isNaN(parseInt(v)) && parseInt(v) > 0,
    minutes: (v) => !isNaN(parseInt(v)) && parseInt(v) > 0,
    hourly: (v) => !isNaN(parseInt(v)) && parseInt(v) >= 0 && parseInt(v) < 60,
  };

  if (validators[scheduleType] && !validators[scheduleType](scheduleValue)) {
    const errors = {
      daily: "Invalid time format. Please use HH:MM (e.g., 14:30)",
      weekly: "Invalid format. Please use: day HH:MM (e.g., monday 09:00)",
      monthly: "Invalid format. Please use: DD HH:MM (e.g., 1 00:00)",
      interval: "Invalid interval. Please enter a positive number of minutes",
      minutes: "Invalid interval. Please enter a positive number of minutes",
      hourly: "Invalid offset. Please enter minutes (0-59)",
    };
    showNotification(errors[scheduleType] || "Invalid format", "warning");
    return;
  }

  fetch("/add_schedule", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mapping_uuid: mappingId,
      schedule_type: scheduleType,
      schedule_value: scheduleValue,
      enabled: true,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Schedule added successfully!", "success");
        const modal = $("addScheduleModal");
        if (modal) {
          hideModal(modal);
        }
        loadSchedules();
      } else {
        showNotification(
          "Error adding schedule: " + (data.error || "Unknown server error"),
          "danger",
        );
      }
    })
    .catch((error) => {
      showNotification("Network error adding schedule: " + error, "danger");
    });
}

function loadSchedules() {
  console.log("Loading schedules...");
  fetch("/get_mappings")
    .then((response) => response.json())
    .then((data) => {
      const schedulesList = $("schedulesList");
      if (!schedulesList) return;
      schedulesList.innerHTML = "";
      const resData = data.data || {};
      if (!resData.mappings || resData.mappings.length === 0) {
        schedulesList.innerHTML =
          '<p style="color: #666; padding: 10px;">No mappings available. Create a mapping first.</p>';
        return;
      }
      const promises = resData.mappings
        .filter((mapping) => mapping.uuid)
        .map((mapping) => {
          return fetch(`/get_schedules?mapping_uuid=${mapping.uuid}`)
            .then((response) => response.json())
            .then((scheduleData) => {
              const sData = scheduleData.data || {};
              if (scheduleData.success && sData.schedules) {
                return { mapping: mapping, schedules: sData.schedules };
              }
              return { mapping: mapping, schedules: [] };
            })
            .catch((error) => {
              console.error(
                "Error fetching schedules for mapping",
                mapping.uuid,
                error,
              );
              return { mapping: mapping, schedules: [] };
            });
        });

      Promise.all(promises)
        .then((results) => {
          let hasSchedules = false;
          results.forEach((result) => {
            if (result.schedules && result.schedules.length > 0) {
              hasSchedules = true;
              result.schedules.forEach((schedule) => {
                const div = document.createElement("div");
                div.className = "schedule-item";
                div.style.padding = "10px";
                div.style.borderBottom = "1px solid #eee";
                div.style.display = "flex";
                div.style.justifyContent = "space-between";
                div.style.alignItems = "center";

                const scheduleTypeLabels = {
                  daily: "Daily",
                  weekly: "Weekly",
                  monthly: "Monthly",
                  interval: "Interval",
                  minutes: "Minutes",
                  hourly: "Hourly",
                };

                div.innerHTML = `
                            <div class="schedule-info">
                                <strong>${result.mapping.source} → ${result.mapping.destination}</strong><br>
                                <span style="color: #666; font-size: 0.9rem;">
                                    ${scheduleTypeLabels[schedule.schedule_type] || schedule.schedule_type}: ${schedule.schedule_value}
                                </span>
                            </div>
                            <button class="btn btn-sm btn-danger" onclick="deleteSchedule('${schedule.uuid}')">Delete</button>
                        `;
                schedulesList.appendChild(div);
              });
            }
          });

          if (!hasSchedules) {
            schedulesList.innerHTML =
              '<p style="color: #666; padding: 10px;">No schedules configured. Click "Add Schedule" to create one.</p>';
          }
        })
        .catch((err) => {
          console.error("Error loading schedules:", err);
          if ($("schedulesList"))
            $("schedulesList").innerHTML =
              '<p style="color: #e74c3c; padding: 10px;">Error loading schedules</p>';
        });
    })
    .catch((err) => {
      console.error("Error loading mappings for schedules:", err);
      if ($("schedulesList"))
        $("schedulesList").innerHTML =
          '<p style="color: #e74c3c; padding: 10px;">Error loading mappings</p>';
    });
}

function deleteSchedule(scheduleId) {
  if (!confirm("Are you sure you want to delete this schedule?")) {
    return;
  }

  fetch(`/delete_schedule/${scheduleId}`, { method: "DELETE" })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Schedule deleted successfully!", "success");
        loadSchedules();
      } else {
        showNotification(
          "Error deleting schedule: " + (data.error || "Unknown server error"),
          "danger",
        );
      }
    })
    .catch((error) => {
      showNotification("Network error deleting schedule: " + error, "danger");
    });
}

function loadBackupHistory() {
  fetch("/get_backup_history?limit=50")
    .then((response) => response.json())
    .then((data) => {
      const logDiv = $("actionLog");
      if (!logDiv) return;
      logDiv.innerHTML = "";
      const resData = data.data || {};
      if (data.success && resData.history && Array.isArray(resData.history)) {
        resData.history.forEach((entry) => {
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
                    ${entry.size_bytes ? ` (${(entry.size_bytes / 1024 / 1024).toFixed(2)} MB)` : ""}
                `;
          logDiv.appendChild(div);
        });
      }
    });
}

// Load email settings and history on page load
window.addEventListener("DOMContentLoaded", function () {
  loadEmailSettings();
  loadBackupHistory();
  loadSchedules();
  setInterval(loadBackupHistory, 30000);
});

// Export to window
window.toggleEmailSettings = toggleEmailSettings;
window.saveEmailSettings = saveEmailSettings;
window.showAddScheduleModal = showAddScheduleModal;
window.updateScheduleInput = updateScheduleInput;
window.saveSchedule = saveSchedule;
window.deleteSchedule = deleteSchedule;
window.loadBackupHistory = loadBackupHistory;
