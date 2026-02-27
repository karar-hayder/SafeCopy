# Changelog

All notable changes to the SafeCopy project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Email Notifications**: Automated email reports on backup success or failure.
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
