"""
Database module for SafeCopy.

This module provides database functionality for storing backup mappings,
backup history, and application settings.
"""

from safecopy.db.controller import (
    DB_VERSION,
    DEFAULT_DB_PATH,
    add_backup_history,
    add_mapping,
    cleanup_old_backup_history,
    delete_mapping,
    get_backup_history,
    get_backup_setting,
    get_backup_settings,
    get_database_version,
    get_db_connection,
    get_mapping,
    get_mappings,
    init_database,
    set_backup_setting,
    set_backup_settings,
    update_mapping,
)

__all__: list[str] = [
    "get_db_connection",
    "init_database",
    "get_mappings",
    "get_mapping",
    "add_mapping",
    "update_mapping",
    "delete_mapping",
    "add_backup_history",
    "get_backup_history",
    "get_backup_settings",
    "get_backup_setting",
    "set_backup_setting",
    "set_backup_settings",
    "get_database_version",
    "cleanup_old_backup_history",
    "DEFAULT_DB_PATH",
    "DB_VERSION",
]
