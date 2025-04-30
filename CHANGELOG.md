# Changelog

All notable changes to the SafeCopy project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-04-30

### Features Added

- System tray integration with menu options
- File versioning with configurable retention (default: 3 versions)
- Backup compression options (none, zip, tar)
- Improved error handling with config file backups
- Atomic writes for configuration files to prevent corruption

### Changes Made

- Updated UI to include compression and version settings
- Improved backup process with better error handling
- Enhanced logging for better troubleshooting

### Issues Fixed

- Fixed issue with config file corruption during saves
- Fixed system tray integration to work alongside web UI
- Fixed backup functionality from system tray menu

## [0.1.0] - 2025-04-29

### Initial Features

- Initial release with basic backup functionality
- Web-based user interface for configuration
- Scheduled backup functionality
- Manual backup execution
- Backup history viewer
- Basic logging system
