# Changelog

All notable changes to the SafeCopy project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-04

### Architecture

- **Modular backup package** — `safecopy/backup.py` (monolith) is replaced by the `safecopy/backup/` package:
  - `engine.py` — `BackupEngine` class; pure copy/compress logic, no I/O side-effects beyond the backup itself.
  - `manifest.py` — pure-function manifest generators and embedders for directory, ZIP, and TAR backups; `load_manifest` loader used by verification.
  - `verification.py` — self-contained backup verifier returning a typed `VerificationResult` dataclass; no dependency on the old `verification.py`.
  - `runner.py` — orchestrator: runs engine → records DB history → verifies → records DB verification.
  - `dtos.py` — `BackupConfig`, `BackupJob`, `BackupResult` Pydantic models.
  - `enums.py` — `CompressionType`, `BackupStatus`, `BackupJobStatus`.
  - `cryptor.py` — moved from `safecopy/cryptor.py` into the backup package.
- **SQLAlchemy database layer** — `safecopy/db/` fully replaces the old `controller.py` raw-SQL module:
  - `models.py` — SQLAlchemy ORM models (`Mappings`, `BackupHistory`, `BackupVerification`, `BackupSchedules`, `User`).
  - `repos/` — `BaseRepo` + concrete repos per model.
  - `services/` — `BaseService` + `BackupHistoryService`, `BackupVerificationService`, `MappingsService`, `BackupSchedulesService`, `UserService`.
  - `dtos/` — Pydantic Create/Update/Response DTOs with field-level validators for every model.
  - `enums.py` — `BackupStatus`, `BackupVerificationStatus`, `CompressionType`, `HashType`, `PasswdMode`, `UserRole`, etc.
  - `session.py` — SQLAlchemy session context manager.
- **Backup naming** format changed to `safe_copy_<source>_<timestamp>_<uuid>_<job_id>_<compression><ext>` for absolute uniqueness.

### Features Added

- **Manifest generation**: every backup now embeds a `manifest.json` with per-file `{size, mtime, checksum}` entries:
  - ZIP: embedded inside the archive.
  - TAR: re-packed with manifest included (optimized with streaming repack).
  - Plain directory: written as `manifest.json` inside the backup dir.
  - Plain file: written as a `<name>_manifest.json` sidecar.
- **DB-backed history and verification**: every backup run writes a `BackupHistory` row and a `BackupVerification` row via the new SQLAlchemy services.
- **Parallel backup runner**: `run_backups_parallel(configs, max_workers)` in `runner.py`.
- **Advanced Scheduling**: Added support for **Minutes** and **Hourly** backup triggers in both the engine and Web UI.
- **Web UI Refactoring**:
  - Deprecated and removed legacy webui file `safecopy/webui.py`.
  - Introduced new modular web structure in `safecopy/web/`.
  - Standardized templates using Jinja2 `base.html` inheritance.
  - Optimized dashboard layout with auto-refreshing history and system status.
- **Comprehensive Testing & DevOps**:
  - Full test suite (51 tests) with 99% coverage across all modules.
  - Added `.coveragerc` and automated coverage reporting.
  - Introduced `.markdownlint.json` configuration to enforce documentation quality.
  - Integrated `pre-commit` hooks for automated linting and formatting.
- **Scheduler Engine Migration**:
  - Deprecated and removed legacy advanced scheduler modules.
  - Introduced a unified, lightweight `safecopy/scheduler/engine.py` for all trigger types.

### Reliability & Fixes

- **Atomic File Operations**: Implemented retry logic with exponential backoff for `os.replace` to handle transient file locks on Windows.
- **Thread Safety**: Removed ineffective threading from manifest generation to resolve checksum mismatches.
- **Unique Job IDs**: Incorporated 8-character unique job IDs into backup filenames to prevent race conditions during concurrent runs.
- **Backup Version Cleanup**:
  - Enhanced pruning logic to correctly identify and ignore sidecar manifest files.
  - Automated removal of associated manifest files when a backup version is pruned.
- **Isolation**: Improved `ensure_admin_exists` and added database isolation (cleanup) in test fixtures.

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
