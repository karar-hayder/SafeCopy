# SafeCopy

SafeCopy is an automated backup tool with a modern web UI designed for effortlessly configuring, scheduling, and monitoring backups from any source folder to your preferred destination.

## Features

- **Modern Web UI**: Intuitive dashboard for all backup operations and management
- **Advanced Scheduling**: Flexible backup scheduling (interval, daily, weekly, monthly)
- **Multiple Backup Mappings**: Support for many independent source–destination pairs
- **Detailed Logs & History**: Rich backup logs, error handling, and visual history viewer
- **On-Demand & Scheduled Execution**: Run backups instantly from the UI or let them run by schedule
- **File Versioning**: Automatic retention of multiple backup versions per mapping
- **Backup Compression**: Choose from: none, zip, or tar
- **System Tray Integration**: Background operation and convenience controls
- **Role-based Web Authentication**: Built-in user management and password protection *(since 0.3.0)*
- **Database or File-backed Config**: Configuration auto-migrates from JSON to SQLite as needed

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/karar-hayder/SafeCopy.git
   cd safecopy
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # (Windows)
   source .venv/bin/activate  # (macOS/Linux)
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting SafeCopy

Launch the app with default settings:

```bash
python main.py
```

### Command-Line Options

- `--interval`: Set backup interval in minutes (default: 10 for legacy interval mode; use the scheduler for advanced scheduling)
- `--port`: Set the web UI port (default: 5000)

Example:

```bash
python main.py --interval 30 --port 8080
```

### Accessing the Web UI

After launch, open your browser and navigate to:

```bash
http://localhost:5000
```

If you've enabled authentication/password protection, login with your configured user.

### Creating Backup Mappings

1. Go to the "Mappings" section of the dashboard.
2. Click "Add Mapping": Specify the source folder, choose a destination drive, set compression and max versions.
3. Save and optionally schedule your new mapping.

### Scheduling Backups

- **Flexible Scheduling**: Use the "Schedules" tab to add daily, weekly, monthly, or interval-based schedules for any mapping.
- **Cancel or Edit Schedules**: All future backups update as you change the configuration.

### Running Backups

- **Manual**: Use the "Run Now" buttons per mapping in the dashboard.
- **Scheduled**: All scheduled jobs run automatically, tracked and logged.

### Viewing Logs & History

- "Backup History" in the dashboard shows all recent actions, success/failure, duration, size, etc.

## Configuration

**SafeCopy** now primarily uses an SQLite database for all persistent data (mappings, schedules, logs, settings, users). If running in "legacy" mode, it will use `config.json` as follows:

```json
{
    "mappings": [
        {
            "source": "C:/path/to/source",
            "destination": "D:/",
            "maxVersions": 3,
            "compression": "zip"
        }
    ],
    "last_actions": [
        "Backup from C:/path/to/source to D:/backup_20230429_123456 completed in 5.23 seconds. Size: 125.45 MB"
    ],
    "backup_settings": {
        "maxVersions": 3,
        "compression": "zip"
    }
}
```

Most users will interact with configuration through the UI, not by editing files.

## Logs

Backup and system logs are found in `safecopy.log`. All jobs, errors, and events including backup sizes, durations, and results are available in the dashboard.

## License

Distributed under the MIT License. See `LICENSE` for details.

## Development Roadmap

### v0.1.0 *(completed)*

- ✅ Folder-to-folder backup (manual/scheduled)
- ✅ Basic Flask web UI
- ✅ JSON-based configuration
- ✅ Logging and background operation
- ✅ Basic history viewer

### v0.2.0 *(completed)*

- ✅ System tray integration
- ✅ File versioning (retention)
- ✅ Better error reporting & recovery
- ✅ Configurable backup compression

### v0.3.0 *(completed)*

- ✅ **Web UI authentication & user management**
- ✅ **Advanced scheduler:** daily/weekly/monthly/interval
- ✅ **Email notifications on backup results**
- ✅ **Backup verification:** integrity and checksums

### v0.4.0 *(in progress)*

- 🔄 Unit tests for backup/schedule modules
- 🔄 Optimizations for large-scale backups
- 🔄 Backup encryption support
- 🔄 Stats/reporting dashboard

### v1.0.0

- 🔄 PyInstaller onefile packaging
- 🔄 Windows system service/installer options
- 🔄 Complete documentation

Contributions and suggestions are very welcome!
