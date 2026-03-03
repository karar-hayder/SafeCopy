import hashlib
import json
import tarfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from safecopy.utils.filesUtils import scandir_walk

MANIFEST_FILENAME = "manifest.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _checksum(file_path: Path, hasher: str = "md5") -> str | None:
    """Compute a hex-digest checksum for a file."""
    try:
        h = hashlib.new(hasher)
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _checksum_from_bytes(data: bytes, hasher: str = "md5") -> str:
    """Compute a hex-digest checksum from raw bytes."""
    return hashlib.new(hasher, data).hexdigest()


# ---------------------------------------------------------------------------
# Generators — return a plain dict, no side effects
# ---------------------------------------------------------------------------


def generate_for_directory(basedir: Path, hasher: str = "md5") -> dict:
    """
    Walk a directory and return a manifest dict.
    Format: { "relative/path": { "size": int, "mtime": int, "checksum": str } }
    """
    basedir = Path(basedir)
    files_to_process = []

    for root, _, files in scandir_walk(basedir):
        root_path = Path(root)
        for name in files:
            fp = root_path / name
            arcname = str(fp.relative_to(basedir)).replace("\\", "/")
            files_to_process.append((fp, arcname))

    def _stat_and_hash(fp: Path, arcname: str):
        size = mtime = checksum = None
        try:
            stat = fp.stat()
            size = stat.st_size
            mtime = int(stat.st_mtime)
        except Exception:
            pass
        checksum = _checksum(fp, hasher)
        return arcname, {"size": size, "mtime": mtime, "checksum": checksum}

    result = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_stat_and_hash, fp, arc): arc for fp, arc in files_to_process
        }
        for future in as_completed(futures):
            arcname, entry = future.result()
            result[arcname] = entry

    return result


def generate_for_zip(zip_path: Path, hasher: str = "md5") -> dict:
    """
    Read an existing ZIP and return a manifest dict for all file members.
    Skips any existing manifest.json inside the archive.
    """
    result = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = [
            info
            for info in zf.infolist()
            if not info.is_dir() and info.filename != MANIFEST_FILENAME
        ]

        def _stat_and_hash(info: zipfile.ZipInfo):
            size = info.file_size
            mtime = int(time.mktime(info.date_time + (0, 0, -1)))
            checksum = None
            try:
                with zf.open(info, "r") as f:
                    h = hashlib.new(hasher)
                    while chunk := f.read(65536):
                        h.update(chunk)
                    checksum = h.hexdigest()
            except Exception:
                pass
            return info.filename, {"size": size, "mtime": mtime, "checksum": checksum}

        for info in members:
            arcname, entry = _stat_and_hash(info)
            result[arcname] = entry

    return result


def generate_for_tar(tar_path: Path, hasher: str = "md5") -> dict:
    """
    Read an existing TAR and return a manifest dict for all file members.
    Skips any existing manifest.json inside the archive.
    """
    result = {}
    with tarfile.open(tar_path, "r:gz") as tf:
        members = [
            m for m in tf.getmembers() if m.isfile() and m.name != MANIFEST_FILENAME
        ]

        def _stat_and_hash(member: tarfile.TarInfo):
            size = member.size
            mtime = int(member.mtime)
            checksum = None
            try:
                f = tf.extractfile(member)
                if f:
                    h = hashlib.new(hasher)
                    while chunk := f.read(65536):
                        h.update(chunk)
                    checksum = h.hexdigest()
                    f.close()
            except Exception:
                pass
            return member.name, {"size": size, "mtime": mtime, "checksum": checksum}

        for m in members:
            arcname, entry = _stat_and_hash(m)
            result[arcname] = entry

    return result


# ---------------------------------------------------------------------------
# Embedders — write manifest.json into an archive, atomically
# ---------------------------------------------------------------------------


def embed_in_zip(zip_path: Path, manifest: dict) -> None:
    """Append manifest.json to an existing ZIP file."""
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode("utf-8")
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(MANIFEST_FILENAME, manifest_bytes)


def embed_in_tar(tar_path: Path, manifest: dict) -> None:
    """
    Re-pack a TAR.GZ to include manifest.json without full extraction.
    """
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode("utf-8")
    tmp_tar = tar_path.with_suffix(".tmp.tar.gz")

    try:
        with tarfile.open(tar_path, "r:gz") as tf_old, tarfile.open(
            tmp_tar, "w:gz"
        ) as tf_new:
            # Copy all existing members
            for member in tf_old.getmembers():
                if member.name != MANIFEST_FILENAME:
                    f = tf_old.extractfile(member)
                    tf_new.addfile(member, f)

            # Add manifest
            tarinfo = tarfile.TarInfo(MANIFEST_FILENAME)
            tarinfo.size = len(manifest_bytes)
            tarinfo.mtime = int(time.time())
            import io

            tf_new.addfile(tarinfo, io.BytesIO(manifest_bytes))

        # Atomic swap
        from safecopy.utils.filesUtils import atomic_file_rename

        atomic_file_rename(tmp_tar, tar_path)

    finally:
        if tmp_tar.exists():
            try:
                tmp_tar.unlink()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Convenience loader (used by verification)
# ---------------------------------------------------------------------------


def load_manifest(backup_path: Path) -> dict | None:
    """
    Load manifest.json from a backup (ZIP, TAR, dir, or .bak sidecar).
    Returns the parsed dict, or None if not found.
    """
    backup_path = Path(backup_path)

    # ZIP archive
    if backup_path.suffix == ".zip" and backup_path.is_file():
        try:
            with zipfile.ZipFile(backup_path, "r") as zf:
                if MANIFEST_FILENAME in zf.namelist():
                    return json.loads(zf.read(MANIFEST_FILENAME))
        except Exception:
            pass
        return None

    # TAR archive
    if backup_path.name.endswith(".tar.gz") and backup_path.is_file():
        try:
            with tarfile.open(backup_path, "r:gz") as tf:
                member = next(
                    (m for m in tf.getmembers() if m.name == MANIFEST_FILENAME), None
                )
                if member:
                    f = tf.extractfile(member)
                    if f:
                        return json.loads(f.read())
        except Exception:
            pass
        return None

    # Plain directory
    if backup_path.is_dir():
        manifest_file = backup_path / MANIFEST_FILENAME
        if manifest_file.exists():
            try:
                return json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    # Plain file — sidecar <name>_manifest.json
    sidecar = backup_path.parent / (backup_path.name + "_manifest.json")
    if sidecar.exists():
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except Exception:
            pass

    return None
