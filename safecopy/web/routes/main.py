from flask import render_template
from flask_login import login_required

from safecopy.utils.webUtils import get_drives, get_settings


def index_route():
    return render_template("index.html")


@login_required
def settings_route():
    try:
        drives = get_drives()
        settings = get_settings()
        return render_template("settings.html", drives=drives, settings=settings)
    except Exception as e:
        return render_template("settings.html", error=str(e))
