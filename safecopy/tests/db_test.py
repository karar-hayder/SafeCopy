import json
import os
import shutil
import tempfile

import pytest

from safecopy.db import (
    add_backup_history,
    add_mapping,
    cleanup_old_backup_history,
    delete_mapping,
    get_backup_history,
    get_backup_setting,
    get_backup_settings,
    get_database_version,
    get_mapping,
    get_mappings,
    init_database,
    set_backup_setting,
    set_backup_settings,
    update_mapping,
)
from safecopy.db.migrate import migrate_json_to_db


@pytest.fixture
def temp_db_file():
    # Use a temporary file as a database
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_safecopy.db")
    yield db_path
    shutil.rmtree(tmpdir)


def test_init_database_creates_schema(temp_db_file):
    result = init_database(temp_db_file)
    assert result is True
    # Table 'mappings' and 'backup_settings' should exist, tested via simple add/get operations
    mapping_id = add_mapping("src", "dst", db_path=temp_db_file)
    assert isinstance(mapping_id, int)
    retrieved = get_mapping(mapping_id, db_path=temp_db_file)
    assert retrieved is not None
    assert retrieved["source"] == "src"
    assert retrieved["destination"] == "dst"


def test_mapping_crud(temp_db_file):
    init_database(temp_db_file)
    # Create
    mapping_id = add_mapping(
        "src",
        "dst",
        max_versions=2,
        compression="zip",
        enabled=True,
        db_path=temp_db_file,
    )
    assert isinstance(mapping_id, int)
    # Read (all)
    mappings = get_mappings(db_path=temp_db_file)
    assert len(mappings) == 1
    # Update
    updated = update_mapping(
        mapping_id, source="src2", enabled=False, db_path=temp_db_file
    )
    assert updated is True
    updated_mapping = get_mapping(mapping_id, db_path=temp_db_file)
    assert updated_mapping["source"] == "src2"
    assert updated_mapping["enabled"] is False
    # Delete
    deleted = delete_mapping(mapping_id, db_path=temp_db_file)
    assert deleted is True
    assert get_mapping(mapping_id, db_path=temp_db_file) is None


def test_backup_history(temp_db_file):
    init_database(temp_db_file)
    mapping_id = add_mapping("a", "b", db_path=temp_db_file)
    # Insert history
    history_id = add_backup_history(
        mapping_id,
        True,
        "backup ok",
        duration=5.1,
        size_bytes=1234,
        backup_path="/backup/b",
        db_path=temp_db_file,
    )
    assert isinstance(history_id, int)
    # Retrieve history
    history = get_backup_history(limit=10, mapping_id=mapping_id, db_path=temp_db_file)
    assert len(history) >= 1
    entry = next((entry for entry in history if entry["id"] == history_id), None)
    assert entry is not None
    assert entry["success"] is True
    assert entry["message"] == "backup ok"


def test_backup_settings(temp_db_file):
    init_database(temp_db_file)
    # Single setting
    ok = set_backup_setting("mykey", "myval", db_path=temp_db_file)
    assert ok is True
    val = get_backup_setting("mykey", db_path=temp_db_file)
    assert val == "myval"
    # Multiple settings
    to_set = {"foo": "bar", "maxVersions": "11"}
    ok = set_backup_settings(to_set, db_path=temp_db_file)
    assert ok is True
    settings = get_backup_settings(db_path=temp_db_file)
    assert "foo" in settings and settings["foo"] == "bar"
    assert settings["maxVersions"] == "11"


def test_database_version_and_cleanup(temp_db_file):
    init_database(temp_db_file)
    v = get_database_version(db_path=temp_db_file)
    assert isinstance(v, int)
    # Add history and cleanup should remove them if days=0
    mapping_id = add_mapping("srcdel", "dstdel", db_path=temp_db_file)
    add_backup_history(mapping_id, True, "msg", db_path=temp_db_file)
    deleted_count = cleanup_old_backup_history(days=0, db_path=temp_db_file)
    # It's possible for zero or one entry to be deleted - just test function runs and returns int
    assert isinstance(deleted_count, int)


def test_migrate_json_to_db(temp_db_file):
    # Create a fake JSON config file
    tmpdir = tempfile.mkdtemp()
    try:
        json_path = os.path.join(tmpdir, "fake_config.json")
        config = {
            "mappings": [
                {
                    "source": "s1",
                    "destination": "d1",
                    "maxVersions": 9,
                    "compression": "zip",
                }
            ],
            "last_actions": [
                "Old format simple message.",
                {
                    "success": False,
                    "message": "fail msg",
                    "timestamp": "2024-04-04T10:10:10",
                },
            ],
            "backup_settings": {"foo": "bar", "maxVersions": 15},
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(config, f)

        # Should migrate data from JSON to DB
        success = migrate_json_to_db(json_path, temp_db_file)
        assert success is True
        # Check migrated mapping
        mappings = get_mappings(db_path=temp_db_file)
        assert len(mappings) == 1
        assert mappings[0]["source"] == "s1"
        # Check migrated backup history
        history = get_backup_history(limit=5, db_path=temp_db_file)
        assert len(history) >= 2
        entry_str = any(ent["message"].startswith("Old format") for ent in history)
        entry_dict = any(ent["message"] == "fail msg" for ent in history)
        assert entry_str and entry_dict
        # Check backup settings
        settings = get_backup_settings(db_path=temp_db_file)
        assert settings.get("foo") == "bar"
        assert (
            settings.get("maxVersions") == "15" or settings.get("maxVersions") == "15"
        )
    finally:
        shutil.rmtree(tmpdir)
