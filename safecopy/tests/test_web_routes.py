import os
from unittest.mock import patch

import pytest

from safecopy.web.webApp import WebApp


@pytest.fixture
def app_with_test_db(db_session, test_engine):
    # Patch start_advanced_scheduler to avoid background threads
    with patch("safecopy.web.webApp.start_advanced_scheduler"):
        # Patch engine in session.py so WebApp uses our test engine
        with patch("safecopy.db.session.engine", test_engine):
            web_app = WebApp("test_secret")
            return web_app.app


@pytest.fixture
def client(app_with_test_db):
    return app_with_test_db.test_client()


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_admin_login_success(client, db_session):
    # Admin is created by WebApp.__init__ via ensure_admin_exists
    response = client.post(
        "/login",
        data={"username": "admin", "password": "adminpassword"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data


@pytest.fixture
def authenticated_client(client, db_session):
    client.post("/login", data={"username": "admin", "password": "adminpassword"})
    return client


def test_get_mappings(authenticated_client):
    response = authenticated_client.get("/get_mappings")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"]["mappings"], list)


def test_save_mapping_success(authenticated_client):
    # Mock drive check for path validation if needed,
    # but DTO validation should pass if path is "absolute"
    mapping_data = {
        "source": "C:/Source" if os.name == "nt" else "/Source",
        "destination": "C:/Backup" if os.name == "nt" else "/Backup",
        "max_versions": 5,
        "compression": "zip",
        "enabled": True,
        "encrypted": False,
    }

    # Expects {"mappings": [...]}
    response = authenticated_client.post(
        "/save_mappings", json={"mappings": [mapping_data]}
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True


@patch("safecopy.web.routes.backup.run_backups_parallel")
def test_run_backup_route(mock_run_parallel, authenticated_client, tmp_path):
    mock_run_parallel.return_value = [(True, "Started")]

    src = tmp_path / "source"
    src.mkdir()
    dst = tmp_path / "dest"
    dst.mkdir()

    mapping_data = {
        "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "source": str(src),
        "destination": str(dst),
        "compression": "zip",
        "encryption": False,
        "max_versions": 3,
        "enabled": True,
    }
    # Expects {"mappings": [...]}
    response = authenticated_client.post(
        "/run_backup", json={"mappings": [mapping_data]}
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    mock_run_parallel.assert_called_once()
