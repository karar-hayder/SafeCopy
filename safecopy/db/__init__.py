"""
Database module for SafeCopy.

This module provides database functionality for storing backup mappings,
backup history, and application settings.
"""

from safecopy.db.controller import (
    get_db_connection,
    init_database,
    get_mappings,
    get_mapping,
    add_mapping,
    update_mapping,
    delete_mapping,
    add_backup_history,
    get_backup_history,
    get_backup_settings,
    get_backup_setting,
    set_backup_setting,
    set_backup_settings,
    get_database_version,
    cleanup_old_backup_history,
    DEFAULT_DB_PATH,
    DB_VERSION,
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
