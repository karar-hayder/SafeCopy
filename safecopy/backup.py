import hashlib
import json
import logging
import os
import re
import shutil
import tarfile
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from safecopy import notifications, verification
from safecopy.config import USE_DATABASE, load_config, save_config
from safecopy.cryptor import Cryptor

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


def scandir_walk(top):
    """
    Walk a directory tree using os.scandir.
    Yields (dirpath, dirs, files).
    """
    top = Path(top)
    dirs, files = [], []
    with os.scandir(top) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                dirs.append(entry.name)
            elif entry.is_file(follow_symlinks=False):
                files.append(entry.name)
    yield str(top), dirs, files
    for d in dirs:
        yield from scandir_walk(top / d)


def _compute_file_checksum(file_path, hasher="md5"):
    """Compute and return checksum for a file."""
    h = hashlib.new(hasher)
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def scandir_copytree(src, dst, log_every_n=100):
    """
    Recursively copy directory tree using os.scandir.
    Returns total bytes copied, file count.
    """
    total = 0
    file_count = 0
    src = Path(src)
    dst = Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for item in os.scandir(src):
        src_path = src / item.name
        dst_path = dst / item.name
        if item.is_dir(follow_symlinks=False):
            size, count = scandir_copytree(
                src_path,
                dst_path,
                log_every_n=log_every_n,
            )
            total += size
            file_count += count
        elif item.is_file(follow_symlinks=False):
            shutil.copy2(src_path, dst_path)
            try:
                sz = dst_path.stat().st_size
                total += sz
            except Exception:
                sz = 0
            file_count += 1
    return total, file_count


def atomic_file_rename(tmp_path, final_path):
    """
    Atomically move the temporary file to the final location.
    Overwrites the final path if necessary.
    """
    try:
        os.replace(str(tmp_path), str(final_path))
    except Exception as e:
        logger.error("Atomic rename failed: %s", e)
        raise


def _generate_manifest_for_directory(basedir, rel_base=None, hasher="md5"):
    """
    Walk directory and generate manifest: relpath -> {size, mtime, checksum}
    """
    basedir = Path(basedir)
    if rel_base is None:
        rel_base = basedir

    files_to_process = []
    for root, _, files in scandir_walk(basedir):
        root_path = Path(root)
        for file in files:
            fp = root_path / file
            arcname = str(fp.relative_to(rel_base))
            files_to_process.append((fp, arcname))

    def stat_and_hash(fp):
        try:
            sz = fp.stat().st_size
        except Exception:
            sz = None
        try:
            mtime = int(fp.stat().st_mtime)
        except Exception:
            mtime = None
        try:
            checksum = _compute_file_checksum(fp, hasher=hasher)
        except Exception:
            checksum = None
        return sz, mtime, checksum

    result = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(stat_and_hash, fp): arcname
            for fp, arcname in files_to_process
        }
        for future in as_completed(future_map):
            arcname = future_map[future]
            sz, mtime, checksum = future.result()
            result[arcname] = {
                "size": sz,
                "mtime": mtime,
                "checksum": checksum,
            }
    return result


def _generate_manifest_for_zip(zip_path, hasher="md5"):
    """
    Generate manifest for a zip file (assume no manifest embedded yet!)
    Returns dict: arcname -> {size, mtime, checksum}
    """
    manifest = {}
    with zipfile.ZipFile(zip_path, "r") as zipf:
        infolist = [
            zinfo
            for zinfo in zipf.infolist()
            if not zinfo.is_dir() and zinfo.filename != "manifest.json"
        ]

        def stat_and_hash(zinfo):
            size = zinfo.file_size
            mtime = int(time.mktime(zinfo.date_time + (0, 0, -1)))
            try:
                with zipf.open(zinfo, "r") as f:
                    h = hashlib.new(hasher)
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                checksum = h.hexdigest()
            except Exception:
                checksum = None
            return zinfo.filename, size, mtime, checksum

        results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(stat_and_hash, zinfo) for zinfo in infolist]
            for future in as_completed(futures):
                arcname, size, mtime, checksum = future.result()
                results[arcname] = {
                    "size": size,
                    "mtime": mtime,
                    "checksum": checksum,
                }
        manifest.update(results)
    return manifest


def _generate_manifest_for_tar(tar_path, hasher="md5"):
    """
    Generate manifest for a tar.gz file (assume no manifest inside yet!)
    Returns dict: arcname -> {size, mtime, checksum}
    """
    manifest = {}
    import tarfile as tf

    with tf.open(tar_path, "r:gz") as tarf:
        members = [
            m for m in tarf.getmembers() if m.isfile() and m.name != "manifest.json"
        ]

        def stat_and_hash(member):
            size = member.size
            mtime = int(member.mtime)
            checksum = None
            try:
                f = tarf.extractfile(member)
                if f:
                    h = hashlib.new(hasher)
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                    checksum = h.hexdigest()
                    f.close()
            except Exception:
                pass
            return member.name, size, mtime, checksum

        results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(stat_and_hash, m) for m in members]
            for future in as_completed(futures):
                arcname, size, mtime, checksum = future.result()
                results[arcname] = {
                    "size": size,
                    "mtime": mtime,
                    "checksum": checksum,
                }
        manifest.update(results)
    return manifest


def perform_backup(
    source_path,
    dest_path,
    max_versions=3,
    compression="none",
    mapping_id=None,
    verbose=False,
    encrypted=False,
    passwd_mode="none",
):
    """
    Perform a backup of the source directory or file to the destination directory.

    Args:
        source_path (str): Path to the source directory or file
        dest_path (str): Path to the destination directory
        max_versions (int): Maximum number of backup versions to keep
        compression (str): Compression type ('none', 'zip', or 'tar')
        mapping_id (any, optional): Optional mapping ID (used in filename if provided)
        verbose (bool): If True, enables extra logging/printing

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
        dest_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = sanitize_filename(source_path.name)[:12]
        mapping_part = f"{mapping_id}" if mapping_id is not None else ""
        uid = uuid.uuid4().hex[:6]
        comp = "plain" if compression == "none" else compression

        parts = ["bk", timestamp, src]
        if mapping_part:
            parts.append(mapping_part)
        parts.append(uid)
        parts.append(comp)
        backup_stem = "_".join(parts)
        manifest_filename = "manifest.json"

        if compression == "zip":
            backup_path = dest_path / f"{backup_stem}.zip"
            tmp_path = dest_path / ("tmp_" + backup_path.name)
            manifest = {}
            file_count = 0

            def _stream_file_to_zip(zipf, fs_path, arcname):
                h = hashlib.md5()
                sz = None
                mtime = None
                try:
                    file_stat = fs_path.stat()
                    sz = file_stat.st_size
                    mtime = int(file_stat.st_mtime)
                except Exception:
                    sz = None
                    mtime = None
                with open(fs_path, "rb") as fsrc:
                    zipw = zipf.open(arcname, mode="w")
                    try:
                        while True:
                            chunk = fsrc.read(65536)
                            if not chunk:
                                break
                            zipw.write(chunk)
                            h.update(chunk)
                    finally:
                        zipw.close()
                checksum = h.hexdigest()
                return {"size": sz, "mtime": mtime, "checksum": checksum}

            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                if source_path.is_dir():
                    for root, _, files in scandir_walk(source_path):
                        root_path = Path(root)
                        for file in files:
                            fp = root_path / file
                            arcname = str(fp.relative_to(source_path)).replace(
                                "\\", "/"
                            )
                            manifest[arcname] = _stream_file_to_zip(zipf, fp, arcname)
                            file_count += 1
                else:
                    arcname = source_path.name
                    manifest[arcname] = _stream_file_to_zip(zipf, source_path, arcname)
                    file_count += 1
                manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode(
                    "utf-8"
                )
                zipf.writestr(manifest_filename, manifest_bytes)
            atomic_file_rename(tmp_path, backup_path)

        elif compression == "tar":
            backup_path = dest_path / f"{backup_stem}.tar.gz"
            tmp_path = dest_path / ("tmp_" + backup_path.name)
            # 1. Create tar.gz from source files/dirs (all handles automatically closed)
            with tarfile.open(tmp_path, "w:gz") as tar:
                file_count = 0
                if source_path.is_dir():
                    for root, _, files in scandir_walk(source_path):
                        root_path = Path(root)
                        for file in files:
                            fp = root_path / file
                            arcname = str(fp.relative_to(source_path))
                            tar.add(fp, arcname=arcname)
                            file_count += 1
                else:
                    tar.add(source_path, arcname=source_path.name)
            # 2. Move the tar to its backup location before further editing
            atomic_file_rename(tmp_path, backup_path)
            # 3. Generate manifest and write to temp json file (handles closed after write)
            manifest = _generate_manifest_for_tar(backup_path)
            manifest_json_path = dest_path / ("tmp_" + backup_stem + "_manifest.json")
            with open(manifest_json_path, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, separators=(",", ":"))
            # 4. Workaround: extract all tar contents to a temp dir, add manifest, create new tar with manifest
            import tempfile

            temp_extract_dir = tempfile.mkdtemp()
            try:
                # Extract tar to temp dir (closing after extraction)
                with tarfile.open(backup_path, "r:gz") as tar_read:
                    tar_read.extractall(temp_extract_dir)
                manifest_copy_path = os.path.join(temp_extract_dir, manifest_filename)
                shutil.copy2(manifest_json_path, manifest_copy_path)
                # All handles so far are closed. Now create final tar with manifest included:
                temp_tar_path = dest_path / ("tmp2_" + backup_path.name)
                with tarfile.open(temp_tar_path, "w:gz") as tar_new:
                    for root, _, files in scandir_walk(temp_extract_dir):
                        root_path = Path(root)
                        for file in files:
                            fp = root_path / file
                            arcname = str(fp.relative_to(temp_extract_dir)).replace(
                                "\\", "/"
                            )
                            tar_new.add(fp, arcname=arcname)
                # Again, all handles are closed before rename
                atomic_file_rename(temp_tar_path, backup_path)
            finally:
                shutil.rmtree(temp_extract_dir)
            manifest_json_path.unlink()

        else:
            if source_path.is_dir():
                backup_path = dest_path / backup_stem
                tmp_path = dest_path / ("tmp_" + backup_stem)
                if tmp_path.exists():
                    if tmp_path.is_file():
                        tmp_path.unlink()
                    else:
                        shutil.rmtree(tmp_path)
                size_bytes, file_count = scandir_copytree(
                    source_path,
                    tmp_path,
                )
                atomic_file_rename(tmp_path, backup_path)
                manifest = _generate_manifest_for_directory(
                    backup_path, rel_base=backup_path
                )
                manifest_path = backup_path / manifest_filename
                with open(manifest_path, "w", encoding="utf-8") as mf:
                    json.dump(manifest, mf, separators=(",", ":"))
            else:
                backup_path = dest_path / f"{backup_stem}.bak"
                tmp_path = dest_path / ("tmp_" + backup_path.name)
                shutil.copy2(source_path, tmp_path)
                try:
                    size_bytes = tmp_path.stat().st_size
                except Exception:
                    size_bytes = 0
                atomic_file_rename(tmp_path, backup_path)
                sz, mtime, checksum = None, None, None
                try:
                    sz = backup_path.stat().st_size
                except Exception:
                    pass
                try:
                    mtime = int(backup_path.stat().st_mtime)
                except Exception:
                    pass
                try:
                    checksum = _compute_file_checksum(backup_path)
                except Exception:
                    pass
                manifest = {
                    backup_path.name: {
                        "size": sz,
                        "mtime": mtime,
                        "checksum": checksum,
                    }
                }
                manifest_path = backup_path.parent / (
                    backup_path.name + "_manifest.json"
                )
                with open(manifest_path, "w", encoding="utf-8") as mf:
                    json.dump(manifest, mf, separators=(",", ":"))

        if not backup_path.exists():
            raise RuntimeError("Backup creation failed: path not created.")

        if size_bytes == 0:
            if backup_path.is_file():
                size_bytes = backup_path.stat().st_size
            elif backup_path.is_dir():
                size_bytes = sum(
                    f.stat().st_size
                    for root, _, files in scandir_walk(backup_path)
                    for f in (Path(root) / file for file in files)
                    if (Path(root) / file).is_file()
                )

        if backup_path.is_file() and size_bytes == 0:
            raise RuntimeError("Backup file created but is empty.")
        cleanup_old_backups(dest_path, max_versions)

        duration = time.time() - start_time
        msg = f"Backup completed successfully: {backup_path} (with manifest)"
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
        backups = [
            p
            for p in dest_path.iterdir()
            if p.name.startswith("bk_") and (p.is_file() or p.is_dir())
        ]
        if not backups:
            return
        backups_sorted = sorted(
            backups,
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        )
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


def run_backup(mapping, db_path=None):
    """
    Run a backup operation for a specific mapping.
    Returns (success: bool, message: str)
    """
    source = mapping.get("source")
    destination = mapping.get("destination")
    max_versions = mapping.get("maxVersions", 3)
    compression = mapping.get("compression", "none")
    mapping_id = mapping.get("id")
    mapping_uuid = mapping.get("uuid")
    mapping_name = mapping.get("name") or mapping.get("mapping_name")
    if not mapping_name:
        mapping_name = f"{source} to {destination}"
    encrypted = mapping.get("encrypted", False)
    source_checksum = None
    backup_checksum = None

    if not source or not destination:
        logger.error("Invalid mapping configuration: source or destination missing.")
        return False, "Invalid mapping configuration"

    start_time = time.time()

    try:
        success, message, duration, size_bytes, backup_path = perform_backup(
            source,
            destination,
            max_versions,
            compression,
            mapping_id=mapping_id,
            encrypted=encrypted,
        )

        if not success:
            logger.error("perform_backup failed: %s", message)
        else:
            # 1. Verification (must happen BEFORE encryption)
            verify_success = False
            verify_msg = "Verification skipped"
            source_checksum = None
            backup_checksum = None

            try:
                verify_success, verify_msg, source_checksum, backup_checksum = (
                    verification.verify_backup(source, backup_path)
                )
                if not verify_success:
                    logger.warning(
                        "Backup verification failed for %s: %s", backup_path, verify_msg
                    )
                    message += f" (Verification failed: {verify_msg})"
            except Exception as e:
                logger.error("Error during backup verification: %s", e)
                verify_msg = f"Verification error: {str(e)}"

            # 2. Encryption (if enabled)
            if encrypted:
                try:
                    cryptor = Cryptor(
                        mapping_uuid=mapping_uuid, mapping_name=mapping_name
                    )
                    if not cryptor.has_key:
                        logger.info(
                            "No key found for mapping %s, generating one...",
                            mapping_name,
                        )
                        cryptor.key = Cryptor.generate_random_key()
                        # cryptor.encrypt will call _set_key_in_keyring

                    encrypted_backup_path = cryptor.encrypt(backup_path)
                    if encrypted_backup_path:
                        backup_path = encrypted_backup_path
                        try:
                            size_bytes = os.path.getsize(backup_path)
                        except Exception:
                            pass
                        message = f"Backup completed and encrypted: {backup_path}"
                    else:
                        success = False
                        message = "Encryption failed at the cryptor level"
                except Exception as e:
                    logger.error("Encryption failed for %s: %s", backup_path, e)
                    success = False
                    message = f"Encryption failed: {str(e)}"

            # 3. Cleanup (only if everything succeeded)
            if success:
                cleanup_old_backups(destination, max_versions)

    except Exception as e:
        logger.error("run_backup raised an exception: %s", e)
        success = False
        message = f"Backup process failed: {str(e)}"
        duration = time.time() - start_time
        size_bytes = 0
        backup_path = None

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
                db_path=db_path,
            )

            if history_id and success:
                try:
                    verification.save_verification_result(
                        backup_history_id=history_id,
                        checksum_type="md5",
                        source_checksum=source_checksum,
                        backup_checksum=backup_checksum,
                        verification_status=verify_success,
                        verification_msg=verify_msg,
                        db_path=db_path,
                    )
                except Exception as ve:
                    logger.error("Error saving verification result: %s", ve)
        except Exception as e:
            logger.error("Error in database history logic: %s", e)
    else:
        try:
            config = load_config()
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            config = {}
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


def run_backups_parallel(mappings, max_workers=4):
    """
    Run multiple backup operations in parallel using ThreadPoolExecutor.
    Returns list of (success, message) tuples in the same order as mappings.
    """
    futures = []
    results = [None] * len(mappings)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, mapping in enumerate(mappings):
            futures.append((idx, executor.submit(run_backup, mapping)))
        for idx, fut in futures:
            try:
                result = fut.result()
                results[idx] = result
            except Exception as e:
                logger.error(
                    "Parallel backup error for mapping %r: %s", mappings[idx], e
                )
                results[idx] = (False, f"Parallel backup error: {e}")
    logger.info(
        "Completed parallel backups: %d/%d succeeded.",
        sum(1 for r in results if r and r[0]),
        len(results),
    )
    return results
