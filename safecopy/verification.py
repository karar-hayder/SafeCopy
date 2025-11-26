"""
Backup verification and integrity checking module.
"""

import hashlib
import logging
import tempfile
import shutil
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, Tuple
from safecopy.db.controller import get_db_connection, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def calculate_checksum(file_path: Path, algorithm: str = "md5") -> Optional[str]:
    """
    Calculate checksum for a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')

    Returns:
        Hex digest of checksum or None if error
    """
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error("Error calculating checksum for %s: %s", file_path, e)
        return None


def calculate_directory_checksum(dir_path: Path, algorithm: str = "md5") -> Optional[str]:
    """
    Calculate combined checksum for all files in a directory.

    Args:
        dir_path: Path to directory
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')

    Returns:
        Hex digest of combined checksum or None if error
    """
    try:
        hash_obj = hashlib.new(algorithm)
        files = sorted(dir_path.rglob("*"))
        for file_path in files:
            if file_path.is_file():
                # Include relative path in hash
                rel_path = file_path.relative_to(dir_path)
                hash_obj.update(str(rel_path).encode())
                file_hash = calculate_checksum(file_path, algorithm)
                if file_hash:
                    hash_obj.update(file_hash.encode())
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error("Error calculating directory checksum for %s: %s", dir_path, e)
        return None


def _extract_archive_to_temp(archive_path: Path) -> Optional[tempfile.TemporaryDirectory]:
    """
    Extract the given archive file (.zip, .tar, .gz, .tar.gz) to a temporary directory.
    Returns the TemporaryDirectory object if successful, or None if failed.
    The caller is responsible for cleaning up the temporary directory.
    """
    try:
        temp_dir = tempfile.TemporaryDirectory()
        extract_path = Path(temp_dir.name)
        # Handle zip files
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_path)
        # Handle .tar, .tar.gz, .tgz, .gz
        elif (
            archive_path.suffix in [".tar", ".gz"]
            or archive_path.name.endswith(".tar.gz")
            or archive_path.suffix == ".tgz"
        ):
            # .tar.gz or .tgz
            tar_mode = (
                "r:gz"
                if archive_path.suffix == ".gz"
                or archive_path.suffix == ".tgz"
                or archive_path.name.endswith(".tar.gz")
                else "r"
            )
            with tarfile.open(archive_path, tar_mode) as tf:
                tf.extractall(extract_path)
        else:
            logger.error("Unknown archive type for extraction: %s", archive_path)
            temp_dir.cleanup()
            return None
        return temp_dir
    except Exception as e:
        logger.error("Failed to extract archive for verification: %s", e)
        return None


def verify_backup(
    source_path: str,
    backup_path: str,
    algorithm: str = "md5",
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verify backup integrity by comparing checksums.
    If backup is a zip/tar archive and source is a directory, extract and compare directory checksums.

    Args:
        source_path: Path to source directory
        backup_path: Path to backup location (file or directory or archive)
        algorithm: Hash algorithm to use

    Returns:
        Tuple of (success: bool, source_checksum: str, backup_checksum: str)
    """
    source = Path(source_path)
    backup = Path(backup_path)

    if not source.exists():
        msg = f"Source path does not exist: {source}"
        logger.error("Backup verification failed: %s", msg)
        return False, None, None

    if not backup.exists():
        msg = f"Backup path does not exist: {backup}"
        logger.error("Backup verification failed: %s", msg)
        return False, None, None

    try:
        # Calculate source checksum
        if source.is_file():
            source_checksum = calculate_checksum(source, algorithm)
            logger.debug("Calculated checksum for source file %s: %s", source, source_checksum)
        else:
            source_checksum = calculate_directory_checksum(source, algorithm)
            logger.debug("Calculated checksum for source directory %s: %s", source, source_checksum)

        if not source_checksum:
            msg = f"Failed to calculate checksum for source: {source}"
            logger.error("Backup verification failed: %s", msg)
            return False, None, None

        backup_checksum = None
        info_msg = ""

        # If backup is a compressed archive and source is a directory, extract and compare directory checksums
        if backup.suffix in [".zip", ".tar", ".gz", ".tgz"] or backup.name.endswith(".tar.gz"):
            if backup.stat().st_size > 0:
                if source.is_dir():
                    temp_dir = _extract_archive_to_temp(backup)
                    if not temp_dir:
                        msg = "Failed to extract backup archive for content verification."
                        logger.error("Backup verification failed: %s", msg)
                        return False, source_checksum, None
                    extract_path = Path(temp_dir.name)
                    backup_checksum = calculate_directory_checksum(extract_path, algorithm)
                    info_msg = "Backup is an archive. Checksums computed by extracting and comparing directory contents."
                    temp_dir.cleanup()
                    logger.info("Backup verification: %s", info_msg)
                else:
                    # Fall back to comparing file hash if source is a file
                    backup_checksum = calculate_checksum(backup, algorithm)
                    info_msg = "Backup is a compressed archive, source is a file. Compared archive file checksum only."
                    logger.info("Backup verification: %s", info_msg)
            else:
                msg = f"Backup file is empty: {backup}"
                logger.error("Backup verification failed: %s", msg)
                return False, source_checksum, None
        elif backup.is_file():
            backup_checksum = calculate_checksum(backup, algorithm)
            if source.is_file():
                info_msg = "Backup and source are both files."
            else:
                info_msg = "Warning: Source is a directory, but backup is a file."
            logger.info("Backup verification: %s", info_msg)
        else:
            backup_checksum = calculate_directory_checksum(backup, algorithm)
            info_msg = "Both source and backup are directories. Directory checksums compared."
            logger.info("Backup verification: %s", info_msg)

        if not backup_checksum:
            msg = f"Failed to calculate checksum for backup: {backup}"
            logger.error("Backup verification failed: %s", msg)
            return False, source_checksum, None

        if source_checksum == backup_checksum:
            msg = (
                f"Backup verification succeeded: checksums match.\n"
                f"Source checksum: {source_checksum}\n"
                f"Backup checksum: {backup_checksum}"
            )
            logger.info(msg)
            return True, source_checksum, backup_checksum
        else:
            msg = (
                f"Backup verification failed: checksums do not match.\n"
                f"Source checksum: {source_checksum}\n"
                f"Backup checksum: {backup_checksum}"
            )
            logger.warning(msg)
            return False, source_checksum, backup_checksum

    except Exception as e:
        msg = f"Error verifying backup: {e}"
        logger.error("Backup verification error: %s", msg)
        return False, None, None


def save_verification_result(
    backup_history_id: int,
    checksum_type: str,
    source_checksum: str,
    backup_checksum: str,
    verification_status: bool,
    db_path: str = None,
) -> bool:
    """
    Save backup verification result to database.

    Args:
        backup_history_id: ID of backup history entry
        checksum_type: Type of checksum used
        source_checksum: Source checksum
        backup_checksum: Backup checksum
        verification_status: Whether verification passed
        db_path: Path to database file

    Returns:
        True if saved successfully, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO backup_verification
                (backup_history_id, checksum_type, source_checksum, backup_checksum,
                 verification_status, verified_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    backup_history_id,
                    checksum_type,
                    source_checksum,
                    backup_checksum,
                    1 if verification_status else 0,
                ),
            )
            logger.debug("Saved verification result for backup history %s", backup_history_id)
            return True
    except Exception as e:
        logger.error("Error saving verification result: %s", e)
        return False


def get_verification_result(backup_history_id: int, db_path: str = None) -> Optional[dict]:
    """
    Get verification result for a backup.

    Args:
        backup_history_id: ID of backup history entry
        db_path: Path to database file

    Returns:
        Dictionary with verification data or None if not found
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, checksum_type, source_checksum, backup_checksum,
                       verification_status, verified_at
                FROM backup_verification
                WHERE backup_history_id = ?
                LIMIT 1
            """,
                (backup_history_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "checksum_type": row["checksum_type"],
                    "source_checksum": row["source_checksum"],
                    "backup_checksum": row["backup_checksum"],
                    "verification_status": bool(row["verification_status"]),
                    "verified_at": row["verified_at"],
                }
    except Exception as e:
        logger.error("Error getting verification result: %s", e)
    return None
