"""
Backup verification and integrity checking module.
Backups now contain a manifest containing per-file checksums.
Verification reads and compares the manifest from source and backup.
"""

import hashlib
import json
import logging
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from safecopy.db.controller import DEFAULT_DB_PATH, get_db_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NORMALIZATION FIX
# ---------------------------------------------------------------------------
def normalize_key(k: str) -> str:
    """Normalize manifest paths to use forward slashes."""
    return k.replace("\\", "/")


# ---------------------------------------------------------------------------
# Manifest Loading
# ---------------------------------------------------------------------------
def load_manifest_from_dir(dir_path: Path) -> Optional[Dict]:
    manifest_path = dir_path / "manifest.json"
    if not manifest_path.exists():
        logger.warning("Manifest file not found in directory: %s", manifest_path)
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Error reading manifest.json from dir %s: %s", dir_path, e)
        return None


def load_manifest_from_zip(zip_path: Path) -> Optional[Dict]:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            with zf.open("manifest.json") as f:
                return json.load(f)
    except Exception as e:
        logger.error("Error loading manifest.json from zip %s: %s", zip_path, e)
        return None


def load_manifest_from_tar(tar_path: Path) -> Optional[Dict]:

    try:
        mode = (
            "r:gz"
            if tar_path.suffix in [".gz", ".tgz"] or tar_path.name.endswith(".tar.gz")
            else "r"
        )
        with tarfile.open(tar_path, mode) as tf:
            try:
                member = tf.getmember("manifest.json")
            except KeyError:
                logger.error("manifest.json not found in tar archive: %s", tar_path)
                return None
            f = tf.extractfile(member)
            if not f:
                logger.error(
                    "Could not extract manifest.json from tar archive: %s", tar_path
                )
                return None
            return json.load(f)
    except Exception as e:
        logger.error("Error loading manifest.json from tar %s: %s", tar_path, e)
        return None


def load_manifest(backup_path: Path) -> Optional[Dict]:
    if backup_path.is_dir():
        return load_manifest_from_dir(backup_path)
    elif backup_path.suffix == ".zip":
        return load_manifest_from_zip(backup_path)
    elif backup_path.suffix in [".tar", ".gz", ".tgz"] or backup_path.name.endswith(
        ".tar.gz"
    ):
        return load_manifest_from_tar(backup_path)
    elif (
        backup_path.is_file()
        and (backup_path.parent / (backup_path.name + "_manifest.json")).exists()
    ):
        manifest_path = backup_path.parent / (backup_path.name + "_manifest.json")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading manifest %s: %s", manifest_path, e)
    else:
        logger.warning("No manifest found alongside backup: %s", backup_path)
    return None


# ---------------------------------------------------------------------------
# Manifest Creation
# ---------------------------------------------------------------------------
def compute_source_manifest(source_path: Path) -> Optional[Dict]:
    manifest = {}
    try:
        if source_path.is_file():
            sz = source_path.stat().st_size
            mtime = int(source_path.stat().st_mtime)
            checksum = calculate_checksum(source_path)
            manifest[source_path.name] = {
                "size": sz,
                "mtime": mtime,
                "checksum": checksum,
            }
        else:
            for path in sorted(source_path.rglob("*")):
                if path.is_file():
                    rel = str(path.relative_to(source_path))
                    try:
                        sz = path.stat().st_size
                    except Exception:
                        sz = None
                    try:
                        mtime = int(path.stat().st_mtime)
                    except Exception:
                        mtime = None
                    try:
                        checksum = calculate_checksum(path)
                    except Exception:
                        checksum = None

                    # normalize source paths immediately
                    manifest[normalize_key(rel)] = {
                        "size": sz,
                        "mtime": mtime,
                        "checksum": checksum,
                    }
    except Exception as e:
        logger.error("Error computing manifest for source: %s", e)
        return None
    return manifest


# ---------------------------------------------------------------------------
# Manifest Comparison (FIXED)
# ---------------------------------------------------------------------------
def compare_manifests(src_manifest: Dict, backup_manifest: Dict) -> Tuple[bool, str]:
    """
    Compare normalized manifests. Returns (success, message).
    """

    # Normalize backup manifest keys too
    src_norm = {normalize_key(k): v for k, v in src_manifest.items()}
    bkp_norm = {normalize_key(k): v for k, v in backup_manifest.items()}

    src_files = set(src_norm.keys())
    backup_files = set(bkp_norm.keys())

    missing_in_backup = src_files - backup_files
    extra_in_backup = backup_files - src_files
    mismatches = []

    for k in src_files & backup_files:
        s = src_norm[k]
        b = bkp_norm[k]
        if s.get("size") != b.get("size") or s.get("checksum") != b.get("checksum"):
            mismatches.append(
                f"{k}: src(size={s.get('size')} MD5={s.get('checksum')}) "
                f"!= backup(size={b.get('size')} MD5={b.get('checksum')})"
            )

    if missing_in_backup or extra_in_backup or mismatches:
        msg = "Mismatch in backup verification:\n"
        if missing_in_backup:
            msg += f"Files missing in backup: {sorted(missing_in_backup)}\n"
        if extra_in_backup:
            msg += f"Extra files in backup: {sorted(extra_in_backup)}\n"
        if mismatches:
            msg += "File content mismatches:\n" + "\n".join(mismatches)
        return False, msg

    return True, "Backup manifest matches source manifest."


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def calculate_checksum(file_path: Path, algorithm: str = "md5") -> Optional[str]:
    try:
        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.error("Error calculating checksum for %s: %s", file_path, e)
        return None


# ---------------------------------------------------------------------------
# Verification Entry Point
# ---------------------------------------------------------------------------
def verify_backup(
    source_path: str,
    backup_path: str,
    algorithm: str = "md5",
) -> Tuple[bool, str, Optional[str], Optional[str]]:

    src = Path(source_path)
    bkp = Path(backup_path)

    if not src.exists():
        msg = f"Source path does not exist: {src}"
        logger.error("Backup verification failed: %s", msg)
        return False, msg, None, None

    if not bkp.exists():
        msg = f"Backup path does not exist: {bkp}"
        logger.error("Backup verification failed: %s", msg)
        return False, msg, None, None

    # Load manifests
    src_manifest = compute_source_manifest(src)
    if src_manifest is None:
        msg = "Failed to construct source manifest"
        logger.error(msg)
        return False, msg, None, None

    backup_manifest = load_manifest(bkp)
    if backup_manifest is None:
        msg = f"Could not locate manifest in backup: {bkp}"
        logger.error(msg)
        return False, msg, None, None

    # Normalize backup manifest as well
    backup_manifest = {normalize_key(k): v for k, v in backup_manifest.items()}

    # Compare
    match, msg = compare_manifests(src_manifest, backup_manifest)

    # Manifest digests
    def manifest_digest(js):
        try:
            return hashlib.md5(
                json.dumps(js, sort_keys=True).encode("utf-8")
            ).hexdigest()
        except Exception:
            return None

    src_md5 = manifest_digest(src_manifest)
    bkp_md5 = manifest_digest(backup_manifest)

    if match:
        logger.info("Backup verification succeeded (per manifest): %s", msg)
        return True, msg, src_md5, bkp_md5
    else:
        logger.warning("Backup verification failed: %s", msg)
        return False, msg, src_md5, bkp_md5


def save_verification_result(
    backup_history_id: int,
    checksum_type: str,
    source_checksum: str,
    backup_checksum: str,
    verification_status: bool,
    verification_msg: str = "",
    db_path: str = None,
) -> bool:
    """
    Save backup verification result to database.

    Args:
        backup_history_id: ID of backup history entry
        checksum_type: Type of checksum used
        source_checksum: Source manifest checksum (digest)
        backup_checksum: Backup manifest checksum (digest)
        verification_status: Whether verification passed
        verification_msg: Human-readable verification result/summary
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
            logger.debug(
                "Saved verification result for backup history %s", backup_history_id
            )
            return True
    except Exception as e:
        logger.error("Error saving verification result: %s", e)
        return False


def get_verification_result(
    backup_history_id: int, db_path: str = None
) -> Optional[dict]:
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
                       verification_status, verification_msg, verified_at
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
                    "verification_msg": row.get("verification_msg", ""),
                    "verified_at": row["verified_at"],
                }
    except Exception as e:
        logger.error("Error getting verification result: %s", e)
    return None
