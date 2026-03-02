import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from safecopy.backup.manifest import generate_for_directory, load_manifest

# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------


@dataclass
class VerificationResult:
    success: bool
    message: str
    source_checksum: str | None = None  # MD5 of the serialized source manifest
    backup_checksum: str | None = None  # MD5 of the serialized backup manifest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _manifest_digest(manifest: dict) -> str | None:
    """Stable MD5 over a sorted JSON serialization of a manifest dict."""
    try:
        return hashlib.md5(
            json.dumps(manifest, sort_keys=True).encode("utf-8")
        ).hexdigest()
    except Exception:
        return None


def _normalize_key(key: str) -> str:
    """Normalize path separators so Windows and POSIX paths compare equal."""
    return key.replace("\\", "/")


def _build_source_manifest(source_path: Path) -> dict | None:
    """
    Produce a manifest dict for the source (file or directory).
    Returns None on failure.
    """
    try:
        source_path = Path(source_path)
        if source_path.is_file():
            return generate_for_directory(source_path.parent)
        return generate_for_directory(source_path)
    except Exception:
        return None


def _compare(source_manifest: dict, backup_manifest: dict) -> tuple[bool, str]:
    """
    Compare two manifest dicts key by key.
    Returns (match: bool, message: str).
    """
    src_keys = set(source_manifest)
    bkp_keys = set(backup_manifest)

    missing = src_keys - bkp_keys
    if missing:
        return False, f"Missing in backup: {', '.join(sorted(missing))}"

    extra = bkp_keys - src_keys
    if extra:
        return False, f"Extra files in backup: {', '.join(sorted(extra))}"

    for key in sorted(src_keys):
        src_entry = source_manifest[key]
        bkp_entry = backup_manifest[key]
        src_csum = src_entry.get("checksum")
        bkp_csum = bkp_entry.get("checksum")
        if src_csum and bkp_csum and src_csum != bkp_csum:
            return False, f"Checksum mismatch for '{key}': {src_csum} != {bkp_csum}"

    return True, "All files verified successfully"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify(source_path: str | Path, backup_path: str | Path) -> VerificationResult:
    """
    Verify that a backup matches its source by comparing manifests.

    Steps:
      1. Build a manifest from the source.
      2. Load the manifest embedded in the backup.
      3. Compare them key by key.

    Returns a VerificationResult with checksums over the serialized manifests.
    """
    source_path = Path(source_path)
    backup_path = Path(backup_path)

    if not source_path.exists():
        return VerificationResult(
            success=False,
            message=f"Source does not exist: {source_path}",
        )

    if not backup_path.exists():
        return VerificationResult(
            success=False,
            message=f"Backup does not exist: {backup_path}",
        )

    # Build source manifest
    src_manifest = _build_source_manifest(source_path)
    if src_manifest is None:
        return VerificationResult(
            success=False,
            message="Failed to build source manifest",
        )

    # If source is a single file, we only care about that one file's entry
    if source_path.is_file():
        key = _normalize_key(source_path.name)
        src_manifest = (
            {
                key: src_manifest[
                    next(k for k in src_manifest if _normalize_key(k) == key)
                ]
            }
            if any(_normalize_key(k) == key for k in src_manifest)
            else {}
        )

    # Load backup manifest
    bkp_manifest = load_manifest(backup_path)
    if bkp_manifest is None:
        return VerificationResult(
            success=False,
            message=f"No manifest found in backup: {backup_path}",
        )

    # Normalize keys
    src_manifest = {_normalize_key(k): v for k, v in src_manifest.items()}
    bkp_manifest = {_normalize_key(k): v for k, v in bkp_manifest.items()}

    match, message = _compare(src_manifest, bkp_manifest)

    return VerificationResult(
        success=match,
        message=message,
        source_checksum=_manifest_digest(src_manifest),
        backup_checksum=_manifest_digest(bkp_manifest),
    )
