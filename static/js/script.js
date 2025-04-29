document.addEventListener('DOMContentLoaded', function () {
    const sourceInput = document.getElementById('source-input');
    const destinationInput = document.getElementById('destination-input');
    const addMappingBtn = document.getElementById('add-mapping');
    const saveMappingsBtn = document.getElementById('save-mappings');
    const runBackupBtn = document.getElementById('run-backup-btn');
    const mappingList = document.getElementById('mapping-list');
    const actionLog = document.getElementById('action-log');
    const backupProgressModal = new bootstrap.Modal(document.getElementById('backup-progress-modal'));
    const backupProgressBar = document.getElementById('backup-progress-bar');
    const backupStatus = document.getElementById('backup-status');

    let mappings = [];

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
    addMappingBtn.addEventListener('click', function () {
        const source = sourceInput.value.trim();
        const destination = destinationInput.value.trim();

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
            destination: destination
        });

        renderMappings();
        addActionLogEntry(`Added mapping: ${source} → ${destination}`, 'success');
    });

    // Save mappings to server
    saveMappingsBtn.addEventListener('click', function () {
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
    });

    // Run backup
    runBackupBtn.addEventListener('click', function () {
        if (mappings.length === 0) {
            addActionLogEntry('No mappings available. Please add mappings first.', 'warning');
            return;
        }

        // Show backup progress modal
        backupProgressModal.show();
        backupProgressBar.style.width = '0%';
        backupStatus.textContent = 'Preparing backup...';

        // Start backup process
        fetch('/run_backup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mappings: mappings })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    backupProgressBar.style.width = '100%';
                    backupProgressBar.classList.remove('progress-bar-danger');
                    backupProgressBar.classList.add('progress-bar-success');
                    backupStatus.textContent = data.message || 'Backup completed successfully!';
                    addActionLogEntry(data.message || 'Backup completed successfully', 'success');

                    // Close modal after a delay
                    setTimeout(() => {
                        backupProgressModal.hide();
                    }, 2000);
                } else {
                    backupProgressBar.style.width = '100%';
                    backupProgressBar.classList.remove('progress-bar-success');
                    backupProgressBar.classList.add('progress-bar-danger');
                    backupStatus.textContent = `Error: ${data.error}`;
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
                backupProgressBar.style.width = '100%';
                backupProgressBar.classList.remove('progress-bar-success');
                backupProgressBar.classList.add('progress-bar-danger');
                backupStatus.textContent = 'Error running backup';
                addActionLogEntry('Error running backup: ' + error.message, 'danger');
            });
    });

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

    // Load mappings when page loads
    loadMappings();

    // Add initial action log entry
    addActionLogEntry('Application started', 'info');
}); 