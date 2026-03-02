import hashlib
import os
import re
from pathlib import Path


def sanitize_filename(name, max_length=40):
    """
    Sanitize a string to be used as a safe part of a filename.
    Removes unsafe characters and trims the length.
    """
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    if len(name) > max_length:
        name = name[:max_length]
    return name


def scandir_walk(top):
    """
    Walk a directory tree using os.scandir.
    Yields (dirpath, dirs, files).
    """
    top = Path(top)
    dirs, files = [], []
    with os.scandir(top) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                dirs.append(entry.name)
            elif entry.is_file(follow_symlinks=False):
                files.append(entry.name)
    yield str(top), dirs, files
    for d in dirs:
        yield from scandir_walk(top / d)


def _compute_file_checksum(file_path, hasher="md5"):
    """Compute and return checksum for a file."""
    h = hashlib.new(hasher)
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def atomic_file_rename(tmp_path, final_path):
    """
    Atomically move the temporary file to the final location.
    Overwrites the final path if necessary.
    """
    try:
        os.replace(str(tmp_path), str(final_path))
    except Exception as e:
        raise e
