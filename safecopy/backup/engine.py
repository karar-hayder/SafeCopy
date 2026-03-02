import json
import logging
import os
import shutil
import tarfile
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from safecopy.backup.cryptor import Cryptor
from safecopy.backup.dtos import BackupConfig, BackupJob
from safecopy.backup.enums import BackupJobStatus, BackupStatus, CompressionType
from safecopy.backup.manifest import (
    MANIFEST_FILENAME,
    embed_in_tar,
    embed_in_zip,
    generate_for_directory,
    generate_for_tar,
    generate_for_zip,
)
from safecopy.utils.filesUtils import atomic_file_rename, sanitize_filename


class BackupEngine:
    def __init__(self, config: BackupConfig):
        self.config = config
        self.source: Path = Path(config.source)  # Could be a file or a dir
        self.destination: Path = Path(config.destination)
        self.encrypted: bool = config.encrypted
        self.passwd: str = config.passwd
        self.compression: CompressionType = config.compression
        self.max_versions: int = config.max_versions

        self.job_status: BackupJobStatus = BackupJobStatus()

        self.backup_path: Path = None
        self.backup_path_encrypted: Path = None
        self.temp_file: Path = None
        self.temp_dir: Path = None
        self.cryptor: Cryptor = None
        if self.encrypted:
            self.cryptor = Cryptor(self.config.uuid)

        self.logger = logging.getLogger("backup_engine")

    def run(self):
        if not self.source or not self.destination:
            raise ValueError("Source or destination not specified")

        self._backup_job()

        duration = self.job_status.end_time - self.job_status.start_time
        size_bytes = (
            self.backup_path.stat().st_size
            if self.backup_path and self.backup_path.exists()
            else 0
        )
        return self.job_status.status, self.job_status.message, duration, size_bytes

    def _backup_job(self):
        """
        Runs the backup job.
        """
        self.job_status = BackupJobStatus()
        self.job_status.start_time = time.time()
        self.job_status.status = BackupStatus.PENDING
        self.job_status.progress = 0.0
        self.job_status.id = str(uuid.uuid4())
        self.job_status.message = "Backup job started"
        self.job_status.created_at = datetime.now()
        self.job_status.updated_at = datetime.now()

        self.logger.info("Starting backup job")
        self._backup()

        if self.encrypted:
            self.logger.info("Encrypting backup files")
            self._encrypt_files()

        self.job_status.end_time = time.time()
        self.job_status.updated_at = datetime.now()
        self.logger.info("Backup job completed")

    def _generate_backup_name(self):
        """
        Generates a backup name.
        Format: safe_copy_<source_name>_<timestamp>_<uuid>_<compression><ext>
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        src = sanitize_filename(self.source.name)

        uuid_str = self.config.uuid[:8]
        compression = self.compression.value_name
        compression_ext = self.compression.extension

        name_parts = ["safe_copy", src, timestamp, uuid_str, compression]
        name = "_".join(name_parts)

        self.backup_path = Path(self.destination / f"{name}{compression_ext}")
        self.temp_file = Path(self.destination / f"{name}.tmp")
        self.temp_dir = Path(self.destination / f"{name}.tmpdir")

    def _backup(self):
        """
        Backs up the source to the destination.
        """
        if not self.source.exists():
            raise FileNotFoundError(f"Source path {self.source} does not exist")

        if not self.destination.exists():
            self.destination.mkdir(parents=True, exist_ok=True)

        self._generate_backup_name()

        # Gather files and compute total size
        files_to_backup = []
        total_size = 0
        if self.source.is_file():
            files_to_backup.append(self.source)
            total_size = self.source.stat().st_size
        else:
            for root, _, files in os.walk(self.source):
                for file_name in files:
                    file_path = Path(root) / file_name
                    if file_path.is_file() and not os.path.islink(file_path):
                        files_to_backup.append(file_path)
                        total_size += file_path.stat().st_size

        try:
            self.job_status.status = BackupStatus.RUNNING
            self.progress = 0.0

            if not files_to_backup:
                raise ValueError("Source has no files to back up")

            if self.compression == CompressionType.NONE:
                self._handle_backup_none(files_to_backup, total_size)
            elif self.compression == CompressionType.ZIP:
                self._handle_backup_zip(files_to_backup, total_size)
            elif self.compression == CompressionType.TAR:
                self._handle_backup_tar(files_to_backup, total_size)

            self._guard_empty_backup()
            self._cleanup_files()
            self._clean_old_backups()
            self.progress = 1.0
            self.job_status.status = BackupStatus.SUCCESS
        except Exception as e:
            self.logger.error("Backup failed", exc_info=True)
            self._cleanup_files(with_backup=True)
            self.job_status.status = BackupStatus.FAILED
            self.job_status.message = str(e)

    # ------------------------------------------------------------------
    # Backup handlers
    # ------------------------------------------------------------------

    def _handle_backup_none(self, files_to_backup: list[Path], total_size: int):
        if self.source.is_file():
            self._copy_raw(self.source, self.temp_file, total_size, 0)
            atomic_file_rename(self.temp_file, self.backup_path)

            # Sidecar manifest next to the plain backup file
            manifest = generate_for_directory(self.source.parent)
            key = self.source.name
            sidecar = self.backup_path.parent / (
                self.backup_path.name + "_manifest.json"
            )
            entry = manifest.get(key) or manifest.get(key.replace("\\", "/"))
            sidecar.write_text(
                json.dumps({key: entry}, separators=(",", ":")),
                encoding="utf-8",
            )
        else:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            copied_size = 0
            for file_path in files_to_backup:
                rel_path = file_path.relative_to(self.source)
                dest_path = self.temp_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                copied_size = self._copy_raw(
                    file_path, dest_path, total_size, copied_size
                )

            atomic_file_rename(self.temp_dir, self.backup_path)

            # Guard runs here, before manifest is written, so only real files count
            self._guard_empty_backup()

            # Manifest inside the backup directory
            manifest = generate_for_directory(self.backup_path)
            manifest_path = self.backup_path / MANIFEST_FILENAME
            manifest_path.write_text(
                json.dumps(manifest, separators=(",", ":")),
                encoding="utf-8",
            )

    def _handle_backup_zip(self, files_to_backup: list[Path], total_size: int):
        with zipfile.ZipFile(
            self.temp_file, "w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            copied_size = 0
            for file_path in files_to_backup:
                arcname = (
                    file_path.name
                    if self.source.is_file()
                    else str(file_path.relative_to(self.source)).replace("\\", "/")
                )
                zf.write(file_path, arcname=arcname)
                copied_size += file_path.stat().st_size
                self.progress = (
                    min(1.0, copied_size / total_size) if total_size else 1.0
                )

        atomic_file_rename(self.temp_file, self.backup_path)

        # Generate manifest and embed it into the ZIP
        manifest = generate_for_zip(self.backup_path)
        embed_in_zip(self.backup_path, manifest)

    def _handle_backup_tar(self, files_to_backup: list[Path], total_size: int):
        with tarfile.open(self.temp_file, "w:gz") as tf:
            copied_size = 0
            for file_path in files_to_backup:
                arcname = (
                    file_path.name
                    if self.source.is_file()
                    else str(file_path.relative_to(self.source)).replace("\\", "/")
                )
                tf.add(file_path, arcname=arcname)
                copied_size += file_path.stat().st_size
                self.progress = (
                    min(1.0, copied_size / total_size) if total_size else 1.0
                )

        atomic_file_rename(self.temp_file, self.backup_path)

        # Generate manifest and embed it into the TAR
        manifest = generate_for_tar(self.backup_path)
        embed_in_tar(self.backup_path, manifest)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _copy_raw(
        self, src: Path, dest: Path, total_size: int, start_copied: int
    ) -> int:
        copied = start_copied
        with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
            while chunk := fsrc.read(50 * 1024 * 1024):  # 50 MB chunks
                fdst.write(chunk)
                copied += len(chunk)
                if total_size > 0:
                    self.progress = min(1.0, copied / total_size)
        return copied

    def _guard_empty_backup(self):
        """Raise if the resulting backup is empty."""
        if not self.backup_path or not self.backup_path.exists():
            raise RuntimeError("Backup path was not created")

        if self.backup_path.is_file() and self.backup_path.stat().st_size == 0:
            raise RuntimeError(f"Backup file is empty: {self.backup_path}")

        if self.backup_path.is_dir() and not any(self.backup_path.iterdir()):
            raise RuntimeError(f"Backup directory is empty: {self.backup_path}")

    def _cleanup_files(self, with_backup: bool = False):
        if self.temp_file and self.temp_file.exists():
            self.temp_file.unlink()
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        if with_backup and self.backup_path and self.backup_path.exists():
            if self.backup_path.is_file():
                self.backup_path.unlink()
            else:
                shutil.rmtree(self.backup_path)

    def _clean_old_backups(self):
        try:
            pattern = f"safe_copy_*_{self.config.uuid[:8]}_*"
            backups = list(self.destination.glob(pattern))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for backup in backups[self.config.max_versions :]:
                try:
                    if backup.is_file():
                        backup.unlink()
                    else:
                        shutil.rmtree(backup)
                except Exception as e:
                    self.logger.error("Failed to remove old backup %s: %s", backup, e)
        except Exception as e:
            self.logger.error("Failed to clean old backups: %s", e)

    def _encrypt_files(self):
        """Encrypts the backup file."""
        result = self.cryptor.encrypt(self.backup_path)
        if result["success"]:
            self.backup_path_encrypted = Path(result["backup_path"])
        else:
            raise Exception(result["message"])

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def status(self):
        return self.job_status.status

    @status.setter
    def status(self, value: BackupStatus):
        self.job_status.status = value
        self.job_status.updated_at = datetime.now()

    @property
    def message(self):
        return self.job_status.message

    @property
    def progress(self):
        return self.job_status.progress

    @progress.setter
    def progress(self, value: float | int):
        self.job_status.progress = round(value, 2)
        self.job_status.updated_at = datetime.now()

    @property
    def start_time(self):
        return self.job_status.start_time

    @property
    def end_time(self):
        return self.job_status.end_time

    @property
    def created_at(self):
        return self.job_status.created_at

    @property
    def updated_at(self):
        return self.job_status.updated_at

    @property
    def job(self):
        return BackupJob(
            id=self.job_status.id,
            config=self.config,
            status=self.job_status.status,
            message=self.job_status.message,
            progress=self.job_status.progress,
            created_at=self.job_status.created_at,
            updated_at=self.job_status.updated_at,
        )
