"""
Advanced backup scheduler with daily, weekly, and monthly support.
"""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

try:
    import schedule  # type: ignore
except ImportError:
    schedule = None
    logging.warning(
        "The 'schedule' package could not be imported. Scheduling features will be unavailable."
    )

from safecopy.backup import run_backup
from safecopy.config import USE_DATABASE, load_config
from safecopy.db.controller import DEFAULT_DB_PATH, get_db_connection, get_mappings
from safecopy.utils import get_available_drives

logger = logging.getLogger(__name__)


def get_schedules_for_mapping(mapping_id: int, db_path: str = None) -> List[Dict]:
    """
    Get all schedules for a mapping.

    Args:
        mapping_id: Mapping ID
        db_path: Path to database file

    Returns:
        List of schedule dictionaries
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, schedule_type, schedule_value, enabled
                FROM backup_schedules
                WHERE mapping_id = ? AND enabled = 1
            """,
                (mapping_id,),
            )
            rows = cursor.fetchall()
            schedules = []
            for row in rows:
                schedules.append(
                    {
                        "id": row["id"],
                        "schedule_type": row["schedule_type"],
                        "schedule_value": row["schedule_value"],
                        "enabled": bool(row["enabled"]),
                    }
                )
            print(schedules)
            return schedules
    except Exception as e:
        logger.error("Error getting schedules: %s", e)
        return []


def add_schedule(
    mapping_id: int,
    schedule_type: str,
    schedule_value: str,
    enabled: bool = True,
    db_path: str = None,
) -> Optional[int]:
    """
    Add a schedule for a mapping.

    Args:
        mapping_id: Mapping ID
        schedule_type: Type of schedule ('daily', 'weekly', 'monthly', 'interval')
        schedule_value: Schedule value (time string, day name, day number, or minutes)
        enabled: Whether schedule is enabled
        db_path: Path to database file

    Returns:
        Schedule ID or None if failed
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO backup_schedules (mapping_id, schedule_type, schedule_value, enabled)
                VALUES (?, ?, ?, ?)
            """,
                (mapping_id, schedule_type, schedule_value, 1 if enabled else 0),
            )
            schedule_id = cursor.lastrowid
            logger.info("Added schedule %s for mapping %s", schedule_id, mapping_id)
            return schedule_id
    except Exception as e:
        logger.error("Error adding schedule: %s", e)
        return None


def delete_schedule(schedule_id: int, db_path: str = None) -> bool:
    """
    Delete a schedule.

    Args:
        schedule_id: Schedule ID
        db_path: Path to database file

    Returns:
        True if deleted successfully
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM backup_schedules WHERE id = ?", (schedule_id,))
            logger.info("Deleted schedule %s", schedule_id)
            return True
    except Exception as e:
        logger.error("Error deleting schedule: %s", e)
        return False


def run_scheduled_backup(mapping: Dict):
    """
    Run a backup for a scheduled mapping.

    Args:
        mapping: Mapping dictionary
    """
    try:
        logger.info(
            "Running scheduled backup for mapping: %s -> %s",
            mapping.get("source"),
            mapping.get("destination"),
        )
        _, message = run_backup(mapping)
        logger.info("Scheduled backup completed: %s", message)
    except Exception as e:
        logger.error("Error running scheduled backup: %s", e)


def _schedule_job_key(mapping: Dict, schedule_type: str, schedule_value: str) -> str:
    """
    Returns a unique key for a job based on mapping id, schedule type, and schedule value.
    """
    return f"{mapping.get('id', '')}::{schedule_type}::{schedule_value}"


def setup_schedule_job(
    mapping: Dict, schedule_type: str, schedule_value: str, scheduled_keys: set = None
):
    """
    Setup a schedule job using the schedule library.

    Args:
        mapping: Mapping dictionary
        schedule_type: Type of schedule
        schedule_value: Schedule value
        scheduled_keys: Set to keep track of unique jobs (optional, used for de-duplication)
    """
    try:
        job_key = _schedule_job_key(mapping, schedule_type, schedule_value)
        if scheduled_keys is not None:
            if job_key in scheduled_keys:
                logger.debug(
                    "Skipping duplicate schedule job (already scheduled): key=%s mapping_id=%s",
                    job_key,
                    mapping.get("id"),
                )
                return
            scheduled_keys.add(job_key)

        if schedule_type == "daily":
            # schedule_value should be in format "HH:MM"
            hour, minute = map(int, schedule_value.split(":"))
            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                run_scheduled_backup, mapping=mapping
            )
            logger.info(
                "Scheduled daily backup at %s for mapping %s",
                schedule_value,
                mapping.get("id"),
            )

        elif schedule_type == "weekly":
            # schedule_value should be day name (monday, tuesday, etc.) and time "day HH:MM"
            parts = schedule_value.split()
            if len(parts) >= 2:
                day_name = parts[0].lower()
                time_str = parts[1]
                hour, minute = map(int, time_str.split(":"))

                day_map = {
                    "monday": schedule.every().monday,
                    "tuesday": schedule.every().tuesday,
                    "wednesday": schedule.every().wednesday,
                    "thursday": schedule.every().thursday,
                    "friday": schedule.every().friday,
                    "saturday": schedule.every().saturday,
                    "sunday": schedule.every().sunday,
                }

                if day_name in day_map:
                    day_map[day_name].at(f"{hour:02d}:{minute:02d}").do(
                        run_scheduled_backup, mapping=mapping
                    )
                    logger.info(
                        "Scheduled weekly backup on %s at %s for mapping %s",
                        day_name,
                        time_str,
                        mapping.get("id"),
                    )

        elif schedule_type == "monthly":
            # schedule_value should be day number and time "DD HH:MM"
            parts = schedule_value.split()
            if len(parts) >= 2:
                day_num = int(parts[0])
                time_str = parts[1]
                hour, minute = map(int, time_str.split(":"))

                def monthly_job():
                    now = datetime.now()
                    if now.day == day_num:
                        run_scheduled_backup(mapping)

                schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(monthly_job)
                logger.info(
                    "Scheduled monthly backup on day %s at %s for mapping %s",
                    day_num,
                    time_str,
                    mapping.get("id"),
                )

        elif schedule_type == "interval":
            # schedule_value should be minutes
            interval_minutes = int(schedule_value)
            schedule.every(interval_minutes).minutes.do(
                run_scheduled_backup, mapping=mapping
            )
            logger.info(
                "Scheduled interval backup every %s minutes for mapping %s",
                interval_minutes,
                mapping.get("id"),
            )

    except Exception as e:
        logger.error("Error setting up schedule: %s", e)


def setup_all_schedules(db_path: str = None):
    """
    Setup all schedules from database.

    Args:
        db_path: Path to database file
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Clear existing schedules
    schedule.clear()

    try:
        scheduled_keys = set()  # To track unique jobs and prevent duplicate scheduling

        if USE_DATABASE:
            mappings = get_mappings(db_path)
            available_drives = get_available_drives()

            for mapping in mappings:
                # Only schedule enabled mappings with available destinations
                if not mapping.get("enabled", True):
                    continue

                dest_path = mapping.get("destination", "")
                drive = None

                if os.name == "nt":
                    # Windows: get drive like 'D:/'
                    drive = os.path.splitdrive(dest_path)[0] + "/"
                    drive_available = drive in available_drives
                else:
                    # Unix: treat root mount/folder, e.g. '/mnt', '/media'
                    drive_available = False
                    for candidate in available_drives:
                        if dest_path.startswith(candidate):
                            drive_available = True
                            break

                if (os.name == "nt" and not drive_available) or (
                    os.name != "nt" and not drive_available
                ):
                    logger.debug(
                        "Skipping mapping %s - destination drive not available",
                        mapping.get("id"),
                    )
                    continue

                schedules = get_schedules_for_mapping(mapping["id"], db_path)
                for sched in schedules:
                    setup_schedule_job(
                        mapping,
                        sched["schedule_type"],
                        sched["schedule_value"],
                        scheduled_keys=scheduled_keys,  # Prevent duplicate scheduling
                    )
        else:
            # Fallback to old interval-based scheduling
            config = load_config()
            mappings = config.get("mappings", [])
            for mapping in mappings:
                # Use default interval scheduling
                setup_schedule_job(
                    mapping, "interval", "10", scheduled_keys=scheduled_keys
                )

        logger.info("Setup %d scheduled jobs", len(schedule.jobs))

    except Exception as e:
        logger.error("Error setting up schedules: %s", e)


def scheduler_loop():
    """Main scheduler loop that runs continuously."""
    logger.info("Starting advanced backup scheduler")

    # Setup initial schedules
    setup_all_schedules()

    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

            # Re-setup schedules every hour in case they changed
            if datetime.now().minute == 0:
                setup_all_schedules()

        except Exception as e:
            logger.error("Error in scheduler loop: %s", e)
            time.sleep(60)


def start_advanced_scheduler():
    """
    Start the advanced scheduler in a separate thread.
    """
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    logger.info("Advanced backup scheduler started")
