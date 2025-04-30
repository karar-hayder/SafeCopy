import shutil
import os
import time
import logging
import glob
from datetime import datetime
from safecopy.config import load_config, save_config
from pathlib import Path
import zipfile
import tarfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("safecopy.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def perform_backup(source_path, dest_path, max_versions=3, compression="none"):
    """
    Perform a backup of the source directory to the destination directory.

    Args:
        source_path (str): Path to the source directory
        dest_path (str): Path to the destination directory
        max_versions (int): Maximum number of backup versions to keep
        compression (str): Compression type ('none', 'zip', or 'tar')

    Returns:
        bool: True if backup was successful, False otherwise
    """
    try:
        source_path = Path(source_path)
        dest_path = Path(dest_path)

        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        # Create destination directory if it doesn't exist
        dest_path.mkdir(parents=True, exist_ok=True)

        # Generate backup name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"

        if compression == "zip":
            # Create zip archive
            zip_path = dest_path / f"{backup_name}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(source_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(source_path)
                        zipf.write(file_path, arcname)
            backup_path = zip_path
        elif compression == "tar":
            # Create tar archive
            tar_path = dest_path / f"{backup_name}.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(source_path, arcname=source_path.name)
            backup_path = tar_path
        else:
            # No compression, just copy the directory
            backup_path = dest_path / backup_name
            shutil.copytree(source_path, backup_path)

        # Clean up old backups if exceeding max_versions
        cleanup_old_backups(dest_path, max_versions)

        logger.info(f"Backup completed successfully: {backup_path}")
        return True, f"Backup completed successfully: {backup_path}"

    except Exception as e:
        error_msg = f"Backup failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def cleanup_old_backups(dest_path, max_versions):
    """
    Remove old backup versions if exceeding max_versions.

    Args:
        dest_path (Path): Path to the backup directory
        max_versions (int): Maximum number of backup versions to keep
    """
    try:
        # Get all backup directories and archives
        backups = []
        for item in dest_path.iterdir():
            if item.name.startswith("backup_"):
                backups.append(item)

        # Sort backups by modification time (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Remove excess backups
        for backup in backups[max_versions:]:
            if backup.is_file():
                backup.unlink()
            else:
                shutil.rmtree(backup)
            logger.info(f"Removed old backup: {backup}")

    except Exception as e:
        logger.error(f"Warning: Failed to cleanup old backups: {str(e)}")


def run_backup(mapping):
    """
    Run a backup operation for a specific mapping.

    Args:
        mapping (dict): Mapping configuration containing source and destination paths
    """
    source = mapping.get("source")
    destination = mapping.get("destination")
    max_versions = mapping.get("maxVersions", 3)
    compression = mapping.get("compression", "none")

    if not source or not destination:
        return False, "Invalid mapping configuration"

    success, message = perform_backup(source, destination, max_versions, compression)

    # Update last actions
    config = load_config()
    config["last_actions"].insert(
        0,
        {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "destination": destination,
            "success": success,
            "message": message,
        },
    )

    # Keep only last 10 actions
    config["last_actions"] = config["last_actions"][:10]
    save_config(config)

    return success, message
