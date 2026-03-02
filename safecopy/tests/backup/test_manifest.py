"""
Tests for safecopy.backup.manifest

Covers:
- generate_for_directory
- generate_for_zip
- generate_for_tar
- embed_in_zip
- embed_in_tar
- load_manifest
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
    load_manifest,
)


@pytest.fixture()
def src_dir(tmp_path: Path) -> Path:
    """A small source directory tree with known files."""
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("world")
    return tmp_path


# ---------------------------------------------------------------------------
# generate_for_directory
# ---------------------------------------------------------------------------


def test_generate_for_directory_keys(src_dir):
    manifest = generate_for_directory(src_dir)
    assert "a.txt" in manifest
    assert "sub/b.txt" in manifest


def test_generate_for_directory_has_checksum(src_dir):
    manifest = generate_for_directory(src_dir)
    for entry in manifest.values():
        assert entry["checksum"] is not None
        assert entry["size"] is not None


# ---------------------------------------------------------------------------
# generate_for_zip + embed_in_zip + load_manifest (zip)
# ---------------------------------------------------------------------------


def test_embed_and_load_zip(src_dir, tmp_path):
    zip_path = tmp_path / "test.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(src_dir / "a.txt", arcname="a.txt")
        zf.write(src_dir / "sub" / "b.txt", arcname="sub/b.txt")

    manifest = generate_for_zip(zip_path)
    assert "a.txt" in manifest
    assert "sub/b.txt" in manifest

    embed_in_zip(zip_path, manifest)

    loaded = load_manifest(zip_path)
    assert loaded is not None
    assert "a.txt" in loaded


def test_generate_for_zip_skips_existing_manifest(src_dir, tmp_path):
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(src_dir / "a.txt", arcname="a.txt")
        zf.writestr(MANIFEST_FILENAME, "{}")  # pre-existing manifest

    manifest = generate_for_zip(zip_path)
    assert MANIFEST_FILENAME not in manifest


# ---------------------------------------------------------------------------
# generate_for_tar + embed_in_tar + load_manifest (tar)
# ---------------------------------------------------------------------------


def test_embed_and_load_tar(src_dir, tmp_path):
    tar_path = tmp_path / "test.tar.gz"

    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(src_dir / "a.txt", arcname="a.txt")
        tf.add(src_dir / "sub" / "b.txt", arcname="sub/b.txt")

    manifest = generate_for_tar(tar_path)
    assert "a.txt" in manifest
    assert "sub/b.txt" in manifest

    embed_in_tar(tar_path, manifest)

    loaded = load_manifest(tar_path)
    assert loaded is not None
    assert "a.txt" in loaded


# ---------------------------------------------------------------------------
# load_manifest — plain directory
# ---------------------------------------------------------------------------


def test_load_manifest_directory(src_dir):
    manifest = generate_for_directory(src_dir)
    manifest_file = src_dir / MANIFEST_FILENAME
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    loaded = load_manifest(src_dir)
    assert loaded is not None
    assert set(loaded.keys()) == set(manifest.keys())


# ---------------------------------------------------------------------------
# load_manifest — sidecar .bak
# ---------------------------------------------------------------------------


def test_load_manifest_sidecar(tmp_path):
    bak_file = tmp_path / "backup.bak"
    bak_file.write_bytes(b"data")
    sidecar = tmp_path / "backup.bak_manifest.json"
    sidecar.write_text(json.dumps({"backup.bak": {"size": 4, "checksum": "abc"}}))

    loaded = load_manifest(bak_file)
    assert loaded is not None
    assert "backup.bak" in loaded


# ---------------------------------------------------------------------------
# load_manifest — missing manifest
# ---------------------------------------------------------------------------


def test_load_manifest_missing_returns_none(tmp_path):
    bak_file = tmp_path / "orphan.bak"
    bak_file.write_bytes(b"x")
    assert load_manifest(bak_file) is None
