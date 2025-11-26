import importlib
import logging
import os
import pathlib
import shutil
import tempfile

try:
    import pytest
except ImportError:  # noqa: W0611  # Show a warning if pytest is missing for linters
    pytest = None  # type: ignore


@pytest.fixture
def temp_source_dir():
    """
    Fixture to create a temporary source directory with test files.
    """
    tmpdir = tempfile.mkdtemp()
    files = []
    for i in range(2):
        file_path = os.path.join(tmpdir, f"file{i}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"line {i}\n" * (i + 1))
        files.append(file_path)
    yield tmpdir, files
    shutil.rmtree(tmpdir)


@pytest.fixture
def temp_dest_dir():
    """
    Fixture to create a temporary destination directory.
    """
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.mark.parametrize("compression", ["none", "zip", "tar"])
def test_perform_backup_creates_backup_and_enforces_max_versions(
    temp_source_dir, temp_dest_dir, compression
):
    """
    Test that perform_backup handles creation, retention, and naming for different compressions.
    """
    import time

    logger = logging.getLogger(
        "test_perform_backup_creates_backup_and_enforces_max_versions"
    )
    src_dir, _files = temp_source_dir
    dst_dir = temp_dest_dir

    from safecopy import backup

    backup_paths = []
    for i in range(3):
        logger.info(
            "Starting backup %d with compression='%s'...",
            i + 1,
            compression,
        )
        success, msg, _duration, _size_bytes, backup_path = backup.perform_backup(
            src_dir, dst_dir, max_versions=2, compression=compression, mapping_id=i
        )
        logger.info(
            "Backup %d result: success=%r, path=%r, msg=%s",
            i + 1,
            success,
            backup_path,
            msg,
        )
        assert success is True
        assert backup_path is not None
        backup_paths.append(backup_path)

        backup_file = pathlib.Path(backup_path)
        expected_is_dir = compression == "none"
        expected_is_file = not expected_is_dir

        for retries in range(10):
            path_exists = backup_file.exists()
            if expected_is_dir and backup_file.is_dir():
                if any(backup_file.iterdir()):
                    break
            elif expected_is_file and backup_file.is_file():
                if backup_file.stat().st_size > 0:
                    break
            logger.warning(
                "Backup path %s not ready (exists=%r, dir=%r, file=%r), attempt %d/10. Sleeping...",
                str(backup_file),
                path_exists,
                backup_file.is_dir(),
                backup_file.is_file(),
                retries + 1,
            )
            time.sleep(0.15)
        logger.info(
            "Backup path exists: %r (is_dir=%r, is_file=%r), path=%s",
            backup_file.exists(),
            backup_file.is_dir(),
            backup_file.is_file(),
            str(backup_file),
        )

        if expected_is_dir:
            logger.debug("Verifying backup directory at %s", str(backup_file))
            assert (
                backup_file.exists()
                and backup_file.is_dir()
                and any(backup_file.iterdir())
            )
        else:
            logger.debug("Verifying backup file at %s", str(backup_file))
            assert (
                backup_file.exists()
                and backup_file.is_file()
                and backup_file.stat().st_size > 0
            )

    dst_dir_path = pathlib.Path(dst_dir)
    dst_items = list(dst_dir_path.iterdir())
    backup_entries = [entry for entry in dst_items if entry.name.startswith("bk_")]
    logger.info(
        "Contents of backup directory (%s): %r",
        dst_dir,
        [e.name for e in backup_entries],
    )
    assert len(backup_entries) == 2


def test_perform_backup_fails_for_missing_source(temp_dest_dir):
    """
    Test that perform_backup fails gracefully when source is missing.
    """
    dst_dir = temp_dest_dir
    missing_src = "/no/such/directory"
    from safecopy import backup

    success, msg, _duration, _size_bytes, backup_path = backup.perform_backup(
        missing_src, dst_dir, max_versions=2, compression="none"
    )
    assert not success
    assert isinstance(msg, str)
    assert backup_path is None


def test_run_backup_adds_last_action_json(monkeypatch, tmp_path):
    """
    Test that run_backup inserts last action into JSON config when USE_DATABASE is False via environment.
    This verifies that config.load_config()['last_actions'] is updated with a backup result.
    """
    import sys

    config_path = tmp_path / "config.json"
    backup_path = tmp_path / "config.json.bak"

    monkeypatch.setenv("USE_DATABASE", "0")
    monkeypatch.setattr("safecopy.config.CONFIG_FILE", str(config_path), raising=False)
    monkeypatch.setattr(
        "safecopy.config.CONFIG_BACKUP", str(backup_path), raising=False
    )

    if "safecopy.config" in sys.modules:
        del sys.modules["safecopy.config"]
    if "safecopy.backup" in sys.modules:
        del sys.modules["safecopy.backup"]

    import safecopy.config as config

    importlib.reload(config)
    import safecopy.backup as backup

    importlib.reload(backup)

    # Write initial empty config
    with open(config_path, "w", encoding="utf-8") as f:
        import json

        json.dump({"mappings": [], "last_actions": [], "backup_settings": {}}, f)

    # Prepare test source and destination directories/files
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("testcontent", encoding="utf-8")
    dst = tmp_path / "backupdest"
    dst.mkdir()

    mapping = {
        "source": str(src),
        "destination": str(dst),
        "maxVersions": 2,
        "compression": "none",
    }
    success, _msg = backup.run_backup(mapping)
    assert success in (True, False)

    conf = config.load_config()
    assert "last_actions" in conf
    if not conf["last_actions"]:
        import pprint

        pprint.pprint(conf)
    assert isinstance(conf["last_actions"], list)
    assert len(conf["last_actions"]) > 0
    entry = conf["last_actions"][0]
    assert entry["source"] == str(src)
    assert entry["destination"] == str(dst)
    assert isinstance(entry["message"], str)
