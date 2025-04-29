document.addEventListener('DOMContentLoaded', function () {
    const folderBrowser = document.getElementById('folder-browser');
    const folderList = document.getElementById('folder-list');
    const currentPathInput = document.getElementById('current-path');
    const browseBtn = document.getElementById('browse-btn');
    const browseDestBtn = document.getElementById('browse-dest-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const selectBtn = document.getElementById('select-btn');
    const upBtn = document.getElementById('up-btn');
    const sourceInput = document.getElementById('source-input');
    const destinationInput = document.getElementById('destination-input');
    const folderPreview = document.getElementById('folder-preview');
    const folderPreviewContent = document.getElementById('folder-preview-content');
    const refreshPreviewBtn = document.getElementById('refresh-preview');
    const destinationPreview = document.getElementById('destination-preview');
    const destinationPreviewContent = document.getElementById('destination-preview-content');
    const refreshDestPreviewBtn = document.getElementById('refresh-dest-preview');

    let currentPath = '';
    let selectedFolder = '';
    let currentBrowserMode = 'source'; // 'source' or 'destination'

    // Open folder browser for source
    browseBtn.addEventListener('click', function () {
        currentBrowserMode = 'source';
        folderBrowser.style.display = 'block';
        fetchFolders('/');
    });

    // Open folder browser for destination
    browseDestBtn.addEventListener('click', function () {
        currentBrowserMode = 'destination';
        folderBrowser.style.display = 'block';
        fetchFolders('/');
    });

    // Close folder browser
    cancelBtn.addEventListener('click', function () {
        folderBrowser.style.display = 'none';
    });

    // Select folder
    selectBtn.addEventListener('click', function () {
        if (selectedFolder) {
            if (currentBrowserMode === 'source') {
                sourceInput.value = selectedFolder;
                loadFolderPreview(selectedFolder, folderPreview, folderPreviewContent);
            } else {
                destinationInput.value = selectedFolder;
                loadFolderPreview(selectedFolder, destinationPreview, destinationPreviewContent);
            }
            folderBrowser.style.display = 'none';
        }
    });

    // Refresh source folder preview
    refreshPreviewBtn.addEventListener('click', function () {
        if (sourceInput.value) {
            loadFolderPreview(sourceInput.value, folderPreview, folderPreviewContent);
        }
    });

    // Refresh destination folder preview
    refreshDestPreviewBtn.addEventListener('click', function () {
        if (destinationInput.value) {
            loadFolderPreview(destinationInput.value, destinationPreview, destinationPreviewContent);
        }
    });

    // Navigate up
    upBtn.addEventListener('click', function () {
        if (currentPath && currentPath !== '/') {
            const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
            fetchFolders(parentPath);
        }
    });

    // Load folder preview
    function loadFolderPreview(path, previewElement, previewContentElement) {
        previewElement.style.display = 'block';
        previewContentElement.innerHTML = '<div class="text-center text-muted">Loading...</div>';

        fetch(`/folder_preview?path=${encodeURIComponent(path)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    previewContentElement.innerHTML = `<div class="text-center text-danger">${data.error}</div>`;
                    return;
                }

                let html = '';

                if (data.files && data.files.length > 0) {
                    html += '<div class="mb-2"><strong>Files:</strong></div>';
                    data.files.slice(0, 5).forEach(file => {
                        html += `<div class="folder-preview-item">${file}</div>`;
                    });

                    if (data.files.length > 5) {
                        html += `<div class="folder-preview-item text-muted">... and ${data.files.length - 5} more files</div>`;
                    }
                }

                if (data.folders && data.folders.length > 0) {
                    html += '<div class="mb-2 mt-2"><strong>Folders:</strong></div>';
                    data.folders.slice(0, 5).forEach(folder => {
                        html += `<div class="folder-preview-item">${folder}</div>`;
                    });

                    if (data.folders.length > 5) {
                        html += `<div class="folder-preview-item text-muted">... and ${data.folders.length - 5} more folders</div>`;
                    }
                }

                if (data.size) {
                    html += `<div class="mt-2 text-muted">Total size: ${data.size}</div>`;
                }

                if (!html) {
                    html = '<div class="text-center text-muted">Empty folder</div>';
                }

                previewContentElement.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading folder preview:', error);
                previewContentElement.innerHTML = '<div class="text-center text-danger">Error loading folder preview</div>';
            });
    }

    // Fetch folders from server
    function fetchFolders(path) {
        currentPath = path;
        currentPathInput.value = path;

        fetch(`/browse_folders?path=${encodeURIComponent(path)}`)
            .then(response => response.json())
            .then(data => {
                folderList.innerHTML = '';

                // Add drives
                if (path === '/') {
                    data.drives.forEach(drive => {
                        const driveItem = document.createElement('div');
                        driveItem.className = 'folder-item';
                        driveItem.textContent = drive;
                        driveItem.dataset.path = drive;
                        driveItem.addEventListener('click', function () {
                            fetchFolders(drive);
                        });
                        folderList.appendChild(driveItem);
                    });
                } else {
                    // Add parent directory
                    const parentItem = document.createElement('div');
                    parentItem.className = 'folder-item';
                    parentItem.textContent = '..';
                    parentItem.addEventListener('click', function () {
                        const parentPath = path.split('/').slice(0, -1).join('/') || '/';
                        fetchFolders(parentPath);
                    });
                    folderList.appendChild(parentItem);

                    // Add folders
                    data.folders.forEach(folder => {
                        const folderItem = document.createElement('div');
                        folderItem.className = 'folder-item';
                        folderItem.textContent = folder;
                        folderItem.dataset.path = `${path}/${folder}`;
                        folderItem.addEventListener('click', function () {
                            fetchFolders(`${path}/${folder}`);
                        });
                        folderList.appendChild(folderItem);
                    });

                    // Add select button for current folder
                    const selectItem = document.createElement('div');
                    selectItem.className = 'folder-item selected';
                    selectItem.textContent = 'Select this folder';
                    selectItem.addEventListener('click', function () {
                        selectedFolder = path;
                        selectBtn.disabled = false;
                    });
                    folderList.appendChild(selectItem);
                }
            })
            .catch(error => {
                console.error('Error fetching folders:', error);
                folderList.innerHTML = '<div class="p-3 text-center text-danger">Error loading folders</div>';
            });
    }
}); 