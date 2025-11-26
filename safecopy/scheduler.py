import logging
import threading
import time
from datetime import datetime

from safecopy.backup import perform_backup
from safecopy.config import load_config, save_config
from safecopy.utils import get_available_drives

# Configure logging
logger = logging.getLogger(__name__)


def backup_func():
    """
    Perform backup operations for all valid mappings.
    Returns True if at least one backup was successful, False otherwise.
    """
    config = load_config()
    available_drives = get_available_drives()

    # Check each mapping to see if the destination drive is available
    valid_mappings = [
        m for m in config["mappings"] if m["destination"] in available_drives
    ]

    if not valid_mappings:
        logger.warning("No backup drives found or no valid mappings configured.")
        return False

    logger.info(f"Starting scheduled backup. Available drives: {available_drives}")
    successful, failed = perform_backup()

    # Update last backup time in config
    config["last_scheduled_backup"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_config(config)

    return len(successful) > 0


def backup_loop(interval_minutes=10):
    """
    Continuously run backup operations at the specified interval.

    Args:
        interval_minutes: The number of minutes between backup attempts
    """
    logger.info(f"Starting backup scheduler with {interval_minutes} minute interval")

    while True:
        try:
            # Check if we should run the backup
            config = load_config()
            if config.get("mappings"):
                backup_func()
            else:
                logger.info("No backup mappings configured. Skipping scheduled backup.")

            # Sleep until next backup
            logger.debug(f"Next backup scheduled in {interval_minutes} minutes")
            time.sleep(interval_minutes * 60)

        except Exception as e:
            logger.error(f"Error in backup scheduler: {str(e)}")
            # Sleep for a short time before retrying
            time.sleep(60)


def start(interval_minutes=10):
    """
    Start the backup scheduler in a separate thread.

    Args:
        interval_minutes: The number of minutes between backup attempts
    """
    thread = threading.Thread(target=backup_loop, args=(interval_minutes,), daemon=True)
    thread.start()
    logger.info(f"Backup scheduler started with {interval_minutes} minute interval")
