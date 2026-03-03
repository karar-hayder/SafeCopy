import logging
import os
import threading
import time
from datetime import datetime
from typing import Set

try:
    import schedule  # type: ignore
except ImportError:
    schedule = None
    logging.warning(
        "The 'schedule' package could not be imported. Scheduling features will be unavailable."
    )

from safecopy.backup.dtos import BackupConfig
from safecopy.backup.runner import run_backup
from safecopy.db.services.backupSchedulesService import BackupSchedulesService
from safecopy.db.services.mappingsService import MappingsService
from safecopy.utils import get_available_drives

logger = logging.getLogger(__name__)

mappings_service = MappingsService()
schedules_service = BackupSchedulesService()


def run_scheduled_backup(mapping_uuid: str):
    """Run a backup for a scheduled mapping."""
    try:
        mapping = mappings_service.get_by_uuid(mapping_uuid)
        if not mapping:
            logger.error("Mapping %s not found for scheduled backup", mapping_uuid)
            return

        logger.info(
            "Running scheduled backup for mapping: %s -> %s",
            mapping.source,
            mapping.destination,
        )

        from safecopy.backup.enums import CompressionType as BackupCompressionType

        # Handle compression enum conversion from DB string/enum to Backup enum
        comp_str = (
            mapping.compression.value
            if hasattr(mapping.compression, "value")
            else str(mapping.compression)
        )
        try:
            comp_type = next(
                c for c in BackupCompressionType if c.value[0] == comp_str.lower()
            )
        except StopIteration:
            comp_type = BackupCompressionType.NONE

        # Convert ResponseDTO/Model to BackupConfig
        config = BackupConfig(
            uuid=mapping.uuid,
            user_uuid=mapping.user_uuid,
            source=mapping.source,
            destination=mapping.destination,
            compression=comp_type,
            encrypted=mapping.encrypted,
            passwd="",  # Scheduler currently doesn't have access to keys unless they are in DB or User settings
            max_versions=mapping.max_versions or 3,
        )

        success, message = run_backup(config)
        logger.info("Scheduled backup completed: %s", message)
    except Exception as e:
        logger.error("Error running scheduled backup: %s", e)


def _schedule_job_key(
    mapping_uuid: str, schedule_type: str, schedule_value: str
) -> str:
    """Returns a unique key for a job."""
    return f"{mapping_uuid}::{schedule_type}::{schedule_value}"


def setup_schedule_job(
    mapping_uuid: str,
    schedule_type: str,
    schedule_value: str,
    scheduled_keys: Set[str] = None,
):
    """Setup a schedule job using the schedule library."""
    if not schedule:
        return

    try:
        job_key = _schedule_job_key(mapping_uuid, schedule_type, schedule_value)
        if scheduled_keys is not None:
            if job_key in scheduled_keys:
                return
            scheduled_keys.add(job_key)

        if schedule_type == "daily":
            hour, minute = map(int, schedule_value.split(":"))
            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                run_scheduled_backup, mapping_uuid=mapping_uuid
            )

        elif schedule_type == "weekly":
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
                        run_scheduled_backup, mapping_uuid=mapping_uuid
                    )

        elif schedule_type == "monthly":
            parts = schedule_value.split()
            if len(parts) >= 2:
                day_num = int(parts[0])
                time_str = parts[1]
                hour, minute = map(int, time_str.split(":"))

                def monthly_job():
                    if datetime.now().day == day_num:
                        run_scheduled_backup(mapping_uuid)

                schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(monthly_job)

        elif schedule_type == "interval" or schedule_type == "minutes":
            interval_minutes = int(schedule_value)
            schedule.every(interval_minutes).minutes.do(
                run_scheduled_backup, mapping_uuid=mapping_uuid
            )

        elif schedule_type == "hourly":
            minutes_offset = int(schedule_value) if schedule_value else 0
            schedule.every().hour.at(f":{minutes_offset:02d}").do(
                run_scheduled_backup, mapping_uuid=mapping_uuid
            )

    except Exception as e:
        logger.error("Error setting up schedule: %s", e)


def setup_all_schedules():
    """Setup all schedules from database."""
    if not schedule:
        return

    schedule.clear()
    try:
        scheduled_keys = set()
        active_mappings = {
            m.uuid: m for m in mappings_service.get_all(enabled=True, page_size=0)
        }
        available_drives = get_available_drives()

        # Batch fetch all enabled schedules
        all_schedules = schedules_service.get_all(enabled=True, page_size=0)

        for sched in all_schedules:
            mapping = active_mappings.get(sched.mapping_uuid)
            if not mapping:
                continue

            dest_path = mapping.destination
            drive_available = False

            if os.name == "nt":
                drive = os.path.splitdrive(dest_path)[0] + "/"
                drive_available = drive in available_drives
            else:
                for candidate in available_drives:
                    if dest_path.startswith(candidate):
                        drive_available = True
                        break

            if not drive_available:
                logger.debug(
                    "Skipping schedule %s - destination not available", sched.uuid
                )
                continue

            setup_schedule_job(
                mapping.uuid,
                sched.schedule_type,
                sched.schedule_value,
                scheduled_keys=scheduled_keys,
            )

        logger.info("Setup %d scheduled jobs", len(schedule.jobs))
    except Exception as e:
        logger.error("Error setting up schedules: %s", e)


def scheduler_loop():
    """Main scheduler loop."""
    logger.info("Starting advanced backup scheduler")
    setup_all_schedules()

    while True:
        try:
            if schedule:
                schedule.run_pending()
            time.sleep(60)

            # Re-setup schedules every hour
            if datetime.now().minute == 0:
                setup_all_schedules()
        except Exception as e:
            logger.error("Error in scheduler loop: %s", e)
            time.sleep(60)


def start_advanced_scheduler():
    """Start the advanced scheduler in a separate thread."""
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    logger.info("Advanced backup scheduler started")
