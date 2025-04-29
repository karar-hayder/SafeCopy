import shutil
import os
import time
import logging
from datetime import datetime
from safecopy.config import load_config, save_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("safecopy.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def perform_backup():
    """
    Perform backup operations for all configured mappings.
    Returns a list of successful and failed backups.
    """
    config = load_config()
    successful_backups = []
    failed_backups = []

    if not config["mappings"]:
        logger.warning("No backup mappings configured.")
        return successful_backups, failed_backups

    for mapping in config["mappings"]:
        src = mapping["source"]
        dst = mapping["destination"]

        try:
            if not os.path.exists(src):
                logger.error(f"Source path {src} does not exist.")
                failed_backups.append((src, dst, "Source path does not exist"))
                continue

            if not os.path.exists(dst):
                logger.info(f"Creating destination directory: {dst}")
                os.makedirs(dst)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst_folder = os.path.join(dst, f"backup_{timestamp}")

            logger.info(f"Starting backup from {src} to {dst_folder}")
            start_time = time.time()

            # Perform the backup
            shutil.copytree(src, dst_folder)

            end_time = time.time()
            duration = end_time - start_time

            # Calculate size of backup
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(dst_folder)
                for filename in filenames
            )
            size_mb = total_size / (1024 * 1024)

            success_msg = f"Backup from {src} to {dst_folder} completed in {duration:.2f} seconds. Size: {size_mb:.2f} MB"
            logger.info(success_msg)

            # Add to successful backups
            successful_backups.append((src, dst_folder))

            # Update config with action
            config["last_actions"].append(success_msg)

        except Exception as e:
            error_msg = f"Backup from {src} to {dst} failed: {str(e)}"
            logger.error(error_msg)
            failed_backups.append((src, dst, str(e)))
            config["last_actions"].append(error_msg)

    # Save the updated config
    save_config(config)

    # Log summary
    logger.info(
        f"Backup operation completed. Successful: {len(successful_backups)}, Failed: {len(failed_backups)}"
    )

    return successful_backups, failed_backups
