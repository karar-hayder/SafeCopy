# SafeCopy

SafeCopy is an automated backup tool that allows you to easily configure and schedule backups from source folders to destination drives.

## Features

- Web-based user interface for easy configuration
- Automated scheduled backups
- Support for multiple backup mappings
- Detailed backup logs and history
- On-demand backup execution
- Configurable backup intervals

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/safecopy.git
   cd safecopy
   ```

2. Create a virtual environment and activate it:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   source .venv/bin/activate  # On macOS/Linux
   ```

3. Install the required dependencies:

   ```bash
   pip install flask flask-caching
   ```

## Usage

### Starting the Application

Run the application with default settings:

```bash
python main.py
```

### Command Line Options

- `--interval`: Set the backup interval in minutes (default: 10)
- `--port`: Set the web UI port (default: 5000)

Example:

```bash
python main.py --interval 30 --port 8080
```

### Web Interface

Once the application is running, open your web browser and navigate to:

```bash
http://localhost:5000
```

### Adding Backup Mappings

1. In the web interface, enter the source folder path in the "Source Folder" field.
2. Select the destination drive from the dropdown menu.
3. Click "Add Mapping" to save the configuration.

### Running Backups

- **Scheduled Backups**: The application automatically runs backups at the configured interval.
- **Manual Backups**: Click the "Run Backup Now" button in the web interface to start a backup immediately.

### Viewing Backup History

The "Recent Actions" section in the web interface displays the history of backup operations, including success and failure messages.

## Configuration

The application configuration is stored in `config.json` in the following format:

```json
{
    "mappings": [
        {
            "source": "C:/path/to/source",
            "destination": "D:/"
        }
    ],
    "last_actions": [
        "Backup from C:/path/to/source to D:/backup_20230429_123456 completed in 5.23 seconds. Size: 125.45 MB"
    ],
    "last_scheduled_backup": "2023-04-29 12:34:56"
}
```

## Logs

The application logs are stored in `safecopy.log` and include detailed information about backup operations, errors, and system events.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
