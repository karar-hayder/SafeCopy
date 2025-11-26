import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "safecopy.db"
DB_VERSION = 1


@contextmanager
def get_db_connection(db_path: str = None):
    """
    Context manager for database connections.
    Establishes and returns a connection to the SQLite database at the given path.

    Args:
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Yields:
        sqlite3.Connection: Database connection
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Database error: %s", e)
        raise RuntimeError(f"Failed to connect to database at {db_path}: {e}") from e
    finally:
        if conn:
            conn.close()


def init_database(db_path: str = None) -> bool:
    """
    Initialize the database with the required schema.

    Args:
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        bool: True if initialization was successful, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Create mappings table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    max_versions INTEGER DEFAULT 3,
                    compression TEXT DEFAULT 'none',
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, destination)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapping_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success INTEGER DEFAULT 1,
                    message TEXT,
                    duration REAL,
                    size_bytes INTEGER,
                    backup_path TEXT,
                    FOREIGN KEY (mapping_id) REFERENCES mappings(id) ON DELETE SET NULL
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS database_version (
                    version INTEGER PRIMARY KEY,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create backup_schedules table for advanced scheduling
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapping_id INTEGER NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_value TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mapping_id) REFERENCES mappings(id) ON DELETE CASCADE
                )
            """
            )

            # Create email_settings table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS email_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smtp_server TEXT NOT NULL,
                    smtp_port INTEGER DEFAULT 587,
                    smtp_username TEXT,
                    smtp_password TEXT,
                    from_email TEXT NOT NULL,
                    to_email TEXT NOT NULL,
                    use_tls INTEGER DEFAULT 1,
                    enabled INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create backup_verification table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_verification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_history_id INTEGER NOT NULL,
                    checksum_type TEXT DEFAULT 'md5',
                    source_checksum TEXT,
                    backup_checksum TEXT,
                    verification_status INTEGER DEFAULT 0,
                    verified_at TIMESTAMP,
                    FOREIGN KEY (backup_history_id) REFERENCES backup_history(id) ON DELETE CASCADE
                )
            """
            )

            # Create web_auth table for password protection
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS web_auth (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Check current database version and migrate if needed
            cursor.execute("SELECT version FROM database_version ORDER BY version DESC LIMIT 1")
            current_version_row = cursor.fetchone()
            current_version = current_version_row["version"] if current_version_row else 0

            if current_version < DB_VERSION:
                # Migration from version 1 to 2
                logger.info("Migrating database from version %s to %s", current_version, DB_VERSION)
                # Tables are created with IF NOT EXISTS, so this is safe
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO database_version (version, updated_at) VALUES (?, CURRENT_TIMESTAMP)
                """,
                    (DB_VERSION,),
                )
            else:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO database_version (version) VALUES (?)
                """,
                    (DB_VERSION,),
                )

            # Initialize default settings if they don't exist
            default_settings = {"maxVersions": "3", "compression": "none"}
            for key, value in default_settings.items():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO backup_settings (key, value) VALUES (?, ?)
                """,
                    (key, value),
                )

            conn.commit()
            logger.info("Database initialized successfully at %s", db_path)
            return True

    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        return False


def get_mappings(db_path: str = None) -> List[Dict[str, Any]]:
    """
    Get all backup mappings from the database.

    Args:
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        List of mapping dictionaries
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, source, destination, max_versions, compression, enabled,
                       created_at, updated_at
                FROM mappings
                ORDER BY created_at DESC
            """
            )

            rows = cursor.fetchall()
            mappings = []
            for row in rows:
                mappings.append(
                    {
                        "id": row["id"],
                        "source": row["source"],
                        "destination": row["destination"],
                        "maxVersions": row["max_versions"],
                        "compression": row["compression"],
                        "enabled": bool(row["enabled"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

            return mappings

    except Exception as e:
        logger.error("Error getting mappings: %s", e)
        return []


def get_mapping(mapping_id: int, db_path: str = None) -> Optional[Dict[str, Any]]:
    """
    Get a specific mapping by ID.

    Args:
        mapping_id: The ID of the mapping to retrieve
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        Mapping dictionary or None if not found
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, source, destination, max_versions, compression, enabled,
                       created_at, updated_at
                FROM mappings
                WHERE id = ?
            """,
                (mapping_id,),
            )

            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "source": row["source"],
                    "destination": row["destination"],
                    "maxVersions": row["max_versions"],
                    "compression": row["compression"],
                    "enabled": bool(row["enabled"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    except Exception as e:
        logger.error("Error getting mapping %s: %s", mapping_id, e)
        return None


def add_mapping(
    source: str,
    destination: str,
    max_versions: int = 3,
    compression: str = "none",
    enabled: bool = True,
    db_path: str = None,
) -> Optional[int]:
    """
    Add a new backup mapping to the database.

    Args:
        source: Source folder path
        destination: Destination folder path
        max_versions: Maximum number of backup versions to keep
        compression: Compression type ('none', 'zip', 'tar')
        enabled: Whether the mapping is enabled
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        ID of the created mapping, or None if creation failed
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO mappings (source, destination, max_versions, compression, enabled)
                VALUES (?, ?, ?, ?, ?)
            """,
                (source, destination, max_versions, compression, 1 if enabled else 0),
            )

            mapping_id = cursor.lastrowid
            logger.info("Added mapping %s: %s -> %s", mapping_id, source, destination)
            return mapping_id

    except sqlite3.IntegrityError as e:
        logger.error("Mapping already exists: %s", e)
        return None
    except Exception as e:
        logger.error("Error adding mapping: %s", e)
        return None


def update_mapping(
    mapping_id: int,
    source: str = None,
    destination: str = None,
    max_versions: int = None,
    compression: str = None,
    enabled: bool = None,
    db_path: str = None,
) -> bool:
    """
    Update an existing backup mapping.

    Args:
        mapping_id: ID of the mapping to update
        source: New source path (optional)
        destination: New destination path (optional)
        max_versions: New max versions (optional)
        compression: New compression type (optional)
        enabled: New enabled status (optional)
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        True if update was successful, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Build update query dynamically based on provided parameters
            updates = []
            params = []

            if source is not None:
                updates.append("source = ?")
                params.append(source)
            if destination is not None:
                updates.append("destination = ?")
                params.append(destination)
            if max_versions is not None:
                updates.append("max_versions = ?")
                params.append(max_versions)
            if compression is not None:
                updates.append("compression = ?")
                params.append(compression)
            if enabled is not None:
                updates.append("enabled = ?")
                params.append(1 if enabled else 0)

            if not updates:
                return False  # No updates to make

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(mapping_id)

            query = f"UPDATE mappings SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            if cursor.rowcount > 0:
                logger.info("Updated mapping %s", mapping_id)
                return True
            else:
                logger.warning("Mapping %s not found for update", mapping_id)
                return False

    except Exception as e:
        logger.error("Error updating mapping %s: %s", mapping_id, e)
        return False


def delete_mapping(mapping_id: int, db_path: str = None) -> bool:
    """
    Delete a backup mapping from the database.

    Args:
        mapping_id: ID of the mapping to delete
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        True if deletion was successful, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mappings WHERE id = ?", (mapping_id,))

            if cursor.rowcount > 0:
                logger.info("Deleted mapping %s", mapping_id)
                return True
            else:
                logger.warning("Mapping %s not found for deletion", mapping_id)
                return False

    except Exception as e:
        logger.error("Error deleting mapping %s: %s", mapping_id, e)
        return False


def add_backup_history(
    mapping_id: Optional[int],
    success: bool,
    message: str,
    duration: float = None,
    size_bytes: int = None,
    backup_path: str = None,
    timestamp: str = None,
    db_path: str = None,
) -> Optional[int]:
    """
    Add a backup history entry.

    Args:
        mapping_id: ID of the mapping (can be None for manual backups)
        success: Whether the backup was successful
        message: Backup result message
        duration: Backup duration in seconds (optional)
        size_bytes: Size of the backup in bytes (optional)
        backup_path: Path to the backup location (optional)
        timestamp: Custom timestamp (optional, defaults to current time)
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        ID of the created history entry, or None if creation failed
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO backup_history 
                (mapping_id, success, message, duration, size_bytes, backup_path, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    mapping_id,
                    1 if success else 0,
                    message,
                    duration,
                    size_bytes,
                    backup_path,
                    timestamp or datetime.now().isoformat(),
                ),
            )

            history_id = cursor.lastrowid
            logger.debug("Added backup history entry %s", history_id)
            return history_id

    except Exception as e:
        logger.error("Error adding backup history: %s", e)
        return None


def get_backup_history(
    limit: int = 50, mapping_id: Optional[int] = None, db_path: str = None
) -> List[Dict[str, Any]]:
    """
    Get backup history entries.

    Args:
        limit: Maximum number of entries to return
        mapping_id: Filter by mapping ID (optional)
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        List of backup history dictionaries
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            if mapping_id is not None:
                cursor.execute(
                    """
                    SELECT id, mapping_id, timestamp, success, message, duration,
                           size_bytes, backup_path
                    FROM backup_history
                    WHERE mapping_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (mapping_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, mapping_id, timestamp, success, message, duration,
                           size_bytes, backup_path
                    FROM backup_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (limit,),
                )

            rows = cursor.fetchall()
            history = []
            for row in rows:
                history.append(
                    {
                        "id": row["id"],
                        "mapping_id": row["mapping_id"],
                        "timestamp": row["timestamp"],
                        "success": bool(row["success"]),
                        "message": row["message"],
                        "duration": row["duration"],
                        "size_bytes": row["size_bytes"],
                        "backup_path": row["backup_path"],
                    }
                )

            return history

    except Exception as e:
        logger.error("Error getting backup history: %s", e)
        return []


def get_backup_settings(db_path: str = None) -> Dict[str, str]:
    """
    Get all backup settings.

    Args:
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        Dictionary of settings (key-value pairs)
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM backup_settings")

            rows = cursor.fetchall()
            settings = {}
            for row in rows:
                settings[row["key"]] = row["value"]

            return settings

    except Exception as e:
        logger.error("Error getting backup settings: %s", e)
        return {}


def get_backup_setting(key: str, default: str = None, db_path: str = None) -> Optional[str]:
    """
    Get a specific backup setting by key.

    Args:
        key: Setting key
        default: Default value if setting doesn't exist
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        Setting value or default if not found
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM backup_settings WHERE key = ?", (key,))

            row = cursor.fetchone()
            if row:
                return row["value"]
            return default

    except Exception as e:
        logger.error("Error getting backup setting %s: %s", key, e)
        return default


def set_backup_setting(key: str, value: str, db_path: str = None) -> bool:
    """
    Set a backup setting.

    Args:
        key: Setting key
        value: Setting value
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        True if setting was saved successfully, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO backup_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (key, value),
            )

            logger.debug("Set backup setting %s = %s", key, value)
            return True

    except Exception as e:
        logger.error("Error setting backup setting %s: %s", key, e)
        return False


def set_backup_settings(settings: Dict[str, str], db_path: str = None) -> bool:
    """
    Set multiple backup settings at once.

    Args:
        settings: Dictionary of settings (key-value pairs)
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        True if all settings were saved successfully, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            for key, value in settings.items():
                cursor.execute(
                    """
                    INSERT INTO backup_settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (key, str(value)),
                )

            logger.debug("Set %d backup settings", len(settings))
            return True

    except Exception as e:
        logger.error("Error setting backup settings: %s", e)
        return False


def get_database_version(db_path: str = None) -> int:
    """
    Get the current database version.

    Args:
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        Database version number, or 0 if not found
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM database_version ORDER BY version DESC LIMIT 1")

            row = cursor.fetchone()
            if row:
                return row["version"]
            return 0

    except Exception as e:
        logger.error("Error getting database version: %s", e)
        return 0


def cleanup_old_backup_history(days: int = 90, db_path: str = None) -> int:
    """
    Remove backup history entries older than specified days.

    Args:
        days: Number of days to keep history
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        Number of entries deleted
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM backup_history
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """,
                (days,),
            )

            deleted_count = cursor.rowcount
            if deleted_count > 0:
                logger.info("Cleaned up %d old backup history entries", deleted_count)
            return deleted_count

    except Exception as e:
        logger.error("Error cleaning up backup history: %s", e)
        return 0
