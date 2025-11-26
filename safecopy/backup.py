import logging
import os
import re
import shutil
import tarfile
import time
import uuid
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
    Perform a backup of the source directory or file to the destination directory.

    Args:
        source_path (str): Path to the source directory or file
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

        # Ensure destination exists
        dest_path.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------------------------
        # SHORT, WINDOWS-FRIENDLY BACKUP NAME
        # ------------------------------------------------------------------
        # Old names were 70–120 chars, breaking MAX_PATH. These are < 40 chars.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = sanitize_filename(source_path.name)[:12]
        mapping_part = f"{mapping_id}" if mapping_id is not None else ""
        uid = uuid.uuid4().hex[:6]
        comp = "plain" if compression == "none" else compression

        # Example: bk_20250101_153045_src_4A2F1A_plain
        parts = ["bk", timestamp, src]
        if mapping_part:
            parts.append(mapping_part)
        parts.append(uid)
        parts.append(comp)
        backup_stem = "_".join(parts)

        # ------------------------------------------------------------------
        # Create backup
        # ------------------------------------------------------------------
        if compression == "zip":
            backup_path = dest_path / f"{backup_stem}.zip"
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                if source_path.is_dir():
                    for root, _, files in os.walk(source_path):
                        for file in files:
                            fp = Path(root) / file
                            arcname = fp.relative_to(
                                source_path
                            )  # correct arcname: relative to source_path
                            zipf.write(fp, arcname)
                else:
                    zipf.write(source_path, arcname=source_path.name)

        elif compression == "tar":
            backup_path = dest_path / f"{backup_stem}.tar.gz"
            with tarfile.open(backup_path, "w:gz") as tar:
                arcname = source_path.name
                tar.add(source_path, arcname=arcname)

        else:
            # NONE: copy tree or file
            if source_path.is_dir():
                backup_path = dest_path / backup_stem
                shutil.copytree(source_path, backup_path, dirs_exist_ok=False)
            else:
                backup_path = dest_path / f"{backup_stem}.bak"
                shutil.copy2(source_path, backup_path)

        # ------------------------------------------------------------------
        # Validate backup exists & measure size
        # ------------------------------------------------------------------
        if not backup_path.exists():
            raise RuntimeError("Backup creation failed: path not created.")

        if backup_path.is_file():
            size_bytes = backup_path.stat().st_size
            if size_bytes == 0:
                raise RuntimeError("Backup file created but is empty.")
        else:
            for dp, _, fns in os.walk(backup_path):
                for f in fns:
                    size_bytes += (Path(dp) / f).stat().st_size

        # ------------------------------------------------------------------
        # Apply retention policy
        # ------------------------------------------------------------------
        cleanup_old_backups(dest_path, max_versions)

        duration = time.time() - start_time
        msg = f"Backup completed successfully: {backup_path}"
        logger.info(msg)
        return True, msg, duration, size_bytes, str(backup_path)

    except Exception as e:
        duration = time.time() - start_time
        msg = f"Backup failed: {e}"
        logger.error(msg)
        return False, msg, duration, 0, None


def cleanup_old_backups(dest_path, max_versions):
    """
    Remove the oldest backups while keeping only the newest `max_versions`.
    """

    try:
        dest_path = Path(dest_path)

        if max_versions < 1 or not dest_path.exists():
            return

        # Collect items that look like backups
        backups = [
            p
            for p in dest_path.iterdir()
            if p.name.startswith("bk_") and (p.is_file() or p.is_dir())
        ]

        if not backups:
            return

        # Sort newest → oldest, with tie-break by name
        backups_sorted = sorted(
            backups,
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        )

        # Remove everything older than the N newest
        for old in backups_sorted[max_versions:]:
            try:
                if old.is_file():
                    old.unlink()
                else:
                    shutil.rmtree(old)
                logger.info("Removed old backup: %s", old)
            except Exception as e:
                logger.error("Error removing backup %s: %s", old, e)

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
        logger.error("Invalid mapping configuration: source or destination missing.")
        # even on error, still try to record the attempt if not using DB
        # (but config recording below is always after the perform_backup except branch)
        return False, "Invalid mapping configuration"

    try:
        success, message, duration, size_bytes, backup_path = perform_backup(
            source, destination, max_versions, compression, mapping_id=mapping_id
        )
    except Exception as e:
        logger.error("perform_backup raised an exception: %s", e)
        # Even if backup completely fails, record attempt in last_actions (JSON mode)
        success, message, duration, size_bytes, backup_path = (
            False,
            f"Backup process failed: {str(e)}",
            0,
            0,
            None,
        )

    history_id = None
    if USE_DATABASE:
        try:
            from safecopy.db.controller import add_backup_history

            history_id = add_backup_history(
                mapping_id=mapping_id,
                success=success,
                message=message,
                duration=duration,
                size_bytes=size_bytes,
                backup_path=backup_path,
            )

            if history_id and success and backup_path:
                try:
                    verify_success, source_checksum, backup_checksum = (
                        verification.verify_backup(source, backup_path)
                    )
                    if not verify_success:
                        logger.warning("Backup verification failed for %s", backup_path)
                        message += " (Verification failed)"

                    try:
                        verification.save_verification_result(
                            backup_history_id=history_id,
                            checksum_type="md5",
                            source_checksum=source_checksum or "",
                            backup_checksum=backup_checksum or "",
                            verification_status=verify_success,
                        )
                    except Exception as ve:
                        logger.error("Error saving verification result: %s", ve)
                except Exception as e:
                    logger.error("Error during backup verification: %s", e)
        except Exception as e:
            logger.error("Error in database history logic: %s", e)
    else:
        # Always add to last_actions in JSON config, even on failure,
        # even if config file didn't exist yet
        try:
            config = load_config()
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            config = {}

        # Ensure "last_actions" exists and is a list
        if not isinstance(config.get("last_actions"), list):
            config["last_actions"] = []
        action = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "destination": destination,
            "success": success,
            "message": message,
        }
        try:
            config["last_actions"].insert(0, action)
            config["last_actions"] = config["last_actions"][:10]
            save_config(config)
        except Exception as e:
            logger.error("Error saving last_actions: %s", e)

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
