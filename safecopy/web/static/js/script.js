document.addEventListener("DOMContentLoaded", function () {
  // Attempt to get page elements only if they exist
  const sourceInput = document.getElementById("sourcePath");
  const destinationInput = document.getElementById("destPath");
  const addMappingBtn = document.getElementById("add-mapping");
  const saveMappingsBtn = document.getElementById("save-mappings");
  const runBackupBtn = document.getElementById("run-backup-btn");
  const mappingList = document.getElementById("mappingsList");
  const actionLog = document.getElementById("actionLog");
  const backupProgressModal = document.getElementById("backupProgressModal");
  const progressBar = document.getElementById("progressBar");
  const progressStatus = document.getElementById("progressStatus");
  const maxVersionsInput = document.getElementById("maxVersions");
  const compressionSelect = document.getElementById("compression");
  const folderBrowserModal = document.getElementById("folderBrowserModal");
  const currentPathInput = document.getElementById("currentPath");
  const folderList = document.getElementById("folderList");

  window.mappings = [];
  window.backupSettings = {
    maxVersions: 3,
    compression: "none",
    encrypted: false,
  };
  let currentBrowseType = "";
  let currentPath = "";

  // Modal functions
  function showModal(modalElement) {
    if (typeof modalElement === "string") {
      modalElement = document.getElementById(modalElement);
    }
    if (modalElement) {
      modalElement.style.display = "flex";
    }
  }

  function hideModal(modalElement) {
    if (typeof modalElement === "string") {
      modalElement = document.getElementById(modalElement);
    }
    if (modalElement) {
      modalElement.style.display = "none";
    }
  }

  window.showModal = showModal;
  window.hideModal = hideModal;

  // Only allow rendering if mappingList and backupSettings elements exist
  function loadMappings() {
    fetch("/get_mappings")
      .then((response) => response.json())
      .then((data) => {
        window.mappings = data.data ? data.data.mappings : data.mappings || [];
        if (mappingList) renderMappings();
      })
      .catch((error) => {
        console.error("Error loading mappings:", error);
        if (actionLog)
          addActionLogEntry(
            "Error loading mappings: " + error.message,
            "danger",
          );
      });
  }

  function loadBackupSettings() {
    fetch("/get_backup_settings")
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          const settings = data.data ? data.data.settings : data.settings;
          window.backupSettings = settings || window.backupSettings;

          // Update UI if present
          if (maxVersionsInput)
            maxVersionsInput.value = window.backupSettings.maxVersions || 3;
          if (compressionSelect)
            compressionSelect.value =
              window.backupSettings.compression || "none";
          const encryptCheckbox = document.getElementById("encryptBackup");
          if (encryptCheckbox)
            encryptCheckbox.checked = window.backupSettings.encrypted || false;
        }
      })
      .catch((error) => {
        console.error("Error loading backup settings:", error);
        if (actionLog)
          addActionLogEntry(
            "Failed to load backup settings: " + error,
            "danger",
          );
      });
  }

  function renderMappings() {
    if (!mappingList) {
      return;
    }
    mappingList.innerHTML = "";

    if (window.mappings.length === 0) {
      mappingList.innerHTML =
        '<div class="text-center text-muted p-3">No mappings added yet</div>';
      return;
    }

    window.mappings.forEach((mapping, index) => {
      const mappingItem = document.createElement("div");
      mappingItem.className = "mapping-item";

      const mappingInfo = document.createElement("div");
      mappingInfo.className = "mapping-info";
      mappingInfo.innerHTML = `
                <div><strong>Source:</strong> ${mapping.source}</div>
                <div><strong>Destination:</strong> ${mapping.destination}</div>
                <div><strong>Max Versions:</strong> ${mapping.max_versions || window.backupSettings.maxVersions}</div>
                <div><strong>Compression:</strong> ${mapping.compression || window.backupSettings.compression}</div>
                <div><strong>Encrypted:</strong> ${mapping.encrypted ? "Yes" : "No"}</div>
                <div class="text-muted small">ID: ${mapping.uuid}</div>
            `;

      const mappingActions = document.createElement("div");
      mappingActions.className = "mapping-actions";

      const deleteBtn = document.createElement("button");
      deleteBtn.className = "btn btn-sm btn-danger";
      deleteBtn.textContent = "Delete";
      deleteBtn.addEventListener("click", () => deleteMapping(index));

      mappingActions.appendChild(deleteBtn);
      mappingItem.appendChild(mappingInfo);
      mappingItem.appendChild(mappingActions);
      mappingList.appendChild(mappingItem);
    });
  }

  function addMapping() {
    if (
      !sourceInput ||
      !destinationInput ||
      !maxVersionsInput ||
      !compressionSelect
    )
      return;

    const source = sourceInput.value.trim();
    const destination = destinationInput.value.trim();
    const maxVersions = parseInt(maxVersionsInput.value) || 3;
    const compression = compressionSelect.value;
    const encryptCheckbox = document.getElementById("encryptBackup");
    const encrypted = encryptCheckbox ? encryptCheckbox.checked : false;

    if (!source || !destination) {
      showNotification(
        "Please select both source and destination folders",
        "warning",
      );
      return;
    }

    // Check if mapping already exists
    const mappingExists = window.mappings.some(
      (m) => m.source === source && m.destination === destination,
    );

    if (mappingExists) {
      showNotification("This mapping already exists", "warning");
      return;
    }

    window.mappings.push({
      source: source,
      destination: destination,
      max_versions: maxVersions,
      compression: compression,
      encrypted: encrypted,
    });

    renderMappings();
    showNotification(`Added mapping: ${source} → ${destination}`, "success");
  }

  function deleteMapping(index) {
    mapping_uuid = window.mappings[index].uuid;
    fetch("/delete_mapping", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ uuid: mapping_uuid }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification("Mapping deleted successfully", "success");
          window.mappings.splice(index, 1);
          renderMappings();
        } else {
          showNotification(`Error deleting mapping: ${data.error}`, "danger");
        }
      })
      .catch((error) => {
        console.error("Error deleting mapping:", error);
        showNotification(`Failed to delete mapping: ${error}`, "danger");
      });
  }

  function saveMappings() {
    if (!maxVersionsInput || !compressionSelect) return;

    window.backupSettings.maxVersions = parseInt(maxVersionsInput.value) || 3;
    window.backupSettings.compression = compressionSelect.value;
    const encryptCheckbox = document.getElementById("encryptBackup");
    window.backupSettings.encrypted = encryptCheckbox
      ? encryptCheckbox.checked
      : false;

    fetch("/save_backup_settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ settings: window.backupSettings }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data.success) {
          console.error("Error saving backup settings:", data.error);
          showNotification(
            `Error saving backup settings: ${data.error}`,
            "danger",
          );
        }
      })
      .catch((error) => {
        console.error("Error saving backup settings:", error);
        showNotification(`Failed to save backup settings: ${error}`, "danger");
      });

    fetch("/save_mappings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ mappings: window.mappings }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification("Mappings saved successfully", "success");
          loadMappings(); // Reload to get potential new UUIDs from server if any were created
        } else {
          showNotification(`Error saving mappings: ${data.error}`, "danger");
        }
      })
      .catch((error) => {
        console.error("Error saving mappings:", error);
        showNotification("Error saving mappings: " + error.message, "danger");
      });
  }

  function runBackup() {
    console.log("Running backup...");
    console.log(window.mappings);
    console.log(window.backupSettings);
    if (!window.mappings || !window.mappings.length) {
      showNotification(
        "No mappings available. Please add mappings first.",
        "warning",
      );
      return;
    }
    if (!backupProgressModal || !progressBar || !progressStatus) {
      showNotification(
        "Backup UI elements missing. Cannot run backup.",
        "danger",
      );
      return;
    }

    showModal(backupProgressModal);
    progressBar.style.width = "0%";
    progressStatus.textContent = "Preparing backup...";

    fetch("/run_backup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        mappings: window.mappings,
        settings: window.backupSettings,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (data.success) {
          progressBar.style.width = "100%";
          progressBar.classList.remove("progress-bar-danger");
          progressBar.classList.add("progress-bar-success");
          const msg = data.message || "Backup completed successfully!";
          progressStatus.textContent = msg;
          showNotification(msg, "success");

          setTimeout(() => {
            hideModal(backupProgressModal);
          }, 2000);
        } else {
          progressBar.style.width = "100%";
          progressBar.classList.remove("progress-bar-success");
          progressBar.classList.add("progress-bar-danger");
          progressStatus.textContent = `Error: ${data.error}`;
          showNotification(`Backup failed: ${data.error}`, "danger");

          if (data.details && Array.isArray(data.details)) {
            data.details.forEach((detail) => {
              showNotification(detail, "danger");
            });
          }
        }
      })
      .catch((error) => {
        console.error("Error running backup:", error);
        progressBar.style.width = "100%";
        progressBar.classList.remove("progress-bar-success");
        progressBar.classList.add("progress-bar-danger");
        progressStatus.textContent = "Error running backup";
        showNotification(`Backup error: ${error.message}`, "danger");
      });
  }

  function addActionLogEntry(message, type = "info") {
    // Only attempt to log if actionLog exists
    if (!actionLog) {
      return;
    }
    const actionItem = document.createElement("div");
    actionItem.className = `action-item text-${type}`;

    const timestamp = new Date().toLocaleTimeString();
    actionItem.innerHTML = `<span class="text-muted">[${timestamp}]</span> ${message}`;

    if (actionLog.firstChild) {
      actionLog.insertBefore(actionItem, actionLog.firstChild);
    } else {
      actionLog.appendChild(actionItem);
    }

    if (actionLog.children.length > 50) {
      actionLog.removeChild(actionLog.lastChild);
    }
  }

  function browseFolder(type) {
    if (!folderBrowserModal || !currentPathInput || !folderList) return;

    currentBrowseType = type;
    currentPath = "/";
    loadFolders();
    showModal(folderBrowserModal);
  }

  function loadFolders() {
    if (!folderBrowserModal || !currentPathInput || !folderList) return;

    fetch(`/browse_folders?path=${encodeURIComponent(currentPath)}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (!data.success) {
          addActionLogEntry(`Error browsing folders: ${data.error}`, "danger");
          return;
        }

        const resData = data.data || {};
        currentPathInput.value = currentPath || "/";
        folderList.innerHTML = "";

        if (currentPath === "/" || currentPath === "") {
          if (resData.drives && resData.drives.length > 0) {
            resData.drives.forEach((drive) => {
              const driveItem = document.createElement("div");
              driveItem.className = "folder-item";
              driveItem.textContent = drive;
              driveItem.addEventListener("click", function () {
                currentPath = drive;
                loadFolders();
              });
              folderList.appendChild(driveItem);
            });
          }
        } else {
          const parentItem = document.createElement("div");
          parentItem.className = "folder-item";
          parentItem.textContent = "..";
          parentItem.addEventListener("click", navigateUp);
          folderList.appendChild(parentItem);

          if (resData.folders && resData.folders.length > 0) {
            resData.folders.forEach((folder) => {
              const folderItem = document.createElement("div");
              folderItem.className = "folder-item";
              folderItem.textContent = folder;
              folderItem.addEventListener("click", function () {
                currentPath = currentPath + "/" + folder;
                loadFolders();
              });
              folderList.appendChild(folderItem);
            });
          } else {
            const noFoldersItem = document.createElement("div");
            noFoldersItem.className = "folder-item";
            noFoldersItem.textContent = "No folders found";
            folderList.appendChild(noFoldersItem);
          }
        }
      })
      .catch((error) => {
        console.error("Error loading folders:", error);
        addActionLogEntry("Error loading folders: " + error.message, "danger");
      });
  }

  function navigateUp() {
    if (currentPath === "") {
      return;
    }

    const parts = currentPath.split("/");
    parts.pop();
    currentPath = parts.join("/");
    loadFolders();
  }

  function selectFolder() {
    if (!sourceInput || !destinationInput || !folderBrowserModal) return;

    if (currentBrowseType === "source") {
      sourceInput.value = currentPath;
    } else if (currentBrowseType === "dest") {
      destinationInput.value = currentPath;
    }
    hideModal(folderBrowserModal);
  }

  // Conditionally load UI elements only if they exist
  if (mappingList) loadMappings();
  if (maxVersionsInput && compressionSelect) loadBackupSettings();

  // Add initial action log entry if actionLog present
  if (actionLog) showNotification("Application started", "info");

  window.browseFolder = browseFolder;
  window.addMapping = addMapping;
  window.saveMappings = saveMappings;
  window.runBackup = runBackup;
  window.navigateUp = navigateUp;
  window.selectFolder = selectFolder;
  window.showModal = showModal;
  window.hideModal = hideModal;

  // Make mappings and settings accessible to other scripts
  window.SafeCopyState = {
    get mappings() {
      return window.mappings;
    },
    set mappings(v) {
      window.mappings = v;
    },
    get settings() {
      return window.backupSettings;
    },
    set settings(v) {
      window.backupSettings = v;
    },
  };

  // Add event listeners for close buttons
  // (must wait for DOMContentLoaded so all modals are in DOM)
  setTimeout(function () {
    const closeButtons = document.querySelectorAll(".close-btn");
    closeButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const modal = this.closest(".modal");
        if (modal) {
          hideModal(modal);
        }
      });
    });
  }, 0);
});
