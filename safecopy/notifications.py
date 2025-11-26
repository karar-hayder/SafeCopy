"""
Email notification module for SafeCopy.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from safecopy.db.controller import get_db_connection, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def get_email_settings(db_path: str = None) -> Optional[dict]:
    """
    Get email notification settings from database.

    Args:
        db_path: Path to database file

    Returns:
        Dictionary with email settings or None if not configured
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, smtp_server, smtp_port, smtp_username, smtp_password,
                       from_email, to_email, use_tls, enabled
                FROM email_settings
                WHERE enabled = 1
                LIMIT 1
            """
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "smtp_server": row["smtp_server"],
                    "smtp_port": row["smtp_port"],
                    "smtp_username": row["smtp_username"],
                    "smtp_password": row["smtp_password"],
                    "from_email": row["from_email"],
                    "to_email": row["to_email"],
                    "use_tls": bool(row["use_tls"]),
                    "enabled": bool(row["enabled"]),
                }
    except Exception as e:
        logger.error("Error getting email settings: %s", e)
    return None


def save_email_settings(
    smtp_server: str,
    smtp_port: int,
    from_email: str,
    to_email: str,
    smtp_username: str = None,
    smtp_password: str = None,
    use_tls: bool = True,
    enabled: bool = True,
    db_path: str = None,
) -> bool:
    """
    Save email notification settings.

    Args:
        smtp_server: SMTP server address
        smtp_port: SMTP server port
        from_email: Sender email address
        to_email: Recipient email address
        smtp_username: SMTP username (optional)
        smtp_password: SMTP password (optional)
        use_tls: Use TLS encryption
        enabled: Enable email notifications
        db_path: Path to database file

    Returns:
        True if settings were saved successfully, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            # Delete existing settings and insert new one
            cursor.execute("DELETE FROM email_settings")
            cursor.execute(
                """
                INSERT INTO email_settings
                (smtp_server, smtp_port, smtp_username, smtp_password,
                 from_email, to_email, use_tls, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    smtp_server,
                    smtp_port,
                    smtp_username,
                    smtp_password,
                    from_email,
                    to_email,
                    1 if use_tls else 0,
                    1 if enabled else 0,
                ),
            )
            logger.info("Saved email settings")
            return True
    except Exception as e:
        logger.error("Error saving email settings: %s", e)
        return False


def send_email(
    subject: str,
    body: str,
    to_email: str = None,
    db_path: str = None,
) -> bool:
    """
    Send an email notification.

    Args:
        subject: Email subject
        body: Email body (HTML or plain text)
        to_email: Recipient email (overrides settings if provided)
        db_path: Path to database file

    Returns:
        True if email was sent successfully, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    settings = get_email_settings(db_path)
    if not settings or not settings["enabled"]:
        logger.debug("Email notifications not configured or disabled")
        return False

    recipient = to_email or settings["to_email"]

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings["from_email"]
        msg["To"] = recipient

        # Add body
        msg.attach(MIMEText(body, "html"))

        # Connect to SMTP server
        if settings["use_tls"]:
            server = smtplib.SMTP(settings["smtp_server"], settings["smtp_port"])
            server.starttls()
        else:
            server = smtplib.SMTP(settings["smtp_server"], settings["smtp_port"])

        # Authenticate if credentials provided
        if settings["smtp_username"] and settings["smtp_password"]:
            server.login(settings["smtp_username"], settings["smtp_password"])

        # Send email
        server.send_message(msg)
        server.quit()

        logger.info("Email sent successfully to %s", recipient)
        return True

    except Exception as e:
        logger.error("Error sending email: %s", e)
        return False


def send_backup_notification(
    success: bool,
    mapping_source: str,
    mapping_destination: str,
    message: str,
    duration: float = None,
    size_bytes: int = None,
    db_path: str = None,
) -> bool:
    """
    Send a backup completion notification email.

    Args:
        success: Whether backup was successful
        mapping_source: Source path
        mapping_destination: Destination path
        message: Backup result message
        duration: Backup duration in seconds
        size_bytes: Backup size in bytes
        db_path: Path to database file

    Returns:
        True if email was sent successfully, False otherwise
    """
    status = "SUCCESS" if success else "FAILED"
    status_color = "#28a745" if success else "#dc3545"

    # Format duration
    duration_str = ""
    if duration:
        if duration < 60:
            duration_str = f"{duration:.2f} seconds"
        elif duration < 3600:
            duration_str = f"{duration / 60:.2f} minutes"
        else:
            duration_str = f"{duration / 3600:.2f} hours"

    # Format size
    size_str = ""
    if size_bytes:
        if size_bytes < 1024:
            size_str = f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    subject = f"SafeCopy Backup {status}: {mapping_source}"

    body = f"""
    <html>
      <body>
        <h2 style="color: {status_color};">Backup {status}</h2>
        <p><strong>Source:</strong> {mapping_source}</p>
        <p><strong>Destination:</strong> {mapping_destination}</p>
        <p><strong>Status:</strong> <span style="color: {status_color};">{status}</span></p>
        <p><strong>Message:</strong> {message}</p>
        {f'<p><strong>Duration:</strong> {duration_str}</p>' if duration_str else ''}
        {f'<p><strong>Size:</strong> {size_str}</p>' if size_str else ''}
      </body>
    </html>
    """

    return send_email(subject, body, db_path=db_path)
