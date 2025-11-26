import logging
import os
import re
import shutil
import tarfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

from safecopy import notifications, verification
from safecopy.config import USE_DATABASE, load_config, save_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("safecopy.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def sanitize_filename(name, max_length=40):
    """
    Sanitize a string to be used as a safe part of a filename.
    Removes unsafe characters and trims the length.
    """
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    if len(name) > max_length:
        name = name[:max_length]
    return name


def perform_backup(
    source_path, dest_path, max_versions=3, compression="none", mapping_id=None
):
    """
    Perform a backup of the source directory to the destination directory.

    Args:
        source_path (str): Path to the source directory
        dest_path (str): Path to the destination directory
        max_versions (int): Maximum number of backup versions to keep
        compression (str): Compression type ('none', 'zip', or 'tar')
        mapping_id (any, optional): Optional mapping ID (used in filename if provided)

    Returns:
        tuple: (success: bool, message: str, duration: float, size_bytes: int, backup_path: str)
    """
    start_time = time.time()
    backup_path = None
    size_bytes = 0

    try:
        source_path = Path(source_path)
        dest_path = Path(dest_path)

        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        # Create destination directory if it doesn't exist
        dest_path.mkdir(parents=True, exist_ok=True)

        # Generate backup name: backup_<YYYYMMDD_HHMMSS>_<sanitized-source>_<mappingid>_<compression>
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_name = sanitize_filename(source_path.name)
        mapping_part = ""
        if mapping_id is not None:
            mapping_part = f"{mapping_id}"
        compression_part = (
            compression if compression and compression != "none" else "plain"
        )

        backup_name_parts = [
            "backup",
            timestamp,
            source_name,
        ]
        if mapping_part:
            backup_name_parts.append(mapping_part)
        backup_name_parts.append(compression_part)
        backup_name = "_".join(str(part) for part in backup_name_parts if part)

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

        # Calculate backup size
        if backup_path.is_file():
            size_bytes = backup_path.stat().st_size
        else:
            # Calculate directory size
            for dirpath, _, filenames in os.walk(backup_path):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    size_bytes += filepath.stat().st_size

        # Clean up old backups if exceeding max_versions
        cleanup_old_backups(dest_path, max_versions)

        duration = time.time() - start_time
        message = f"Backup completed successfully: {backup_path}"
        logger.info(message)
        return True, message, duration, size_bytes, str(backup_path)

    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Backup failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, duration, 0, None


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
            logger.info("Removed old backup: %s", backup)

    except Exception as e:
        logger.error("Warning: Failed to cleanup old backups: %s", e)


def run_backup(mapping):
    """
    Run a backup operation for a specific mapping.

    Args:
        mapping (dict): Mapping configuration containing source and destination paths
            Can include 'id' if from database

    Returns:
        tuple: (success: bool, message: str)
    """
    source = mapping.get("source")
    destination = mapping.get("destination")
    max_versions = mapping.get("maxVersions", 3)
    compression = mapping.get("compression", "none")
    mapping_id = mapping.get("id")  # Database mapping ID if available

    if not source or not destination:
        return False, "Invalid mapping configuration"

    # Pass mapping_id down for best naming
    success, message, duration, size_bytes, backup_path = perform_backup(
        source, destination, max_versions, compression, mapping_id=mapping_id
    )

    # Log to database or JSON
    history_id = None
    if USE_DATABASE:
        from safecopy.db.controller import add_backup_history

        history_id = add_backup_history(
            mapping_id=mapping_id,
            success=success,
            message=message,
            duration=duration,
            size_bytes=size_bytes,
            backup_path=backup_path,
        )

        # Verify backup if successful and save verification result
        if history_id and success and backup_path:
            try:
                verify_success, source_checksum, backup_checksum = (
                    verification.verify_backup(source, backup_path)
                )
                if not verify_success:
                    logger.warning("Backup verification failed for %s", backup_path)
                    message += " (Verification failed)"

                verification.save_verification_result(
                    backup_history_id=history_id,
                    checksum_type="md5",
                    source_checksum=source_checksum or "",
                    backup_checksum=backup_checksum or "",
                    verification_status=verify_success,
                )
            except Exception as e:
                logger.error("Error during backup verification: %s", e)
    else:
        # Update last actions in JSON config
        config = load_config()
        config.setdefault("last_actions", [])
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

    # Send email notification
    try:
        notifications.send_backup_notification(
            success=success,
            mapping_source=source,
            mapping_destination=destination,
            message=message,
            duration=duration,
            size_bytes=size_bytes,
        )
    except Exception as e:
        logger.error("Error sending email notification: %s", e)

    return success, message
