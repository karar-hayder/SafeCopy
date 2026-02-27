import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "safecopy.db"
DB_VERSION = 1


@contextmanager
def get_db_connection(db_path: str = None):
    """
    Context manager for database connections.
    Establishes and returns a connection to the SQLite database at the given path.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        # Return a dictionary per row to allow attribute-style, key-style, and .get
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        conn.execute("PRAGMA foreign_keys=ON")
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
    Returns True if initialization was successful, False otherwise.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    source TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    max_versions INTEGER DEFAULT 3,
                    compression TEXT DEFAULT 'none',
                    enabled INTEGER DEFAULT 1,
                    encrypted INTEGER DEFAULT 0,
                    passwd_mode TEXT DEFAULT 'none',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(uuid, source, destination)
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
            cursor.execute("PRAGMA table_info(backup_verification)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "verification_msg" not in columns:
                try:
                    cursor.execute(
                        "ALTER TABLE backup_verification ADD COLUMN verification_msg TEXT"
                    )
                except Exception as e:
                    logger.error(
                        "Failed to add verification_msg column to backup_verification: %s",
                        e,
                    )

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

            cursor.execute(
                "SELECT version FROM database_version ORDER BY version DESC LIMIT 1"
            )
            current_version_row = cursor.fetchone()
            current_version = (
                current_version_row["version"] if current_version_row else 0
            )

            if current_version < DB_VERSION:
                logger.info(
                    "Migrating database from version %s to %s",
                    current_version,
                    DB_VERSION,
                )
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
    Retrieve all backup mappings from the database.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
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
                        "uuid": row["uuid"],
                        "source": row["source"],
                        "destination": row["destination"],
                        "maxVersions": row["max_versions"],
                        "compression": row["compression"],
                        "enabled": bool(row["enabled"]),
                        "encrypted": bool(row["encrypted"]),
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
    Retrieve a specific mapping by ID.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM mappings
                WHERE id = ?
            """,
                (mapping_id,),
            )

            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "uuid": row["uuid"],
                    "source": row["source"],
                    "destination": row["destination"],
                    "max_versions": row["max_versions"],
                    "compression": row["compression"],
                    "enabled": bool(row["enabled"]),
                    "encrypted": bool(row["encrypted"]),
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
    encrypted: bool = False,
    uuid_str: str = None,
    db_path: str = None,
) -> Optional[int]:
    """
    Add a new backup mapping to the database.
    Returns ID of the created mapping or None if it fails.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO mappings (uuid, source, destination, max_versions, compression, enabled, encrypted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    uuid_str or str(uuid.uuid4()),
                    source,
                    destination,
                    max_versions,
                    compression,
                    1 if enabled else 0,
                    1 if encrypted else 0,
                ),
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
    encrypted: bool = None,
    db_path: str = None,
) -> bool:
    """
    Update an existing backup mapping. Returns True if updated, False otherwise.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

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
            if encrypted is not None:
                updates.append("encrypted = ?")
                params.append(1 if encrypted else 0)

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(mapping_id)

            query = f"UPDATE mappings SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            if cursor.rowcount > 0:
                logger.info("Updated mapping %s", mapping_id)
                return True
            return False

    except Exception as e:
        logger.error("Error updating mapping %s: %s", mapping_id, e)
        return False


def delete_mapping(mapping_id: int, db_path: str = None) -> bool:
    """
    Delete a backup mapping from the database. Returns True if deleted, False otherwise.
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
    Add a backup history entry. Returns the ID of the new entry or None if it fails.
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
            return history_id

    except Exception as e:
        logger.error("Error adding backup history: %s", e)
        return None


def get_backup_history(
    limit: int = 50, mapping_id: Optional[int] = None, db_path: str = None
) -> List[Dict[str, Any]]:
    """
    Get backup history entries. Returns a list of backup history dictionaries.
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
    Retrieve all backup settings as key-value pairs.
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


def get_backup_setting(
    key: str, default: str = None, db_path: str = None
) -> Optional[str]:
    """
    Retrieve a specific backup setting by key. Returns the value or default.
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
    Set a backup setting. Returns True if successful, False otherwise.
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
            return True

    except Exception as e:
        logger.error("Error setting backup setting %s: %s", key, e)
        return False


def set_backup_settings(settings: Dict[str, str], db_path: str = None) -> bool:
    """
    Set multiple backup settings at once. Returns True if all were set successfully.
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
            return True

    except Exception as e:
        logger.error("Error setting backup settings: %s", e)
        return False


def get_database_version(db_path: str = None) -> int:
    """
    Get the current database version. Returns version number or 0 if not found.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT version FROM database_version ORDER BY version DESC LIMIT 1"
            )

            row = cursor.fetchone()
            if row:
                return row["version"]
            return 0

    except Exception as e:
        logger.error("Error getting database version: %s", e)
        return 0


def cleanup_old_backup_history(days: int = 90, db_path: str = None) -> int:
    """
    Remove backup history entries older than specified days. Returns number deleted.
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
