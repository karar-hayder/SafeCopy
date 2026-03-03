from flask import redirect, session, url_for

from safecopy.db.services.userService import UserService
from safecopy.utils import get_available_drives


def is_logged_in():
    return session.get("user_authenticated", False)


def get_current_username():
    return session.get("username")


def is_auth_enabled():
    return True


def check_auth_required():
    if is_auth_enabled() and not is_logged_in():
        return redirect(url_for("login"))
    return None


def get_settings():
    username = get_current_username()
    if not username:
        return None
    config = UserService()
    user = config.get_user_by_username(username)
    return user.settings if user else None


def get_drives():
    drives = get_available_drives()
    return drives
