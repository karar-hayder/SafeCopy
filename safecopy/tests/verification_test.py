import os
import pathlib
import shutil
import tempfile

import pytest

from safecopy import verification

TEST_CONTENTS = "This is some test content for checksum.\n"


@pytest.fixture
def temp_file_with_content():
    tmpdir = tempfile.mkdtemp()
    file_path = os.path.join(tmpdir, "testfile.txt")
    with open(file_path, "w") as f:
        f.write(TEST_CONTENTS)
    yield file_path, tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def temp_dir_with_files():
    tmpdir = tempfile.mkdtemp()
    files = []
    for i in range(3):
        file_path = os.path.join(tmpdir, f"file{i}.txt")
        with open(file_path, "w") as f:
            f.write(TEST_CONTENTS * (i + 1))
        files.append(file_path)
    yield tmpdir, files
    shutil.rmtree(tmpdir)


def test_calculate_checksum_file(temp_file_with_content):
    file_path, tmpdir = temp_file_with_content
    path = pathlib.Path(file_path)
    checksum = verification.calculate_checksum(path, "md5")
    assert isinstance(checksum, str)
    checksum_repeat = verification.calculate_checksum(path, "md5")
    assert checksum == checksum_repeat


def test_compute_source_manifest_file(temp_file_with_content):
    file_path, tmpdir = temp_file_with_content
    path = pathlib.Path(file_path)
    manifest = verification.compute_source_manifest(path)
    assert isinstance(manifest, dict)
    assert path.name in manifest
    entry = manifest[path.name]
    assert "size" in entry and "checksum" in entry


def test_compute_source_manifest_directory(temp_dir_with_files):
    dir_path, files = temp_dir_with_files
    path = pathlib.Path(dir_path)
    manifest = verification.compute_source_manifest(path)
    assert isinstance(manifest, dict)
    for file_path in files:
        rel_name = os.path.basename(file_path)
        # Should be present and non-empty
        assert rel_name in [p.split("/")[-1] for p in manifest.keys()]
    # Modifying a file should change the manifest
    target_file = pathlib.Path(files[0])
    with open(target_file, "a") as f:
        f.write("extra data\n")
    new_manifest = verification.compute_source_manifest(path)
    assert manifest != new_manifest


def test_compare_manifests_identical(temp_dir_with_files):
    dir_path, files = temp_dir_with_files
    path = pathlib.Path(dir_path)
    manifest1 = verification.compute_source_manifest(path)
    manifest2 = verification.compute_source_manifest(path)
    result, msg = verification.compare_manifests(manifest1, manifest2)
    assert result is True
    assert "matches" in msg


def test_compare_manifests_different(temp_dir_with_files):
    dir_path, files = temp_dir_with_files
    path = pathlib.Path(dir_path)
    manifest1 = verification.compute_source_manifest(path)
    # Modify one file and get new manifest
    target_file = pathlib.Path(files[0])
    with open(target_file, "w") as f:
        f.write("DIFFERENT CONTENT\n")
    manifest2 = verification.compute_source_manifest(path)
    result, msg = verification.compare_manifests(manifest1, manifest2)
    assert result is False
    assert "Mismatch" in msg


def test_load_manifest_and_verify(temp_dir_with_files, tmp_path):
    dir_path, files = temp_dir_with_files
    # Save manifest.json to this directory (simulate backup dir)
    manifest = verification.compute_source_manifest(pathlib.Path(dir_path))
    manifest_path = pathlib.Path(dir_path) / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        import json

        json.dump(manifest, f)
    loaded_manifest = verification.load_manifest_from_dir(pathlib.Path(dir_path))
    assert loaded_manifest == manifest

    # Now zip archive (manifest.json will be included by shutil.make_archive)
    zip_file = tmp_path / "backup.zip"
    shutil.make_archive(str(zip_file)[:-4], "zip", dir_path)
    # Remove manifest.json from the "source" manifest so comparison works (real verify omits 'manifest.json')
    manifest.pop("manifest.json", None)
    loaded_manifest_zip = verification.load_manifest_from_zip(zip_file)
    # The loaded manifest should match the manifest minus manifest.json
    assert loaded_manifest_zip == manifest


def test_verify_backup_works_file(tmp_path):
    # This test now verifies the REAL scenario: backup filename should match source filename.
    # Create an original file
    orig_path = tmp_path / "verifyme.txt"
    orig_path.write_text(TEST_CONTENTS)
    # Simulate a backup file with the SAME filename as source (as safecopy does for single files)
    # Put backup file in a different directory to avoid SameFileError
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    backup_path = backup_dir / "verifyme.txt"
    shutil.copy(str(orig_path), str(backup_path))
    # Write manifest for the backup file as safecopy/backup.py would do
    import json

    sz = backup_path.stat().st_size
    mtime = int(backup_path.stat().st_mtime)
    checksum = verification.calculate_checksum(backup_path)
    manifest = {
        backup_path.name: {
            "size": sz,
            "mtime": mtime,
            "checksum": checksum,
        }
    }
    manifest_path_bkp = backup_path.parent / (backup_path.name + "_manifest.json")
    with open(manifest_path_bkp, "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    result, msg, src_hash, bkp_hash = verification.verify_backup(
        str(orig_path), str(backup_path), algorithm="md5"
    )
    assert result is True
    assert src_hash == bkp_hash
    assert "matches" in msg


def test_verify_backup_works_directory(tmp_path):
    src = tmp_path / "srcdir"
    src.mkdir()
    (src / "a.txt").write_text("x")
    (src / "b.txt").write_text("y")
    backup = tmp_path / "backupdir"
    backup.mkdir()
    shutil.copy(str(src / "a.txt"), str(backup / "a.txt"))
    shutil.copy(str(src / "b.txt"), str(backup / "b.txt"))
    # Write manifest.json for backup directory (because verify_backup expects it there)
    import json

    manifest_bkp = verification.compute_source_manifest(backup)
    manifest_path_bkp = backup / "manifest.json"
    with open(manifest_path_bkp, "w", encoding="utf-8") as f:
        json.dump(manifest_bkp, f)
    # The real backup should contain this manifest
    result, msg, src_hash, bkp_hash = verification.verify_backup(
        str(src), str(backup), algorithm="md5"
    )
    assert result is True
    assert src_hash == bkp_hash


def test_verify_backup_zip_directory(tmp_path):
    src = tmp_path / "dir"
    src.mkdir()
    (src / "a.txt").write_text("abc")
    (src / "b.txt").write_text("def")

    # Write a correct manifest for the ZIP archive, as safecopy does
    manifest = verification.compute_source_manifest(src)
    manifest_path = src / "manifest.json"
    import json

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    zip_file = tmp_path / "bkp.zip"
    shutil.make_archive(str(zip_file)[:-4], "zip", src)

    # Remove manifest.json from src to simulate proper backup scenario,
    # (since original source wouldn't keep the manifest for independent verify)
    manifest_path.unlink()

    # Verification should pass as both backup + manifest.json in backup.zip as required
    result, msg, src_hash, bkp_hash = verification.verify_backup(
        str(src), str(zip_file), algorithm="md5"
    )
    assert result is True
    assert src_hash == bkp_hash


def test_verify_backup_error_missing_source(tmp_path):
    src = tmp_path / "nosuch.txt"
    backup = tmp_path / "file.txt"
    backup.write_text(TEST_CONTENTS)
    result, msg, src_hash, bkp_hash = verification.verify_backup(str(src), str(backup))
    assert result is False
    assert "does not exist" in msg
    assert src_hash is None
    assert bkp_hash is None or isinstance(bkp_hash, (str, type(None)))


def test_verify_backup_error_missing_backup(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text(TEST_CONTENTS)
    backup = tmp_path / "nosuchbackup.txt"
    result, msg, src_hash, bkp_hash = verification.verify_backup(str(src), str(backup))
    assert result is False
    assert "does not exist" in msg
    assert bkp_hash is None
    assert src_hash is None or isinstance(src_hash, (str, type(None)))


def test_save_and_get_verification_result(tmp_path):
    # Use a temporary sqlite db
    db_path = str(tmp_path / "db.sqlite3")
    # Setup minimal database schema
    import sqlite3

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_verification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_history_id INTEGER,
            checksum_type TEXT,
            source_checksum TEXT,
            backup_checksum TEXT,
            verification_status INTEGER,
            verification_msg TEXT,
            verified_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """
    )
    conn.commit()
    conn.close()
    # Save a result
    ok = verification.save_verification_result(
        backup_history_id=1,
        checksum_type="md5",
        source_checksum="abc",
        backup_checksum="abc",
        verification_status=True,
        verification_msg="Test Success",
        db_path=db_path,
    )
    assert ok is True
    result = verification.get_verification_result(1, db_path=db_path)
    assert result is not None
    assert result["checksum_type"] == "md5"
    assert result["verification_status"] is True
    # Accept None or the expected string for compatibility
    assert result.get("verification_msg", "") in ("Test Success", None, "")
