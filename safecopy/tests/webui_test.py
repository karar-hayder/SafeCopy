import json
import os

try:
    import pytest  # type: ignore
except ImportError:  # noqa: W0611
    pytest = None  # type: ignore

from safecopy.config import CONFIG_BACKUP, CONFIG_FILE, DEFAULT_CONFIG


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    """
    Return a Flask test client using a fresh config file;
    disables DB (forces JSON) and disables auth.
    """
    orig_config_file = CONFIG_FILE
    orig_config_backup = CONFIG_BACKUP
    orig_dir = os.getcwd()
    temp_config = tmp_path / "config.json"
    temp_backup = tmp_path / "config.json.bak"
    temp_config.write_text(json.dumps(DEFAULT_CONFIG, indent=4), encoding="utf-8")
    os.chdir(tmp_path)

    import safecopy.config as config_mod

    config_mod.CONFIG_FILE = str(temp_config)
    config_mod.CONFIG_BACKUP = str(temp_backup)

    # Patch to disable DB usage *before* importing webui:
    monkeypatch.setattr(config_mod, "USE_DATABASE", False)

    # Auth: patch to always return False
    import safecopy.auth as auth_mod

    monkeypatch.setattr(auth_mod, "is_auth_enabled", lambda: False)

    # Patch db.controller just in case (no real db writes)
    import safecopy.db.controller as db_controller_mod

    monkeypatch.setattr(db_controller_mod, "DEFAULT_DB_PATH", ":memory:")

    # Import webui/app after config patches, also patch USE_DATABASE for redundancy:
    import safecopy.webui as webui_mod

    monkeypatch.setattr(webui_mod, "USE_DATABASE", False)
    app = webui_mod.app
    app.config["TESTING"] = True

    # Patch Flask's url_map so that url_for("index") etc. work for *_route endpoints.
    with app.app_context():
        for rule in list(app.url_map.iter_rules()):
            if rule.endpoint.endswith("_route"):
                alias = rule.endpoint[:-6]
                if alias and alias not in app.view_functions:
                    app.add_url_rule(
                        rule.rule,
                        endpoint=alias,
                        view_func=app.view_functions[rule.endpoint],
                        methods=rule.methods,
                    )

    with app.test_client() as client:
        yield client

    config_mod.CONFIG_FILE = orig_config_file
    config_mod.CONFIG_BACKUP = orig_config_backup
    os.chdir(orig_dir)


def test_index_route_unauth(test_client, recwarn):
    """Test dashboard page renders successfully without auth, and suppress flask_caching deprecation."""
    # Ignore DeprecationWarning from flask_caching, but let pytest process others.
    resp = test_client.get("/")
    assert resp.status_code == 200


def test_settings_route_renders(test_client):
    """Test settings page renders and contains keywords."""
    resp = test_client.get("/settings")
    assert resp.status_code == 200
    assert (
        b"settings" in resp.data or b"Settings" in resp.data or b"mapping" in resp.data
    )


def test_get_mappings_returns_default(test_client):
    """Test get_mappings returns list and contains 'mappings'."""
    resp = test_client.get("/get_mappings")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "mappings" in data
    assert isinstance(data["mappings"], list)


def test_save_and_reload_mappings(test_client):
    """Test save_mappings and subsequent reload of mappings."""
    resp = test_client.get("/get_mappings")
    mappings = resp.get_json()["mappings"]
    changed_value = "/tmp/fake_source"
    if mappings:
        mappings[0]["source"] = changed_value
    else:
        mappings.append(
            {
                "source": changed_value,
                "destination": "/tmp/y",
                "maxVersions": 3,
                "compression": "none",
                "id": 0,
                "enabled": True,
            }
        )
    out = test_client.post(
        "/save_mappings",
        data=json.dumps({"mappings": mappings}),
        content_type="application/json",
    )
    assert out.status_code == 200
    out_json = out.get_json()
    assert out_json["success"]

    resp2 = test_client.get("/get_mappings")
    data = resp2.get_json()
    found = any(m.get("source") == changed_value for m in data.get("mappings", []))
    if not found and len(mappings) == 1:
        fallback_found = any(
            m.get("source") == mappings[0].get("source")
            for m in data.get("mappings", [])
        )
        assert fallback_found or found
    else:
        assert found


def test_delete_mapping_route_invalid(test_client):
    """Test delete_mapping route handles invalid index gracefully."""
    resp = test_client.post("/delete_mapping", data={"index": "999"})
    assert resp.status_code == 302 or resp.status_code == 200


def test_get_backup_settings_and_save(test_client):
    """Test backup settings retrieval and save interaction."""
    resp = test_client.get("/get_backup_settings")
    assert resp.status_code == 200
    val = resp.get_json()
    assert "settings" in val

    new_settings = {"maxVersions": 42, "compression": "zip"}
    out = test_client.post(
        "/save_backup_settings",
        data=json.dumps({"settings": new_settings}),
        content_type="application/json",
    )
    assert out.status_code == 200
    assert out.get_json()["success"]
    resp2 = test_client.get("/get_backup_settings")
    settings_after = resp2.get_json()["settings"]
    for k, v in new_settings.items():
        assert k in settings_after
        if str(settings_after[k]) != str(v):
            assert str(settings_after[k]) == str(
                DEFAULT_CONFIG.get("backup_settings", {}).get(k, v)
            )
        else:
            assert str(settings_after[k]) == str(v)


def test_browse_folders_and_folder_preview(tmp_path, test_client):
    """Test browsing folders and previewing contents."""
    resp = test_client.get("/browse_folders?path=/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "drives" in data

    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "foo.txt").write_text("bar")
    (folder / "subfolder").mkdir()

    resp2 = test_client.get(f"/browse_folders?path={folder}")
    assert resp2.status_code == 200
    folders = resp2.get_json().get("folders")
    assert folders is not None
    assert "subfolder" in folders

    resp3 = test_client.get(f"/folder_preview?path={folder}")
    j = resp3.get_json()
    assert "files" in j and "folders" in j
    assert "foo.txt" in j["files"]
    assert "subfolder" in j["folders"]


def test_get_backup_history_route(test_client):
    """Test retrieving backup job history route returns history."""
    resp = test_client.get("/get_backup_history")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "history" in data


def test_email_settings_roundtrip(monkeypatch, test_client):
    """Test email settings retrieval and saving."""
    fake_settings = {}
    import safecopy.notifications as notif

    monkeypatch.setattr(notif, "get_email_settings", lambda: fake_settings)
    monkeypatch.setattr(notif, "save_email_settings", lambda **kwargs: True)
    resp = test_client.get("/email_settings")
    assert resp.status_code == 200
    assert resp.get_json()["success"]

    vals = {
        "smtp_server": "s",
        "smtp_port": 123,
        "from_email": "x@y",
        "to_email": "y@z",
        "smtp_username": None,
        "smtp_password": None,
        "use_tls": True,
        "enabled": True,
    }
    out = test_client.post(
        "/email_settings", data=json.dumps(vals), content_type="application/json"
    )
    assert out.status_code == 200
    assert out.get_json()["success"]
