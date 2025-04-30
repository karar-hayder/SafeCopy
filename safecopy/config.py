import json
import os
import shutil
import tempfile
import logging
from pathlib import Path

CONFIG_FILE = "config.json"
CONFIG_BACKUP = "config.json.bak"
DEFAULT_CONFIG = {
    "mappings": [],
    "last_actions": [],
    "backup_settings": {"maxVersions": 3, "compression": "none"},
}

logger = logging.getLogger(__name__)


def init_config():
    """Initialize the configuration file if it doesn't exist."""
    from pathlib import Path
    import sys

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        logger.info(f"Created new config file: {CONFIG_FILE}")
    else:
        # Validate existing config
        try:
            with open(CONFIG_FILE, "r") as f:
                json.load(f)
            logger.info(f"Validated existing config file: {CONFIG_FILE}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid config file: {e}")
            # Try to restore from backup if it exists
            if os.path.exists(CONFIG_BACKUP):
                shutil.copy(CONFIG_BACKUP, CONFIG_FILE)
                logger.info(f"Restored config from backup: {CONFIG_BACKUP}")
            else:
                # Create a new config file
                with open(CONFIG_FILE, "w") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.info(f"Created new config file after corruption: {CONFIG_FILE}")

    desktop = Path.home() / "Desktop"

    if sys.platform == "win32":
        shortcut_path = desktop / "SafeCopy.lnk"
    else:
        shortcut_path = desktop / "SafeCopy.desktop"

    if not shortcut_path.exists():
        create_desktop_shortcut()


def create_desktop_shortcut():
    """Create a shortcut on the desktop to launch the web UI."""
    import sys
    from pathlib import Path

    desktop = Path.home() / "Desktop"

    if sys.platform == "win32":
        from win32com.client import Dispatch

        shortcut_path = os.path.join(desktop, "SafeCopy.lnk")
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = "cmd"
        shortcut.Arguments = "/c start http://localhost:5000"
        shortcut.WorkingDirectory = str(Path.home())

        # Set icon if available
        static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
        logo_path = os.path.join(static_dir, "imgs", "logo.ico")
        print(logo_path)

        if logo_path:
            shortcut.IconLocation = logo_path

        shortcut.save()

    else:  # Linux/Mac
        desktop_entry = f"""[Desktop Entry]
Name=SafeCopy
Exec=xdg-open http://localhost:5000
Type=Application
Terminal=false
Categories=Utility;
"""
        shortcut_path = os.path.join(desktop, "SafeCopy.desktop")

        with open(shortcut_path, "w") as f:
            f.write(desktop_entry)

        # Make executable
        os.chmod(shortcut_path, 0o755)


def open_web_ui():
    """Open the web UI in the default browser."""
    import webbrowser

    webbrowser.open("http://localhost:5000")


def load_config():
    """Load configuration from file with error handling."""
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error loading config: {e}")
        # Try to restore from backup
        if os.path.exists(CONFIG_BACKUP):
            logger.info(f"Attempting to restore from backup: {CONFIG_BACKUP}")
            shutil.copy(CONFIG_BACKUP, CONFIG_FILE)
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                logger.info("Successfully restored config from backup")
                return config
            except:
                logger.error("Failed to restore from backup, using default config")
                return DEFAULT_CONFIG.copy()
        else:
            logger.error("No backup available, using default config")
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Unexpected error loading config: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(data):
    """Save configuration to file with error handling and atomic writes."""
    try:
        # Validate that data is valid JSON
        json_str = json.dumps(data)
        json.loads(json_str)  # This will raise an error if invalid

        # Create a backup of the current config if it exists
        if os.path.exists(CONFIG_FILE):
            shutil.copy(CONFIG_FILE, CONFIG_BACKUP)
            logger.info(f"Created backup of config file: {CONFIG_BACKUP}")

        # Use atomic write with a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
        temp_path = temp_file.name

        try:
            # Write to temporary file
            json.dump(data, temp_file, indent=4)
            temp_file.close()

            # Replace the original file with the temporary file
            if os.name == "nt":  # Windows
                # On Windows, we need to remove the original file first
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
                shutil.move(temp_path, CONFIG_FILE)
            else:  # Unix-like
                shutil.move(temp_path, CONFIG_FILE)

            logger.info(f"Successfully saved config to {CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error during atomic write: {e}")
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {e}")
        return False
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False
