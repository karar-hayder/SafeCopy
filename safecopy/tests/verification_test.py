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


def test_calculate_directory_checksum(temp_dir_with_files):
    dir_path, files = temp_dir_with_files
    path = pathlib.Path(dir_path)
    checksum = verification.calculate_directory_checksum(path, "md5")
    assert isinstance(checksum, str)
    # Modifying a file should alter the checksum
    test_file = pathlib.Path(files[0])
    with open(test_file, "a") as f:
        f.write("extra data\n")
    new_checksum = verification.calculate_directory_checksum(path, "md5")
    assert checksum != new_checksum


def test_extract_archive_to_temp_and_verify(tmp_path):
    # Create a directory and zip it
    dir_path = tmp_path / "arc_dir"
    dir_path.mkdir()
    (dir_path / "a.txt").write_text("abc")
    (dir_path / "b.txt").write_text("def")
    zip_path = tmp_path / "archive.zip"
    shutil.make_archive(str(zip_path)[:-4], "zip", str(dir_path))
    # Now extract using internal function and check files are present
    temp_dir_obj = verification._extract_archive_to_temp(zip_path)
    assert temp_dir_obj is not None
    extract_dir = pathlib.Path(temp_dir_obj.name)
    files = list(extract_dir.iterdir())
    assert any(f.name == "a.txt" for f in files)
    assert any(f.name == "b.txt" for f in files)
    temp_dir_obj.cleanup()


def test_verify_backup_file_to_file(temp_file_with_content):
    file_path, tmpdir = temp_file_with_content
    # Copy file to backup location
    backup_path = os.path.join(tmpdir, "backup.txt")
    shutil.copy(file_path, backup_path)
    result, src_hash, dest_hash = verification.verify_backup(
        file_path, backup_path, "md5"
    )
    assert result is True
    # Confirm that hashes match
    assert src_hash == dest_hash


def test_verify_backup_directory_to_directory(temp_dir_with_files):
    dir_path, files = temp_dir_with_files
    # Make backup by copying directory
    tmp_backup = tempfile.mkdtemp()
    for f in files:
        shutil.copy(f, tmp_backup)
    result, src_hash, dest_hash = verification.verify_backup(
        dir_path, tmp_backup, "md5"
    )
    shutil.rmtree(tmp_backup)
    assert result is True
    assert src_hash == dest_hash


def test_verify_backup_directory_to_zip_archive(temp_dir_with_files):
    dir_path, files = temp_dir_with_files
    zip_fd, zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(zip_fd)
    shutil.make_archive(zip_path[:-4], "zip", dir_path)
    # verify_backup should extract archive and compare checksums
    result, src_hash, backup_hash = verification.verify_backup(
        dir_path, zip_path, "md5"
    )
    os.remove(zip_path)
    assert result is True
    assert src_hash == backup_hash


def test_verify_backup_error_missing_source(temp_file_with_content):
    file_path, tmpdir = temp_file_with_content
    missing_path = os.path.join(tmpdir, "no-such.txt")
    backup_path = file_path
    result, src_hash, dest_hash = verification.verify_backup(
        missing_path, backup_path, "md5"
    )
    assert result is False
    assert src_hash is None


def test_verify_backup_error_missing_backup(temp_file_with_content):
    file_path, tmpdir = temp_file_with_content
    missing_path = os.path.join(tmpdir, "no-such-backup.txt")
    result, src_hash, dest_hash = verification.verify_backup(
        file_path, missing_path, "md5"
    )
    assert result is False
    assert dest_hash is None


def test_save_and_get_verification_result(tmp_path):
    # Use a temporary sqlite db
    db_path = str(tmp_path / "db.sqlite3")
    # Setup minimal database schema
    import sqlite3

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE backup_verification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_history_id INTEGER,
            checksum_type TEXT,
            source_checksum TEXT,
            backup_checksum TEXT,
            verification_status INTEGER,
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
        db_path=db_path,
    )
    assert ok is True
    result = verification.get_verification_result(1, db_path=db_path)
    assert result is not None
    assert result["checksum_type"] == "md5"
    assert result["verification_status"] is True
