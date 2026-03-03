"""
Tests for BackupEngine

Covers:
- Plain file backup: .bak + sidecar manifest
- Plain dir backup: copied dir + manifest.json inside
- ZIP backup: manifest.json embedded in ZIP
- TAR backup: manifest.json embedded in TAR
- Empty backup guard (source is an empty dir)
"""

import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from safecopy.backup.dtos import BackupConfig
from safecopy.backup.engine import BackupEngine
from safecopy.backup.enums import CompressionType
from safecopy.backup.manifest import MANIFEST_FILENAME, load_manifest


def _make_config(tmp_path: Path, src: Path, compression: str = "none") -> BackupConfig:
    dst = tmp_path / "dst"
    dst.mkdir()
    return BackupConfig(
        uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        user_uuid="ffffffff-0000-1111-2222-333333333333",
        source=str(src),
        destination=str(dst),
        encrypted=False,
        passwd="",
        compression=CompressionType[compression.upper()],
        max_versions=3,
    )


@pytest.fixture()
def src_dir(tmp_path: Path) -> Path:
    src = tmp_path / "source"
    src.mkdir()
    (src / "file1.txt").write_text("content one")
    (src / "sub").mkdir()
    (src / "sub" / "file2.txt").write_text("content two")
    return src


@pytest.fixture()
def src_file(tmp_path: Path) -> Path:
    f = tmp_path / "single.txt"
    f.write_text("single file content")
    return f


# ---------------------------------------------------------------------------
# Plain file backup
# ---------------------------------------------------------------------------


def test_plain_file_backup_creates_bak(src_file, tmp_path):
    config = _make_config(tmp_path, src_file, compression="none")
    engine = BackupEngine(config)
    engine.run()

    dst = Path(config.destination)
    # NONE compression produces 'safe_copy_<name>_<ts>_<uuid>_none' with no extension.
    # Exclude the sidecar _manifest.json (which also contains 'safe_copy' in its name).
    backup_files = [
        p
        for p in dst.iterdir()
        if p.is_file()
        and "safe_copy" in p.name
        and not p.name.endswith("_manifest.json")
    ]
    assert (
        len(backup_files) == 1
    ), f"Expected a plain backup file, got: {list(dst.iterdir())}"
    assert backup_files[0].stat().st_size > 0


def test_plain_file_backup_has_sidecar_manifest(src_file, tmp_path):
    config = _make_config(tmp_path, src_file, compression="none")
    BackupEngine(config).run()

    dst = Path(config.destination)
    # Sidecar is '<backup_name>_manifest.json'
    backup_file = next(
        p
        for p in dst.iterdir()
        if p.is_file()
        and "safe_copy" in p.name
        and not p.name.endswith("_manifest.json")
    )
    manifest = load_manifest(backup_file)

    assert manifest is not None
    assert len(manifest) == 1


# ---------------------------------------------------------------------------
# Plain dir backup
# ---------------------------------------------------------------------------


def test_plain_dir_backup_creates_dir(src_dir, tmp_path):
    config = _make_config(tmp_path, src_dir, compression="none")
    BackupEngine(config).run()

    dst = Path(config.destination)
    backup_dirs = [p for p in dst.iterdir() if p.is_dir()]
    assert len(backup_dirs) == 1


def test_plain_dir_backup_has_manifest_inside(src_dir, tmp_path):
    config = _make_config(tmp_path, src_dir, compression="none")
    BackupEngine(config).run()

    dst = Path(config.destination)
    backup_dir = next(p for p in dst.iterdir() if p.is_dir())
    manifest = load_manifest(backup_dir)

    assert manifest is not None
    keys = set(manifest.keys())
    assert "file1.txt" in keys or any("file1.txt" in k for k in keys)


# ---------------------------------------------------------------------------
# ZIP backup
# ---------------------------------------------------------------------------


def test_zip_backup_creates_zip(src_dir, tmp_path):
    config = _make_config(tmp_path, src_dir, compression="zip")
    BackupEngine(config).run()

    dst = Path(config.destination)
    zips = list(dst.glob("*.zip"))
    assert len(zips) == 1


def test_zip_backup_has_embedded_manifest(src_dir, tmp_path):
    config = _make_config(tmp_path, src_dir, compression="zip")
    BackupEngine(config).run()

    dst = Path(config.destination)
    zip_path = next(dst.glob("*.zip"))

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert MANIFEST_FILENAME in zf.namelist()
        data = json.loads(zf.read(MANIFEST_FILENAME))
        assert len(data) >= 2  # file1.txt + sub/file2.txt


# ---------------------------------------------------------------------------
# TAR backup
# ---------------------------------------------------------------------------


def test_tar_backup_creates_tar_gz(src_dir, tmp_path):
    config = _make_config(tmp_path, src_dir, compression="tar")
    BackupEngine(config).run()

    dst = Path(config.destination)
    tars = list(dst.glob("*.tar.gz"))
    assert len(tars) == 1


def test_tar_backup_has_embedded_manifest(src_dir, tmp_path):
    config = _make_config(tmp_path, src_dir, compression="tar")
    BackupEngine(config).run()

    dst = Path(config.destination)
    tar_path = next(dst.glob("*.tar.gz"))

    with tarfile.open(tar_path, "r:gz") as tf:
        names = tf.getnames()
        assert MANIFEST_FILENAME in names


# ---------------------------------------------------------------------------
# Unique Filenames & Job IDs
# ---------------------------------------------------------------------------


def test_backup_filenames_include_job_id(src_file, tmp_path):
    config = _make_config(tmp_path, src_file, compression="none")
    engine = BackupEngine(config)
    engine.run()

    dst = Path(config.destination)
    job_id = engine.job_status.id[:8]
    backup_files = list(dst.glob(f"*_{job_id}_*"))
    assert len(backup_files) >= 1
    assert job_id in backup_files[0].name


def test_concurrent_backups_unique_paths(src_file, tmp_path):
    config = _make_config(tmp_path, src_file, compression="none")
    engine1 = BackupEngine(config)
    engine2 = BackupEngine(config)

    # They should have different job IDs even if created almost at once
    engine1._backup_job()
    engine2._backup_job()

    assert engine1.job_status.id != engine2.job_status.id
    assert engine1.backup_path != engine2.backup_path
    assert engine1.backup_path.exists()
    assert engine2.backup_path.exists()


# ---------------------------------------------------------------------------
# Empty backup guard
# ---------------------------------------------------------------------------


def test_empty_dir_backup_marks_failed(tmp_path):
    src = tmp_path / "empty_source"
    src.mkdir()
    config = _make_config(tmp_path, src, compression="none")
    engine = BackupEngine(config)
    engine.run()

    from safecopy.backup.enums import BackupStatus

    assert engine.status == BackupStatus.FAILED
