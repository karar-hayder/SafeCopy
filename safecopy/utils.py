import logging
import os
import string

logger = logging.getLogger(__name__)


def get_available_drives():
    """Return a list of available drives (e.g., 'D:/', 'E:/')."""
    if os.name == "nt":  # Windows
        drives = [f"{d}:/" for d in string.ascii_uppercase if os.path.exists(f"{d}:/")]
    else:  # Unix-like systems
        # For Unix-like systems, we'll use common mount points
        drives = ["/", "/home", "/mnt", "/media"]
        # Filter to only existing directories
        drives = [d for d in drives if os.path.exists(d)]

    logger.info("Detected available drives: %s", drives)
    return drives


def is_valid_path(path):
    """
    Check if a path is valid and accessible.

    Args:
        path: The path to check

    Returns:
        bool: True if the path is valid and accessible, False otherwise
    """
    try:
        # Normalize path
        if os.name == "nt":  # Windows
            path = path.replace("/", "\\")

        # Check if path exists and is a directory
        return os.path.exists(path) and os.path.isdir(path)
    except Exception as e:
        logger.error("Error checking path validity: %s", str(e))
        return False


def get_folder_size(path):
    """
    Calculate the total size of a folder in bytes.

    Args:
        path: The path to the folder

    Returns:
        int: The total size in bytes
    """
    total_size = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception as e:
        logger.error("Error calculating folder size: %s", str(e))

    return total_size


def format_size(size_bytes):
    """
    Format a size in bytes to a human-readable string.

    Args:
        size_bytes: The size in bytes

    Returns:
        str: A human-readable size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
