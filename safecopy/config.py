import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List

# --- .env/SECRET_KEY handling ---
try:
    from dotenv import dotenv_values, load_dotenv, set_key  # type: ignore
except ImportError:

    def load_dotenv(path=None) -> None:
        pass

    def set_key(path, key, value) -> None:
        pass

    def dotenv_values(path=None) -> dict:
        return {}


import secrets

ENV_PATH = os.path.join(os.getcwd(), ".env")
SECRET_KEY_ENV_VAR = "SECRET_KEY"


def ensure_env_secret_key() -> str | Any:
    """
    Ensure that a SECRET_KEY exists in the .env file.

    If the .env file or the SECRET_KEY variable does not exist, a new
    cryptographically secure secret key will be generated and written.
    Returns the existing or newly created secret key as a string.
    """
    env_exists = os.path.exists(ENV_PATH)
    env_vars = {}
    if env_exists:
        env_vars = dotenv_values(ENV_PATH)
    secret_key = env_vars.get(SECRET_KEY_ENV_VAR)

    if not secret_key:
        # Generate new secret key
        new_secret = secrets.token_urlsafe(48)
        # Add or create .env file with SECRET_KEY
        if env_exists:
            set_key(ENV_PATH, SECRET_KEY_ENV_VAR, new_secret)
        else:
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write(f"{SECRET_KEY_ENV_VAR}={new_secret}\n")
        return new_secret
    return secret_key


# Load environment and ensure SECRET_KEY
load_dotenv(ENV_PATH)
SECRET_KEY = os.getenv(SECRET_KEY_ENV_VAR) or ensure_env_secret_key()
# If still not set after ensure_env_secret_key, reload
if not SECRET_KEY:
    load_dotenv(ENV_PATH)

CONFIG_FILE = "config.json"
CONFIG_BACKUP = "config.json.bak"
DEFAULT_CONFIG = {
    "mappings": [],
    "last_actions": [],
    "backup_settings": {"maxVersions": 3, "compression": "none"},
}

# Database support
USE_DATABASE = True  # Set to False to use JSON instead
logger = logging.getLogger(__name__)


def init_config() -> None:
    """Initialize the configuration (database or JSON file) if it doesn't exist."""
    import sys
    from pathlib import Path

    if USE_DATABASE:
        # Initialize database and migrate from JSON if needed
        from safecopy.db.controller import DEFAULT_DB_PATH
        from safecopy.db.migrate import check_and_migrate

        if not check_and_migrate(DEFAULT_DB_PATH):
            logger.error("Failed to initialize database, falling back to JSON")
            init_config_json()
    else:
        init_config_json()

    desktop = Path.home() / "Desktop"

    if sys.platform == "win32":
        shortcut_path = desktop / "SafeCopy.lnk"
    else:
        shortcut_path = desktop / "SafeCopy.desktop"

    if not shortcut_path.exists():
        create_desktop_shortcut()


def init_config_json():
    """Initialize the JSON configuration file if it doesn't exist."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        logger.info("Created new config file: %s", CONFIG_FILE)
    else:
        # Validate existing config
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                json.load(f)
            logger.info("Validated existing config file: %s", CONFIG_FILE)
        except json.JSONDecodeError as e:
            logger.error("Invalid config file: %s", e)
            # Try to restore from backup if it exists
            if os.path.exists(CONFIG_BACKUP):
                shutil.copy(CONFIG_BACKUP, CONFIG_FILE)
                logger.info("Restored config from backup: %s", CONFIG_BACKUP)
            else:
                # Create a new config file
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.info("Created new config file after corruption: %s", CONFIG_FILE)


def create_desktop_shortcut() -> None:
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
        desktop_entry = (
            "[Desktop Entry]\n"
            "Name=SafeCopy\n"
            "Exec=xdg-open http://localhost:5000\n"
            "Type=Application\n"
            "Terminal=false\n"
            "Categories=Utility;\n"
        )
        shortcut_path = os.path.join(desktop, "SafeCopy.desktop")

        with open(shortcut_path, "w", encoding="utf-8") as f:
            f.write(desktop_entry)

        # Make executable
        os.chmod(shortcut_path, 0o755)


def open_web_ui() -> None:
    """Open the web UI in the default browser."""
    import webbrowser

    webbrowser.open("http://localhost:5000")


def load_config() -> dict[str, Any] | Any:
    """Load configuration from database or JSON file with error handling."""
    if USE_DATABASE:
        return load_config_db()
    else:
        return load_config_json()


def load_config_db() -> dict[str, Any]:
    """Load configuration from database and return in JSON-compatible format."""
    try:
        from safecopy.db.controller import (
            get_backup_history,
            get_backup_settings,
            get_mappings,
        )

        mappings: List[Dict[str, Any]] = get_mappings()
        # Convert to old format for compatibility
        mappings_list = []
        for mapping in mappings:
            mappings_list.append(
                {
                    "source": mapping["source"],
                    "destination": mapping["destination"],
                    "maxVersions": mapping["maxVersions"],
                    "compression": mapping["compression"],
                }
            )

        # Get backup history (last 10 for compatibility)
        history: List[Dict[str, Any]] = get_backup_history(limit=10)
        last_actions = []
        for entry in history:
            last_actions.append(
                {
                    "timestamp": entry["timestamp"],
                    "source": "",  # Not stored in history
                    "destination": "",  # Not stored in history
                    "success": entry["success"],
                    "message": entry["message"],
                }
            )

        # Get backup settings
        settings: Dict[str, str] = get_backup_settings()
        backup_settings = {
            "maxVersions": int(settings.get("maxVersions", 3)),
            "compression": settings.get("compression", "none"),
        }

        return {
            "mappings": mappings_list,
            "last_actions": last_actions,
            "backup_settings": backup_settings,
        }
    except Exception as e:
        logger.error("Error loading config from database: %s", e)
        return DEFAULT_CONFIG.copy()


def load_config_json() -> Any | dict[str, Any]:
    """Load configuration from JSON file with error handling."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logger.error("Error loading config: %s", e)
        # Try to restore from backup
        if os.path.exists(CONFIG_BACKUP):
            logger.info("Attempting to restore from backup: %s", CONFIG_BACKUP)
            shutil.copy(CONFIG_BACKUP, CONFIG_FILE)
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info("Successfully restored config from backup")
                return config
            except Exception:
                logger.error("Failed to restore from backup, using default config")
                return DEFAULT_CONFIG.copy()
        else:
            logger.error("No backup available, using default config")
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error("Unexpected error loading config: %s", e)
        return DEFAULT_CONFIG.copy()


def save_config(data) -> bool:
    """Save configuration to database or JSON file with error handling."""
    if USE_DATABASE:
        return save_config_db(data)
    else:
        return save_config_json(data)


def save_config_db(data) -> bool:
    """Save configuration to database."""
    try:
        from safecopy.db.controller import (
            add_mapping,
            delete_mapping,
            get_mappings,
            set_backup_settings,
            update_mapping,
        )

        # Save mappings
        if "mappings" in data:
            existing_mappings: Dict[Any, Dict[str, Any]] = {
                m["id"]: m for m in get_mappings()
            }
            existing_by_path: Dict[tuple[Any, Any], Any] = {
                (m["source"], m["destination"]): m["id"]
                for m in existing_mappings.values()
            }

            # Process new/updated mappings
            for mapping in data["mappings"]:
                source = mapping.get("source")
                destination = mapping.get("destination")
                key = (source, destination)

                if key in existing_by_path:
                    # Update existing mapping
                    mapping_id = existing_by_path[key]
                    update_mapping(
                        mapping_id=mapping_id,
                        max_versions=mapping.get("maxVersions"),
                        compression=mapping.get("compression"),
                    )
                else:
                    # Add new mapping
                    add_mapping(
                        source=source,
                        destination=destination,
                        max_versions=mapping.get("maxVersions", 3),
                        compression=mapping.get("compression", "none"),
                    )

            # Remove mappings that are no longer in the list
            current_paths = {
                (m.get("source"), m.get("destination")) for m in data["mappings"]
            }
            for mapping_id, mapping in existing_mappings.items():
                key = (mapping["source"], mapping["destination"])
                if key not in current_paths:
                    delete_mapping(mapping_id)

        # Save backup settings
        if "backup_settings" in data:
            settings = data["backup_settings"]
            settings_dict = {k: str(v) for k, v in settings.items()}
            set_backup_settings(settings_dict)

        return True
    except Exception as e:
        logger.error("Error saving config to database: %s", e)
        return False


def save_config_json(data) -> bool:
    """Save configuration to JSON file with error handling and atomic writes."""
    try:
        # Validate that data is valid JSON
        json_str: str = json.dumps(data)
        json.loads(json_str)  # This will raise an error if invalid

        # Create a backup of the current config if it exists
        if os.path.exists(CONFIG_FILE):
            shutil.copy(CONFIG_FILE, CONFIG_BACKUP)
            logger.info("Created backup of config file: %s", CONFIG_BACKUP)

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

            logger.info("Successfully saved config to %s", CONFIG_FILE)
            return True
        except Exception as e:
            logger.error("Error during atomic write: %s", e)
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON data: %s", e)
        return False
    except Exception as e:
        logger.error("Error saving configuration: %s", e)
        return False
