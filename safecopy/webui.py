import os
import json
import logging
import shutil

from flask import Flask, render_template, request, redirect, flash, jsonify, session, url_for
from flask_caching import Cache

from safecopy.config import (
    load_config,
    save_config,
    CONFIG_FILE,
    CONFIG_BACKUP,
    DEFAULT_CONFIG,
    USE_DATABASE,
    SECRET_KEY,
)
from safecopy.utils import get_available_drives, get_folder_size, format_size
from safecopy.backup import run_backup as backup_run_backup
from safecopy.auth import login_manager, verify_user, is_auth_enabled, User
from safecopy import notifications, advanced_scheduler

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)
app.config["CACHE_TYPE"] = "simple"
app.config["SECRET_KEY"] = SECRET_KEY
cache = Cache(app)
login_manager.init_app(app)
logger = logging.getLogger(__name__)

# --- Custom session-based auth instead of Flask-Login ---


def is_logged_in():
    """Return True if session indicates authentication."""
    return session.get("user_authenticated", False)


def get_current_username():
    """Get the logged-in username from session."""
    return session.get("username")


def check_auth_required():
    """Check authentication with session cookies."""
    if is_auth_enabled() and not is_logged_in():
        return redirect(url_for("login"))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page using session."""
    if not is_auth_enabled():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if verify_user(username, password):
            from safecopy.db.controller import get_db_connection, DEFAULT_DB_PATH

            with get_db_connection(DEFAULT_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM web_auth WHERE username = ?", (username,))
                row = cursor.fetchone()
                user_id = row["id"] if row else 1

            session["user_authenticated"] = True
            session["username"] = username
            session["user_id"] = user_id
            flash("Logged in successfully", "success")
            next_page = request.args.get("next") or url_for("index")
            return redirect(next_page)
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout page: destroy session."""
    session.pop("user_authenticated", None)
    session.pop("username", None)
    session.pop("user_id", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


@app.route("/")
def index():
    """Render the dashboard page."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check
    return render_template("index.html")


@app.route("/settings")
def settings():
    """Render the settings page."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check
    try:
        drives = get_available_drives()
        config = load_config()
        return render_template("settings.html", config=config, drives=drives)
    except Exception as e:
        logger.error("Error loading settings page: %s", e)
        try:
            if os.path.exists(CONFIG_BACKUP):
                shutil.copy(CONFIG_BACKUP, CONFIG_FILE)
                logger.info("Restored config from backup: %s", CONFIG_BACKUP)
            else:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.info("Created new config file after corruption: %s", CONFIG_FILE)
            config = load_config()
            drives = get_available_drives()
            return render_template("settings.html", config=config, drives=drives)
        except Exception as e2:
            logger.error("Failed to recover from config error: %s", e2)
            return render_template("settings.html", config=DEFAULT_CONFIG, drives=[])


@app.route("/get_mappings")
def get_mappings():
    """Get all mappings from the configuration."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    if USE_DATABASE:
        from safecopy.db.controller import get_mappings as db_get_mappings

        mappings = db_get_mappings()
        mappings_list = []
        for mapping in mappings:
            mappings_list.append(
                {
                    "id": mapping["id"],
                    "source": mapping["source"],
                    "destination": mapping["destination"],
                    "maxVersions": mapping["maxVersions"],
                    "compression": mapping["compression"],
                    "enabled": mapping.get("enabled", True),
                }
            )
        return jsonify({"mappings": mappings_list})
    else:
        config = load_config()
        mappings_with_ids = []
        for idx, mapping in enumerate(config["mappings"]):
            mapping_copy = mapping.copy()
            mapping_copy["id"] = idx
            mappings_with_ids.append(mapping_copy)
        return jsonify({"mappings": mappings_with_ids})


@app.route("/save_mappings", methods=["POST"])
def save_mappings():
    """Save mappings to the configuration."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check
    try:
        data = request.get_json()
        if not data or "mappings" not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        config = load_config()
        if config["mappings"] != data["mappings"]:
            config["mappings"] = data["mappings"]

            if not save_config(config):
                return (
                    jsonify({"success": False, "error": "Failed to save configuration"}),
                    500,
                )

        return jsonify({"success": True})
    except Exception as e:
        logger.error("Error saving mappings: %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/delete_mapping", methods=["POST"])
def delete_mapping_route():
    """Delete a mapping by index (for JSON) or ID (for database)."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check
    if USE_DATABASE:
        from safecopy.db.controller import (
            get_mappings as db_get_mappings,
            delete_mapping as db_delete_mapping,
        )

        try:
            mapping_id = int(request.form.get("id", request.form.get("index", -1)))
            mappings = db_get_mappings()
            if mapping_id > 0:
                mapping = next((m for m in mappings if m["id"] == mapping_id), None)
            else:
                index = int(request.form.get("index", -1))
                if 0 <= index < len(mappings):
                    mapping = mappings[index]
                    mapping_id = mapping["id"]
                else:
                    mapping = None

            if mapping and db_delete_mapping(mapping_id):
                flash(
                    f"Mapping from {mapping['source']} to {mapping['destination']} deleted.",
                    "success",
                )
            else:
                flash("Mapping not found.", "danger")
        except (ValueError, KeyError) as e:
            logger.error("Error deleting mapping: %s", e)
            flash("Invalid mapping identifier.", "danger")
    else:
        index = int(request.form["index"])
        config = load_config()

        if 0 <= index < len(config["mappings"]):
            deleted_mapping = config["mappings"].pop(index)
            save_config(config)
            flash(
                f"Mapping from {deleted_mapping['source']} to {deleted_mapping['destination']} deleted.",
                "success",
            )
        else:
            flash("Invalid mapping index.", "danger")

    return redirect("/")


@app.route("/run_backup", methods=["POST"])
def run_backup():
    """Run all configured backups present in received 'mappings'."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check
    try:
        data = request.get_json()
        mappings = data.get("mappings", [])

        if not mappings:
            return jsonify({"success": False, "error": "No backup mappings configured"})

        results = []
        for mapping in mappings:
            source = mapping.get("source")
            destination = mapping.get("destination")
            max_versions = mapping.get("max_versions", 3)
            compression = mapping.get("compression", "none")

            try:
                mapping_dict = {
                    "source": source,
                    "destination": destination,
                    "maxVersions": max_versions,
                    "compression": compression,
                }
                success, message = backup_run_backup(mapping_dict)
                results.append(
                    {
                        "source": source,
                        "success": success,
                        "message": message if success else f"Backup failed: {message}",
                    }
                )
            except Exception as e:
                results.append({"source": source, "success": False, "error": str(e)})

        successful_backups = [r for r in results if r["success"]]
        if not successful_backups:
            return jsonify(
                {
                    "success": False,
                    "error": "All backups failed",
                    "details": "\n".join([f"{r['source']}: {r['error']}" for r in results]),
                }
            )
        elif len(successful_backups) < len(results):
            return jsonify(
                {
                    "success": True,
                    "message": "Some backups completed successfully",
                    "details": "\n".join(
                        [f"{r['source']}: {r.get('message', r.get('error'))}" for r in results]
                    ),
                }
            )
        else:
            return jsonify({"success": True, "message": "All backups completed successfully"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/browse_folders")
def browse_folders():
    """Browse folders on the server for the file browser dialog."""
    path = request.args.get("path", "/")

    if path == "/" or path == "":
        drives = get_available_drives()
        return jsonify({"drives": drives, "folders": []})

    if os.name == "nt":
        path = path.replace("/", "\\")

    if not os.path.exists(path) or not os.path.isdir(path):
        return jsonify({"error": "Path does not exist or is not a directory"}), 400

    try:
        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        return jsonify({"folders": sorted(folders)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/folder_preview")
def folder_preview():
    """Get a preview of the contents of a folder."""
    path = request.args.get("path", "")

    if not path:
        return jsonify({"error": "No path provided"}), 400

    if os.name == "nt":
        path = path.replace("/", "\\")

    if not os.path.exists(path) or not os.path.isdir(path):
        return jsonify({"error": "Path does not exist or is not a directory"}), 400

    try:
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        size = get_folder_size(path)
        size_formatted = format_size(size)
        return jsonify({"files": sorted(files), "folders": sorted(folders), "size": size_formatted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_backup_settings", methods=["GET"])
def get_backup_settings():
    """Get the current backup settings."""
    config = load_config()
    settings_val = config.get("backup_settings", {"maxVersions": 3, "compression": "none"})
    return jsonify({"success": True, "settings": settings_val})


@app.route("/save_backup_settings", methods=["POST"])
def save_backup_settings():
    """Save the backup settings."""
    try:
        data = request.get_json()
        settings_val = data.get("settings", {})

        config = load_config()
        if config["backup_settings"] != settings_val:
            config["backup_settings"] = settings_val

            if not save_config(config):
                return (
                    jsonify({"success": False, "error": "Failed to save configuration"}),
                    500,
                )

        return jsonify({"success": True})
    except Exception as e:
        logger.error("Error saving backup settings: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/get_backup_history")
def get_backup_history_route():
    """Get backup history from database or config."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    try:
        if USE_DATABASE:
            from safecopy.db.controller import get_backup_history

            limit = int(request.args.get("limit", 50))
            history = get_backup_history(limit=limit)
            return jsonify({"success": True, "history": history})
        else:
            config = load_config()
            history = config.get("last_actions", [])
            history_list = []
            for entry in history:
                if isinstance(entry, dict):
                    history_list.append(
                        {
                            "id": None,
                            "mapping_id": None,
                            "timestamp": entry.get("timestamp", ""),
                            "success": entry.get("success", True),
                            "message": entry.get("message", ""),
                            "duration": None,
                            "size_bytes": None,
                            "backup_path": None,
                        }
                    )
            return jsonify({"success": True, "history": history_list})
    except Exception as e:
        logger.error("Error getting backup history: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/email_settings", methods=["GET", "POST"])
def email_settings():
    """Get or save email notification settings."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    if request.method == "GET":
        settings = notifications.get_email_settings()
        return jsonify({"success": True, "settings": settings or {}})
    else:
        try:
            data = request.get_json()
            success = notifications.save_email_settings(
                smtp_server=data.get("smtp_server"),
                smtp_port=int(data.get("smtp_port", 587)),
                from_email=data.get("from_email"),
                to_email=data.get("to_email"),
                smtp_username=data.get("smtp_username"),
                smtp_password=data.get("smtp_password"),
                use_tls=data.get("use_tls", True),
                enabled=data.get("enabled", True),
            )
            return jsonify({"success": success})
        except Exception as e:
            logger.error("Error saving email settings: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/schedules", methods=["GET"])
def get_schedules():
    """Get all schedules for a mapping."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    try:
        mapping_id_str = request.args.get("mapping_id")
        if not mapping_id_str or mapping_id_str == "":
            return jsonify({"success": False, "error": "mapping_id is required"}), 400
        mapping_id = int(mapping_id_str)
        schedules = advanced_scheduler.get_schedules_for_mapping(mapping_id)
        return jsonify({"success": True, "schedules": schedules})
    except ValueError:
        return jsonify({"success": False, "error": "Invalid mapping_id"}), 400
    except Exception as e:
        logger.error("Error getting schedules: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/schedules", methods=["POST"])
def add_schedule():
    """Add a schedule for a mapping."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    try:
        data = request.get_json()
        schedule_id = advanced_scheduler.add_schedule(
            mapping_id=int(data.get("mapping_id")),
            schedule_type=data.get("schedule_type"),
            schedule_value=data.get("schedule_value"),
            enabled=data.get("enabled", True),
        )
        if schedule_id:
            advanced_scheduler.setup_all_schedules()
            return jsonify({"success": True, "schedule_id": schedule_id})
        else:
            return jsonify({"success": False, "error": "Failed to create schedule"}), 500
    except Exception as e:
        logger.error("Error adding schedule: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/schedules/<int:schedule_id>", methods=["DELETE"])
def delete_schedule_route(schedule_id):
    """Delete a schedule."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    try:
        success = advanced_scheduler.delete_schedule(schedule_id)
        if success:
            advanced_scheduler.setup_all_schedules()
        return jsonify({"success": success})
    except Exception as e:
        logger.error("Error deleting schedule: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/users")
def users():
    """Render the user management page."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check
    return render_template("users.html")


@app.route("/get_users")
def get_users():
    """Get all users."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    try:
        from safecopy.db.controller import get_db_connection, DEFAULT_DB_PATH

        with get_db_connection(DEFAULT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, enabled, created_at FROM web_auth ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            users_list = []
            for row in rows:
                users_list.append(
                    {
                        "id": row["id"],
                        "username": row["username"],
                        "enabled": bool(row["enabled"]),
                        "created_at": row["created_at"],
                    }
                )
            return jsonify({"success": True, "users": users_list})
    except Exception as e:
        logger.error("Error getting users: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/create_user", methods=["POST"])
def create_user():
    """Create a new user."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"success": False, "error": "Username and password are required"}), 400

        if len(password) < 6:
            return (
                jsonify({"success": False, "error": "Password must be at least 6 characters"}),
                400,
            )

        from safecopy.auth import create_user as create_user_func

        success = create_user_func(username, password)

        if success:
            return jsonify({"success": True})
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to create user. Username may already exist.",
                    }
                ),
                400,
            )
    except Exception as e:
        logger.error("Error creating user: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/change_password", methods=["POST"])
def change_password():
    """Change user password."""
    auth_check = check_auth_required()
    if auth_check:
        return auth_check

    try:
        data = request.get_json()
        username = data.get("username")
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not username or not old_password or not new_password:
            return jsonify({"success": False, "error": "All fields are required"}), 400

        if len(new_password) < 6:
            return (
                jsonify({"success": False, "error": "New password must be at least 6 characters"}),
                400,
            )

        from safecopy.auth import change_password as change_password_func

        success = change_password_func(username, old_password, new_password)

        if success:
            return jsonify({"success": True})
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to change password. Check your current password.",
                    }
                ),
                400,
            )
    except Exception as e:
        logger.error("Error changing password: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


def run(port=5000, debug=True):
    """
    Run the Flask web application.

    Args:
        port: The port to run the web server on
        debug: Whether to run in debug mode
    """
    app.run(port=port, debug=debug)
