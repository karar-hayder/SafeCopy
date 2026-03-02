"""
Tests for safecopy.backup.runner

All external dependencies (BackupEngine, services, DTOs, verify) are mocked
so no database, filesystem, or Pydantic validation is involved.

Covers:
- run_backup records history and verification on success
- run_backup still records history on failure (no verification)
- run_backups_parallel returns correct success counts
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from safecopy.backup.dtos import BackupConfig
from safecopy.backup.enums import BackupStatus as EngineBackupStatus
from safecopy.backup.enums import CompressionType
from safecopy.backup.runner import run_backup, run_backups_parallel
from safecopy.backup.verification import VerificationResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(uuid: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee") -> BackupConfig:
    return BackupConfig(
        uuid=uuid,
        user_uuid="ffffffff-0000-1111-2222-333333333333",
        source="/fake/source",
        destination="/fake/dest",
        encrypted=False,
        passwd="",
        compression=CompressionType.NONE,
        max_versions=3,
    )


def _make_engine_mock(
    status=None, message="ok", duration=1.0, size=100, backup_path=None
):
    """Build a pre-configured BackupEngine mock."""
    if status is None:
        status = EngineBackupStatus.SUCCESS
    instance = MagicMock()
    instance.backup_path = Path(backup_path) if backup_path else None
    instance.backup_path_encrypted = None
    instance.run.return_value = (status, message, duration, size)
    return instance


def _make_history_mock(history_uuid: str = "hist-uuid-1234-5678-90ab-cdef01234567"):
    """Build a BackupHistoryService mock that returns a fake history record."""
    history_record = MagicMock()
    history_record.uuid = history_uuid
    service_mock = MagicMock()
    service_mock.return_value.create.return_value = history_record
    return service_mock


# ---------------------------------------------------------------------------
# run_backup — success path
# ---------------------------------------------------------------------------


@patch("safecopy.backup.runner.BackupVerificationService")
@patch("safecopy.backup.runner.BackupHistoryService")
@patch("safecopy.backup.runner.BackupVerificationCreateDTO")
@patch("safecopy.backup.runner.BackupHistoryCreateDTO")
@patch("safecopy.backup.runner.verify")
@patch("safecopy.backup.runner.BackupEngine")
def test_run_backup_success(
    MockEngine,
    mock_verify,
    MockHistoryDTO,
    MockVerificationDTO,
    MockHistoryService,
    MockVerificationService,
):
    engine_instance = _make_engine_mock(
        status=EngineBackupStatus.SUCCESS,
        backup_path="/fake/dest/backup.bak",
    )
    MockEngine.return_value = engine_instance

    mock_verify.return_value = VerificationResult(
        success=True,
        message="All files verified successfully",
        source_checksum="abc123",
        backup_checksum="abc123",
    )

    history_record = MagicMock()
    history_record.uuid = "hist-uuid-1234-5678-90ab-cdef01234567"
    MockHistoryService.return_value.create.return_value = history_record

    success, message = run_backup(_make_config())

    assert success is True
    MockHistoryService.return_value.create.assert_called_once()
    MockVerificationService.return_value.create.assert_called_once()
    mock_verify.assert_called_once()


# ---------------------------------------------------------------------------
# run_backup — engine failure: history recorded but verification skipped
# ---------------------------------------------------------------------------


@patch("safecopy.backup.runner.BackupVerificationService")
@patch("safecopy.backup.runner.BackupHistoryService")
@patch("safecopy.backup.runner.BackupVerificationCreateDTO")
@patch("safecopy.backup.runner.BackupHistoryCreateDTO")
@patch("safecopy.backup.runner.verify")
@patch("safecopy.backup.runner.BackupEngine")
def test_run_backup_engine_failure(
    MockEngine,
    mock_verify,
    MockHistoryDTO,
    MockVerificationDTO,
    MockHistoryService,
    MockVerificationService,
):
    engine_instance = _make_engine_mock(
        status=EngineBackupStatus.FAILED,
        message="disk full",
        duration=0.5,
        size=0,
        backup_path=None,  # no backup produced
    )
    MockEngine.return_value = engine_instance

    history_record = MagicMock()
    history_record.uuid = "hist-uuid-fail-0000-0000-0000-000000000000"
    MockHistoryService.return_value.create.return_value = history_record

    success, message = run_backup(_make_config())

    assert success is False
    MockHistoryService.return_value.create.assert_called_once()
    mock_verify.assert_not_called()
    MockVerificationService.return_value.create.assert_not_called()


# ---------------------------------------------------------------------------
# run_backups_parallel
# ---------------------------------------------------------------------------


@patch("safecopy.backup.runner.run_backup")
def test_run_backups_parallel_all_succeed(mock_run_backup):
    mock_run_backup.return_value = (True, "ok")
    configs = [
        _make_config(f"aaaaaaaa-bbbb-cccc-dddd-{str(i).zfill(12)}") for i in range(4)
    ]

    results = run_backups_parallel(configs, max_workers=2)

    assert len(results) == 4
    assert all(r[0] is True for r in results)


@patch("safecopy.backup.runner.run_backup")
def test_run_backups_parallel_partial_failure(mock_run_backup):
    """Second call raises; the others succeed."""
    call_count = {"n": 0}

    def side_effect(config):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated failure")
        return (True, "ok")

    mock_run_backup.side_effect = side_effect
    configs = [
        _make_config(f"aaaaaaaa-bbbb-cccc-dddd-{str(i).zfill(12)}") for i in range(3)
    ]

    results = run_backups_parallel(configs, max_workers=2)

    assert len(results) == 3
    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]
    assert len(successes) == 2
    assert len(failures) == 1
