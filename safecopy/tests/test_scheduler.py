import os
from unittest.mock import MagicMock, patch

import pytest

from safecopy.scheduler.engine import (
    run_scheduled_backup,
    setup_all_schedules,
    setup_schedule_job,
)


@pytest.fixture
def mock_schedule():
    with patch("safecopy.scheduler.engine.schedule") as mock:
        yield mock


@pytest.fixture
def mock_mappings_service():
    with patch("safecopy.scheduler.engine.mappings_service") as mock:
        yield mock


@pytest.fixture
def mock_schedules_service():
    with patch("safecopy.scheduler.engine.schedules_service") as mock:
        yield mock


def test_setup_schedule_job_daily(mock_schedule):
    setup_schedule_job("uuid-1", "daily", "14:30")
    mock_schedule.every().day.at.assert_called_with("14:30")


def test_setup_schedule_job_minutes(mock_schedule):
    setup_schedule_job("uuid-1", "minutes", "15")
    mock_schedule.every.assert_called_with(15)


def test_setup_schedule_job_hourly(mock_schedule):
    setup_schedule_job("uuid-1", "hourly", "45")
    mock_schedule.every().hour.at.assert_called_with(":45")


@patch("safecopy.scheduler.engine.run_backup")
def test_run_scheduled_backup_success(mock_run_backup, mock_mappings_service):
    mock_mapping = MagicMock()
    mock_mapping.uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    mock_mapping.user_uuid = "ffffffff-0000-1111-2222-333333333333"
    mock_mapping.source = "C:/Source" if os.name == "nt" else "/Source"
    mock_mapping.destination = "C:/Backup" if os.name == "nt" else "/Backup"
    mock_mapping.compression = "zip"
    mock_mapping.encrypted = False
    mock_mapping.max_versions = 3
    mock_mappings_service.get_by_uuid.return_value = mock_mapping

    mock_run_backup.return_value = (True, "Success")

    run_scheduled_backup(mock_mapping.uuid)

    mock_run_backup.assert_called_once()
    assert mock_run_backup.call_args[0][0].uuid == mock_mapping.uuid


@patch("safecopy.scheduler.engine.get_available_drives")
def test_setup_all_schedules(
    mock_drives, mock_mappings_service, mock_schedules_service, mock_schedule
):
    mock_drives.return_value = ["C:/", "D:/"] if os.name == "nt" else ["/"]

    mock_mapping = MagicMock()
    mock_mapping.uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    mock_mapping.destination = "D:/backups" if os.name == "nt" else "/backups"
    mock_mappings_service.get_all.return_value = [mock_mapping]

    mock_sched = MagicMock()
    mock_sched.mapping_uuid = mock_mapping.uuid
    mock_sched.schedule_type = "daily"
    mock_sched.schedule_value = "10:00"
    mock_sched.enabled = True
    mock_schedules_service.get_all.return_value = [mock_sched]

    # Mock NT system for drive check
    with patch("os.name", "nt"):
        setup_all_schedules()

    assert mock_schedule.clear.called
    # Check if a job was added
    mock_schedule.every().day.at.assert_called_with("10:00")
