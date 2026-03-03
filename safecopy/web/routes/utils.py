import os

from flask import request
from flask_login import login_required

from safecopy.utils import format_size, get_available_drives, get_folder_size
from safecopy.web.api_utils import standard_response


@login_required
def browse_folders():
    """Browse folders on the server for the file browser dialog."""
    try:
        path = request.args.get("path", "/")

        if path == "/" or path == "":
            drives = get_available_drives()
            return standard_response(True, data={"drives": drives, "folders": []})

        if os.name == "nt":
            path = path.replace("/", "\\")

        if not os.path.exists(path) or not os.path.isdir(path):
            return standard_response(
                False,
                error="Path does not exist or is not a directory",
                status_code=400,
            )

        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        return standard_response(True, data={"folders": sorted(folders)})
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def folder_preview():
    """Get a preview of the contents of a folder."""
    try:
        path = request.args.get("path", "")

        if not path:
            return standard_response(False, error="No path provided", status_code=400)

        if os.name == "nt":
            path = path.replace("/", "\\")

        if not os.path.exists(path) or not os.path.isdir(path):
            return standard_response(
                False,
                error="Path does not exist or is not a directory",
                status_code=400,
            )

        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        size = get_folder_size(path)
        size_formatted = format_size(size)
        data = {
            "files": sorted(files),
            "folders": sorted(folders),
            "size": size_formatted,
        }
        return standard_response(True, data=data)
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)
