"""
Migration utility to migrate data from JSON config to database.
"""

import json
import os
import logging
from safecopy.db.controller import (
    init_database,
    add_mapping,
    add_backup_history,
    set_backup_settings,
    get_mappings,
    DEFAULT_DB_PATH,
)
from safecopy.config import CONFIG_FILE, CONFIG_BACKUP, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def migrate_json_to_db(json_path: str = None, db_path: str = None) -> bool:
    """
    Migrate data from JSON config file to database.

    Args:
        json_path: Path to JSON config file. If None, uses CONFIG_FILE.
        db_path: Path to database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        True if migration was successful, False otherwise
    """
    if json_path is None:
        json_path = CONFIG_FILE

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Check if JSON file exists
    if not os.path.exists(json_path):
        logger.info("No JSON config file found, skipping migration")
        return True  # Not an error, just nothing to migrate

    # Check if database already has data
    if os.path.exists(db_path):
        existing_mappings = get_mappings(db_path)
        if existing_mappings:
            logger.info("Database already contains data, skipping migration")
            return True

    try:
        # Load JSON config
        with open(json_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        logger.info("Starting migration from JSON to database...")

        # Initialize database
        if not init_database(db_path):
            logger.error("Failed to initialize database")
            return False

        # Migrate mappings
        mappings = config.get("mappings", [])
        migrated_count = 0
        for mapping in mappings:
            try:
                mapping_id = add_mapping(
                    source=mapping.get("source", ""),
                    destination=mapping.get("destination", ""),
                    max_versions=mapping.get("maxVersions", 3),
                    compression=mapping.get("compression", "none"),
                    enabled=True,
                    db_path=db_path,
                )
                if mapping_id:
                    migrated_count += 1
            except Exception as e:
                logger.warning("Failed to migrate mapping %s: %s", mapping, e)

        logger.info("Migrated %d mappings", migrated_count)

        # Migrate backup history (last_actions)
        last_actions = config.get("last_actions", [])
        history_count = 0
        for action in last_actions:
            try:
                # Handle both old string format and new dict format
                if isinstance(action, str):
                    # Old format: just a message string
                    add_backup_history(
                        mapping_id=None,
                        success=True,  # Assume success for old format
                        message=action,
                        db_path=db_path,
                    )
                    history_count += 1
                elif isinstance(action, dict):
                    # New format: dict with timestamp, source, destination, success, message
                    add_backup_history(
                        mapping_id=None,  # Can't map to specific mapping without lookup
                        success=action.get("success", True),
                        message=action.get("message", ""),
                        timestamp=action.get("timestamp"),
                        db_path=db_path,
                    )
                    history_count += 1
            except Exception as e:
                logger.warning("Failed to migrate history entry %s: %s", action, e)

        logger.info("Migrated %d backup history entries", history_count)

        # Migrate backup settings
        backup_settings = config.get("backup_settings", {})
        if backup_settings:
            try:
                # Convert values to strings for database storage
                settings_dict = {k: str(v) for k, v in backup_settings.items()}
                set_backup_settings(settings_dict, db_path)
                logger.info("Migrated backup settings")
            except Exception as e:
                logger.warning("Failed to migrate backup settings: %s", e)

        logger.info("Migration completed successfully")
        return True

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON config file: %s", e)
        return False
    except Exception as e:
        logger.error("Error during migration: %s", e)
        return False


def check_and_migrate(db_path: str = None) -> bool:
    """
    Check if migration is needed and perform it if necessary.

    Args:
        db_path: Path to database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        True if migration check/completion was successful
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Initialize database if it doesn't exist
    if not os.path.exists(db_path):
        logger.info("Database does not exist, initializing...")
        if not init_database(db_path):
            logger.error("Failed to initialize database")
            return False

    # Check if we need to migrate from JSON
    if os.path.exists(CONFIG_FILE):
        # Check if database is empty
        existing_mappings = get_mappings(db_path)
        if not existing_mappings:
            logger.info("Database is empty, attempting migration from JSON...")
            return migrate_json_to_db(CONFIG_FILE, db_path)

    return True
