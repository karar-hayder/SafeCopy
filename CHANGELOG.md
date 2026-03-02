# Changelog

All notable changes to the SafeCopy project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0-dev] - 2026-03-02 *(refactoring in progress — last stable: `aed40f7e`)*

### Architecture

- **Modular backup package** — `safecopy/backup.py` (monolith) is replaced by the `safecopy/backup/` package:
  - `engine.py` — `BackupEngine` class; pure copy/compress logic, no I/O side-effects beyond the backup itself
  - `manifest.py` — pure-function manifest generators and embedders for directory, ZIP, and TAR backups; `load_manifest` loader used by verification
  - `verification.py` — self-contained backup verifier returning a typed `VerificationResult` dataclass; no dependency on the old `verification.py`
  - `runner.py` — orchestrator: runs engine → records DB history → verifies → records DB verification
  - `dtos.py` — `BackupConfig`, `BackupJob`, `BackupResult` Pydantic models
  - `enums.py` — `CompressionType`, `BackupStatus`, `BackupJobStatus`
  - `cryptor.py` — moved from `safecopy/cryptor.py` into the backup package
- **SQLAlchemy database layer** — `safecopy/db/` fully replaces the old `controller.py` raw-SQL module:
  - `models.py` — SQLAlchemy ORM models (`Mappings`, `BackupHistory`, `BackupVerification`, `BackupSchedules`, `User`)
  - `repos/` — `BaseRepo` + concrete repos per model
  - `services/` — `BaseService` + `BackupHistoryService`, `BackupVerificationService`, `MappingsService`, `BackupSchedulesService`, `UserService`
  - `dtos/` — Pydantic Create/Update/Response DTOs with field-level validators for every model
  - `enums.py` — `BackupStatus`, `BackupVerificationStatus`, `CompressionType`, `HashType`, `PasswdMode`, `UserRole`, etc.
  - `session.py` — SQLAlchemy session context manager
- **Backup naming** format changed to `safe_copy_<source>_<timestamp>_<uuid>_<compression><ext>`

### Features Added

- **Manifest generation**: every backup now embeds a `manifest.json` with per-file `{size, mtime, checksum}` entries:
  - ZIP: embedded inside the archive
  - TAR: re-packed with manifest included
  - Plain directory: written as `manifest.json` inside the backup dir
  - Plain file: written as a `<name>_manifest.json` sidecar
- **DB-backed history and verification**: every backup run writes a `BackupHistory` row and a `BackupVerification` row via the new SQLAlchemy services
- **Parallel backup runner**: `run_backups_parallel(configs, max_workers)` in `runner.py`
- **Unit test suite** for the backup package (`safecopy/tests/backup/`):
  - `test_manifest.py` — generators, embedders, and `load_manifest` for all backup types
  - `test_verification.py` — verify passes/fails; tamper detection; missing manifest/source
  - `test_engine.py` — all 4 backup types including manifest content, plus empty-source guard
  - `test_runner.py` — mocked unit tests for `run_backup` and `run_backups_parallel`
- **Unit test suite** for DB services (`safecopy/tests/services/`):
  - `test_history_service.py`, `test_mappings_service.py`, `test_schedules_service.py`, `test_user_service.py`, `test_verification_service.py`

### Features Removed

- **SMTP integration for automated email notifications.** (Removed in v0.5.0, planned to be re-added in v0.6.0)

## [0.4.0] - 2026-02-27

### Features Added

- **End-to-End Encryption**: AES-256-GCM encryption with chunk-length-prefixed format.
- **Improved Security**: Secure key storage in system keyring and use of UUIDs for mapping identification.
- **Enhanced Backup Flow**: Reordered process to verify backup integrity *before* encryption.
- **UI Support**: New settings in Web UI to enable/disable encryption per mapping.

### Changes Made

- Refactored `Cryptor` to use modern cryptography (`AESGCM`).
- Added magic header `SFENC1.0` to encrypted files for identification.
- Updated `db/controller.py` with `uuid` column and NOT NULL constraints for improved data integrity.

## [0.3.0] - 2025-12-15

### Features Added (0.3.0)

- **Web UI Authentication**: Built-in user management and password protection.
- **Advanced Scheduler**: Flexible daily, weekly, monthly, and interval-based scheduling.
- **Email Notifications**: Automated email reports on backup success or failure. (Removed in v0.5.0, planned to be re-added in v0.6.0)
- **Backup Verification**: Content integrity checks using MD5 checksums.

## [0.2.0] - 2025-04-30

### Features Added (0.2.0)

- System tray integration with menu options
- File versioning with configurable retention (default: 3 versions)
- Backup compression options (none, zip, tar)
- Improved error handling with config file backups
- Atomic writes for configuration files to prevent corruption

### Changes Made (0.2.0)

- Updated UI to include compression and version settings
- Improved backup process with better error handling
- Enhanced logging for better troubleshooting

### Issues Fixed (0.2.0)

- Fixed issue with config file corruption during saves
- Fixed system tray integration to work alongside web UI
- Fixed backup functionality from system tray menu

## [0.1.0] - 2025-04-29

### Initial Features (0.1.0)

- Initial release with basic backup functionality
- Web-based user interface for configuration
- Scheduled backup functionality
- Manual backup execution
- Backup history viewer
- Basic logging system
