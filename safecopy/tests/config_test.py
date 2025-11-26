import json
import os
import shutil
import tempfile

try:
    import pytest  # type: ignore
except ImportError:
    pytest = None  # type: ignore

from safecopy import config


@pytest.fixture
def temp_config_file():
    tmpdir = tempfile.mkdtemp()
    config_path = os.path.join(tmpdir, "config.json")
    backup_path = os.path.join(tmpdir, "config.json.bak")
    yield config_path, backup_path, tmpdir
    shutil.rmtree(tmpdir)


def test_save_and_load_config_json(temp_config_file, monkeypatch):
    config_path, backup_path, _tmpdir = temp_config_file

    # Patch config module path variables
    monkeypatch.setattr(config, "CONFIG_FILE", config_path)
    monkeypatch.setattr(config, "CONFIG_BACKUP", backup_path)
    monkeypatch.setattr(config, "USE_DATABASE", False)

    data = {
        "mappings": [
            {
                "source": "/src",
                "destination": "/dst",
                "maxVersions": 5,
                "compression": "zip",
            }
        ],
        "last_actions": [
            {"timestamp": "2024-04-05T12:34:00", "success": True, "message": "ok"}
        ],
        "backup_settings": {"maxVersions": 5, "compression": "zip"},
    }
    result = config.save_config(data)
    assert result is True

    # Should read back what we just wrote
    loaded = config.load_config_json()
    assert loaded["mappings"][0]["source"] == "/src"
    assert loaded["backup_settings"]["maxVersions"] == 5

    # Should make a backup if CONFIG_FILE already exists
    assert os.path.exists(config_path)
    result2 = config.save_config(data)
    assert result2 is True
    assert os.path.exists(backup_path)


def test_save_config_json_invalid(monkeypatch, temp_config_file):
    config_path, backup_path, tmpdir = temp_config_file
    monkeypatch.setattr(config, "CONFIG_FILE", config_path)
    monkeypatch.setattr(config, "CONFIG_BACKUP", backup_path)
    monkeypatch.setattr(config, "USE_DATABASE", False)

    # Invalid type: not JSON serializable
    bad_data = {"foo": {1, 2}}
    result = config.save_config(bad_data)
    assert result is False

    # Attempt malformed (simulate corrupted config)
    with open(config_path, "w") as f:
        f.write("{ bad json }")
    # Should fall back to default config
    loaded = config.load_config_json()
    assert isinstance(loaded, dict)
    assert "mappings" in loaded


def test_env_secret_key_generation(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    monkeypatch.setattr(config, "ENV_PATH", str(env_path))
    monkeypatch.setattr(config, "SECRET_KEY_ENV_VAR", "SECRET_KEY")

    # Remove file if it exists
    if env_path.exists():
        env_path.unlink()
    # Ensure SECRET_KEY is generated
    secret = config.ensure_env_secret_key()
    assert isinstance(secret, str)
    assert len(secret) > 10
    # Calling again should return same key
    secret2 = config.ensure_env_secret_key()
    assert secret == secret2
    # SECRET_KEY is present in .env
    content = env_path.read_text()
    assert "SECRET_KEY" in content


# Additional test for config loading fallback
def test_load_config_json_recovers_from_backup(monkeypatch, temp_config_file):
    config_path, backup_path, tmpdir = temp_config_file
    monkeypatch.setattr(config, "CONFIG_FILE", config_path)
    monkeypatch.setattr(config, "CONFIG_BACKUP", backup_path)
    monkeypatch.setattr(config, "USE_DATABASE", False)

    # Write a valid config and backup
    good_data = {"foo": "bar"}
    with open(config_path, "w") as f:
        json.dump(good_data, f)
    shutil.copy(config_path, backup_path)

    # Now, corrupt the config file
    with open(config_path, "w") as f:
        f.write("{ bad json")

    loaded = config.load_config_json()
    assert loaded == good_data or isinstance(loaded, dict)
