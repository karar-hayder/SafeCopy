"""
Tests for safecopy.backup.verification

Covers:
- verify() passes on a freshly created backup (zip, tar, dir, file)
- verify() fails when a file is tampered with
- verify() fails when backup manifest is missing
"""

import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from safecopy.backup.manifest import (
    MANIFEST_FILENAME,
    embed_in_tar,
    embed_in_zip,
    generate_for_directory,
    generate_for_tar,
    generate_for_zip,
)
from safecopy.backup.verification import verify


@pytest.fixture()
def src_dir(tmp_path: Path) -> Path:
    src = tmp_path / "source"
    src.mkdir()
    (src / "hello.txt").write_text("hello world")
    (src / "sub").mkdir()
    (src / "sub" / "data.bin").write_bytes(b"\x00\x01\x02")
    return src


# ---------------------------------------------------------------------------
# ZIP
# ---------------------------------------------------------------------------


def test_verify_zip_passes(src_dir, tmp_path):
    zip_path = tmp_path / "backup.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(src_dir / "hello.txt", arcname="hello.txt")
        zf.write(src_dir / "sub" / "data.bin", arcname="sub/data.bin")

    manifest = generate_for_zip(zip_path)
    embed_in_zip(zip_path, manifest)

    result = verify(src_dir, zip_path)
    assert result.success, result.message


def test_verify_zip_fails_on_tamper(src_dir, tmp_path):
    zip_path = tmp_path / "backup.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(src_dir / "hello.txt", arcname="hello.txt")

    # Embed correct manifest, then modify the source
    manifest = generate_for_zip(zip_path)
    embed_in_zip(zip_path, manifest)
    (src_dir / "hello.txt").write_text("TAMPERED")

    result = verify(src_dir, zip_path)
    assert not result.success


# ---------------------------------------------------------------------------
# TAR
# ---------------------------------------------------------------------------


def test_verify_tar_passes(src_dir, tmp_path):
    tar_path = tmp_path / "backup.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(src_dir / "hello.txt", arcname="hello.txt")
        tf.add(src_dir / "sub" / "data.bin", arcname="sub/data.bin")

    manifest = generate_for_tar(tar_path)
    embed_in_tar(tar_path, manifest)

    result = verify(src_dir, tar_path)
    assert result.success, result.message


# ---------------------------------------------------------------------------
# Plain directory
# ---------------------------------------------------------------------------


def test_verify_dir_passes(src_dir, tmp_path):
    bkp_dir = tmp_path / "backup_dir"
    import shutil

    shutil.copytree(src_dir, bkp_dir)

    manifest = generate_for_directory(bkp_dir)
    (bkp_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest), encoding="utf-8")

    result = verify(src_dir, bkp_dir)
    assert result.success, result.message


# ---------------------------------------------------------------------------
# Missing manifest
# ---------------------------------------------------------------------------


def test_verify_fails_when_no_manifest(src_dir, tmp_path):
    zip_path = tmp_path / "no_manifest.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(src_dir / "hello.txt", arcname="hello.txt")

    result = verify(src_dir, zip_path)
    assert not result.success
    assert "manifest" in result.message.lower()


# ---------------------------------------------------------------------------
# Missing source / backup
# ---------------------------------------------------------------------------


def test_verify_fails_missing_source(tmp_path):
    zip_path = tmp_path / "x.zip"
    zip_path.write_bytes(b"")
    result = verify(tmp_path / "nonexistent", zip_path)
    assert not result.success


def test_verify_fails_missing_backup(src_dir, tmp_path):
    result = verify(src_dir, tmp_path / "ghost.zip")
    assert not result.success
