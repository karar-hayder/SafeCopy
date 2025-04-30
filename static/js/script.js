document.addEventListener('DOMContentLoaded', function () {
    const sourceInput = document.getElementById('sourcePath');
    const destinationInput = document.getElementById('destPath');
    const addMappingBtn = document.getElementById('add-mapping');
    const saveMappingsBtn = document.getElementById('save-mappings');
    const runBackupBtn = document.getElementById('run-backup-btn');
    const mappingList = document.getElementById('mappingsList');
    const actionLog = document.getElementById('actionLog');
    const backupProgressModal = document.getElementById('backupProgressModal');
    const progressBar = document.getElementById('progressBar');
    const progressStatus = document.getElementById('progressStatus');
    const maxVersionsInput = document.getElementById('maxVersions');
    const compressionSelect = document.getElementById('compression');
    const folderBrowserModal = document.getElementById('folderBrowserModal');
    const currentPathInput = document.getElementById('currentPath');
    const folderList = document.getElementById('folderList');

    let mappings = [];
    let backupSettings = {
        maxVersions: 3,
        compression: 'none'
    };
    let currentBrowseType = '';
    let currentPath = '';

    // Modal functions
    function showModal(modalElement) {
        modalElement.style.display = 'flex';
    }

    function hideModal(modalElement) {
        if (typeof modalElement === 'string') {
            // If a string ID is passed, get the element
            modalElement = document.getElementById(modalElement);
        }
        if (modalElement) {
            modalElement.style.display = 'none';
        }
    }

    // Load existing mappings from server
    function loadMappings() {
        fetch('/get_mappings')
            .then(response => response.json())
            .then(data => {
                mappings = data.mappings || [];
                renderMappings();
            })
            .catch(error => {
                console.error('Error loading mappings:', error);
                addActionLogEntry('Error loading mappings', 'danger');
            });
    }

    // Load backup settings from server
    function loadBackupSettings() {
        fetch('/get_backup_settings')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    backupSettings = data.settings || backupSettings;
                    maxVersionsInput.value = backupSettings.maxVersions;
                    compressionSelect.value = backupSettings.compression;
                }
            })
            .catch(error => {
                console.error('Error loading backup settings:', error);
            });
    }

    // Render mappings in the UI
    function renderMappings() {
        mappingList.innerHTML = '';

        if (mappings.length === 0) {
            mappingList.innerHTML = '<div class="text-center text-muted p-3">No mappings added yet</div>';
            return;
        }

        mappings.forEach((mapping, index) => {
            const mappingItem = document.createElement('div');
            mappingItem.className = 'mapping-item';

            const mappingInfo = document.createElement('div');
            mappingInfo.className = 'mapping-info';
            mappingInfo.innerHTML = `
                <div><strong>Source:</strong> ${mapping.source}</div>
                <div><strong>Destination:</strong> ${mapping.destination}</div>
                <div><strong>Max Versions:</strong> ${mapping.max_versions || backupSettings.maxVersions}</div>
                <div><strong>Compression:</strong> ${mapping.compression || backupSettings.compression}</div>
            `;

            const mappingActions = document.createElement('div');
            mappingActions.className = 'mapping-actions';

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-sm btn-danger';
            deleteBtn.textContent = 'Delete';
            deleteBtn.addEventListener('click', function () {
                mappings.splice(index, 1);
                renderMappings();
                addActionLogEntry(`Deleted mapping: ${mapping.source} → ${mapping.destination}`, 'info');
            });

            mappingActions.appendChild(deleteBtn);
            mappingItem.appendChild(mappingInfo);
            mappingItem.appendChild(mappingActions);
            mappingList.appendChild(mappingItem);
        });
    }

    // Add a new mapping
    function addMapping() {
        const source = sourceInput.value.trim();
        const destination = destinationInput.value.trim();
        const maxVersions = parseInt(maxVersionsInput.value) || 3;
        const compression = compressionSelect.value;

        if (!source || !destination) {
            addActionLogEntry('Please select both source and destination folders', 'warning');
            return;
        }

        // Check if mapping already exists
        const mappingExists = mappings.some(m =>
            m.source === source && m.destination === destination
        );

        if (mappingExists) {
            addActionLogEntry('This mapping already exists', 'warning');
            return;
        }

        mappings.push({
            source: source,
            destination: destination,
            max_versions: maxVersions,
            compression: compression
        });

        renderMappings();
        addActionLogEntry(`Added mapping: ${source} → ${destination}`, 'success');
    }

    // Save mappings to server
    function saveMappings() {
        // Update backup settings
        backupSettings.maxVersions = parseInt(maxVersionsInput.value) || 3;
        backupSettings.compression = compressionSelect.value;

        // Save backup settings
        fetch('/save_backup_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ settings: backupSettings })
        })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Error saving backup settings:', data.error);
                }
            })
            .catch(error => {
                console.error('Error saving backup settings:', error);
            });

        // Save mappings
        fetch('/save_mappings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mappings: mappings })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addActionLogEntry('Mappings saved successfully', 'success');
                } else {
                    addActionLogEntry(`Error saving mappings: ${data.error}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error saving mappings:', error);
                addActionLogEntry('Error saving mappings', 'danger');
            });
    }

    // Run backup
    function runBackup() {
        if (mappings.length === 0) {
            addActionLogEntry('No mappings available. Please add mappings first.', 'warning');
            return;
        }

        // Show backup progress modal
        showModal(backupProgressModal);
        progressBar.style.width = '0%';
        progressStatus.textContent = 'Preparing backup...';

        // Start backup process
        fetch('/run_backup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mappings: mappings,
                settings: backupSettings
            })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    progressBar.style.width = '100%';
                    progressBar.classList.remove('progress-bar-danger');
                    progressBar.classList.add('progress-bar-success');
                    progressStatus.textContent = data.message || 'Backup completed successfully!';
                    addActionLogEntry(data.message || 'Backup completed successfully', 'success');

                    // Close modal after a delay
                    setTimeout(() => {
                        hideModal(backupProgressModal);
                    }, 2000);
                } else {
                    progressBar.style.width = '100%';
                    progressBar.classList.remove('progress-bar-success');
                    progressBar.classList.add('progress-bar-danger');
                    progressStatus.textContent = `Error: ${data.error}`;
                    addActionLogEntry(`Backup failed: ${data.error}`, 'danger');

                    // Add detailed error messages if available
                    if (data.details && Array.isArray(data.details)) {
                        data.details.forEach(detail => {
                            addActionLogEntry(detail, 'danger');
                        });
                    }
                }
            })
            .catch(error => {
                console.error('Error running backup:', error);
                progressBar.style.width = '100%';
                progressBar.classList.remove('progress-bar-success');
                progressBar.classList.add('progress-bar-danger');
                progressStatus.textContent = 'Error running backup';
                addActionLogEntry('Error running backup: ' + error.message, 'danger');
            });
    }

    // Add entry to action log
    function addActionLogEntry(message, type = 'info') {
        const actionItem = document.createElement('div');
        actionItem.className = `action-item text-${type}`;

        const timestamp = new Date().toLocaleTimeString();
        actionItem.innerHTML = `<span class="text-muted">[${timestamp}]</span> ${message}`;

        actionLog.insertBefore(actionItem, actionLog.firstChild);

        // Limit the number of log entries
        if (actionLog.children.length > 50) {
            actionLog.removeChild(actionLog.lastChild);
        }
    }

    // Folder browser functions
    function browseFolder(type) {
        currentBrowseType = type;
        currentPath = '/';
        loadFolders();
        showModal(folderBrowserModal);
    }

    function loadFolders() {
        fetch(`/browse_folders?path=${encodeURIComponent(currentPath)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    addActionLogEntry(`Error browsing folders: ${data.error}`, 'danger');
                    return;
                }

                currentPathInput.value = currentPath || '/';
                folderList.innerHTML = '';

                // Add drives if at root
                if (currentPath === '/' || currentPath === '') {
                    if (data.drives && data.drives.length > 0) {
                        data.drives.forEach(drive => {
                            const driveItem = document.createElement('div');
                            driveItem.className = 'folder-item';
                            driveItem.textContent = drive;
                            driveItem.addEventListener('click', function () {
                                currentPath = drive;
                                loadFolders();
                            });
                            folderList.appendChild(driveItem);
                        });
                    }
                } else {
                    // Add parent directory
                    const parentItem = document.createElement('div');
                    parentItem.className = 'folder-item';
                    parentItem.textContent = '..';
                    parentItem.addEventListener('click', navigateUp);
                    folderList.appendChild(parentItem);

                    // Add folders
                    if (data.folders && data.folders.length > 0) {
                        data.folders.forEach(folder => {
                            const folderItem = document.createElement('div');
                            folderItem.className = 'folder-item';
                            folderItem.textContent = folder;
                            folderItem.addEventListener('click', function () {
                                currentPath = currentPath + '/' + folder;
                                loadFolders();
                            });
                            folderList.appendChild(folderItem);
                        });
                    } else {
                        const noFoldersItem = document.createElement('div');
                        noFoldersItem.className = 'folder-item';
                        noFoldersItem.textContent = 'No folders found';
                        folderList.appendChild(noFoldersItem);
                    }
                }
            })
            .catch(error => {
                console.error('Error loading folders:', error);
                addActionLogEntry('Error loading folders: ' + error.message, 'danger');
            });
    }

    function navigateUp() {
        if (currentPath === '') {
            return;
        }

        const parts = currentPath.split('/');
        parts.pop();
        currentPath = parts.join('/');
        loadFolders();
    }

    function selectFolder() {
        if (currentBrowseType === 'source') {
            sourceInput.value = currentPath;
        } else if (currentBrowseType === 'dest') {
            destinationInput.value = currentPath;
        }
        hideModal(folderBrowserModal);
    }

    // Load mappings and settings when page loads
    loadMappings();
    loadBackupSettings();

    // Add initial action log entry
    addActionLogEntry('Application started', 'info');

    // Make functions available globally
    window.browseFolder = browseFolder;
    window.addMapping = addMapping;
    window.saveMappings = saveMappings;
    window.runBackup = runBackup;
    window.navigateUp = navigateUp;
    window.selectFolder = selectFolder;
    window.showModal = showModal;
    window.hideModal = hideModal;

    // Add event listeners for close buttons
    document.addEventListener('DOMContentLoaded', function () {
        // Add event listeners for all close buttons
        const closeButtons = document.querySelectorAll('.close-btn');
        closeButtons.forEach(button => {
            button.addEventListener('click', function () {
                const modal = this.closest('.modal');
                if (modal) {
                    hideModal(modal);
                }
            });
        });
    });
}); 