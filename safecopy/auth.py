"""
Authentication module for SafeCopy web UI.
"""

import logging
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    UserMixin,
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from safecopy.db.controller import get_db_connection, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


class User(UserMixin):
    """User class for Flask-Login."""

    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    """Load user from database."""
    try:
        with get_db_connection(DEFAULT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username FROM web_auth WHERE id = ? AND enabled = 1", (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return User(row["id"], row["username"])
    except Exception as e:
        logger.error("Error loading user: %s", e)
    return None


def create_user(username: str, password: str, db_path: str = None) -> bool:
    """
    Create a new user account.

    Args:
        username: Username
        password: Plain text password
        db_path: Path to database file

    Returns:
        True if user was created successfully, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        password_hash = generate_password_hash(password)
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO web_auth (username, password_hash)
                VALUES (?, ?)
            """,
                (username, password_hash),
            )
            logger.info("Created user: %s", username)
            return True
    except Exception as e:
        logger.error("Error creating user: %s", e)
        return False


def verify_user(username: str, password: str, db_path: str = None) -> bool:
    """
    Verify user credentials.

    Args:
        username: Username
        password: Plain text password
        db_path: Path to database file

    Returns:
        True if credentials are valid, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash FROM web_auth WHERE username = ? AND enabled = 1",
                (username,),
            )
            row = cursor.fetchone()
            if row and check_password_hash(row["password_hash"], password):
                return True
    except Exception as e:
        logger.error("Error verifying user: %s", e)
    return False


def change_password(
    username: str, old_password: str, new_password: str, db_path: str = None
) -> bool:
    """
    Change user password.

    Args:
        username: Username
        old_password: Current password
        new_password: New password
        db_path: Path to database file

    Returns:
        True if password was changed successfully, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not verify_user(username, old_password, db_path):
        return False

    try:
        new_password_hash = generate_password_hash(new_password)
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE web_auth
                SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            """,
                (new_password_hash, username),
            )
            logger.info("Changed password for user: %s", username)
            return True
    except Exception as e:
        logger.error("Error changing password: %s", e)
        return False


def is_auth_enabled(db_path: str = None) -> bool:
    """
    Check if authentication is enabled (has at least one user).

    Args:
        db_path: Path to database file

    Returns:
        True if authentication is enabled, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM web_auth WHERE enabled = 1")
            row = cursor.fetchone()
            return row["count"] > 0 if row else False
    except Exception as e:
        logger.error("Error checking auth status: %s", e)
        return False
