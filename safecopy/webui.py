import os
import json
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_caching import Cache
from safecopy.config import (
    load_config,
    save_config,
    CONFIG_FILE,
    CONFIG_BACKUP,
    DEFAULT_CONFIG,
)
from safecopy.utils import get_available_drives, get_folder_size, format_size
from safecopy.backup import perform_backup
import logging
import shutil

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)
app.config["CACHE_TYPE"] = "simple"  # Simple in-memory cache (for demo purposes)
app.config["SECRET_KEY"] = os.urandom(24)  # For flash messages
cache = Cache(app)
logger = logging.getLogger(__name__)


@app.route("/", methods=["GET", "POST"])
def settings():
    """Render the settings page."""
    try:
        drives = get_available_drives()
        config = load_config()
        return render_template("settings.html", config=config, drives=drives)
    except Exception as e:
        logger.error(f"Error loading settings page: {e}")
        # If there's an error loading the config, try to fix it
        try:
            # Try to restore from backup
            if os.path.exists(CONFIG_BACKUP):
                shutil.copy(CONFIG_BACKUP, CONFIG_FILE)
                logger.info(f"Restored config from backup: {CONFIG_BACKUP}")
            else:
                # Create a new config file
                with open(CONFIG_FILE, "w") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.info(f"Created new config file after corruption: {CONFIG_FILE}")

            # Try again with the fixed config
            config = load_config()
            drives = get_available_drives()
            return render_template("settings.html", config=config, drives=drives)
        except Exception as e2:
            logger.error(f"Failed to recover from config error: {e2}")
            # Last resort: use default config
            return render_template("settings.html", config=DEFAULT_CONFIG, drives=[])


@app.route("/get_mappings")
def get_mappings():
    """Get all mappings from the configuration."""
    config = load_config()
    return jsonify({"mappings": config["mappings"]})


@app.route("/save_mappings", methods=["POST"])
def save_mappings():
    """Save mappings to the configuration."""
    try:
        data = request.get_json()
        if not data or "mappings" not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        config = load_config()
        if config["mappings"] != data["mappings"]:
            config["mappings"] = data["mappings"]

            # Save config and check for errors
            if not save_config(config):
                return (
                    jsonify(
                        {"success": False, "error": "Failed to save configuration"}
                    ),
                    500,
                )

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error saving mappings: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/delete_mapping", methods=["POST"])
def delete_mapping():
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
                # Create backup with compression settings
                backup_result = perform_backup(
                    source_path=source,
                    dest_path=destination,
                    max_versions=max_versions,
                    compression=compression,
                )
                results.append(
                    {
                        "source": source,
                        "success": True,
                        "message": f"Backup completed successfully to {destination}",
                    }
                )
            except Exception as e:
                results.append({"source": source, "success": False, "error": str(e)})

        # Check if any backups succeeded
        successful_backups = [r for r in results if r["success"]]
        if not successful_backups:
            return jsonify(
                {
                    "success": False,
                    "error": "All backups failed",
                    "details": "\n".join(
                        [f"{r['source']}: {r['error']}" for r in results]
                    ),
                }
            )
        elif len(successful_backups) < len(results):
            return jsonify(
                {
                    "success": True,
                    "message": "Some backups completed successfully",
                    "details": "\n".join(
                        [
                            f"{r['source']}: {r.get('message', r.get('error'))}"
                            for r in results
                        ]
                    ),
                }
            )
        else:
            return jsonify(
                {"success": True, "message": "All backups completed successfully"}
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/browse_folders")
def browse_folders():
    """Browse folders on the server for the file browser dialog."""
    path = request.args.get("path", "/")

    # Handle root path (show drives)
    if path == "/" or path == "":
        drives = get_available_drives()
        return jsonify({"drives": drives, "folders": []})

    # Normalize path
    if os.name == "nt":  # Windows
        path = path.replace("/", "\\")

    # Check if path exists and is a directory
    if not os.path.exists(path) or not os.path.isdir(path):
        return jsonify({"error": "Path does not exist or is not a directory"}), 400

    # Get folders in the path
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

    # Normalize path
    if os.name == "nt":  # Windows
        path = path.replace("/", "\\")

    # Check if path exists and is a directory
    if not os.path.exists(path) or not os.path.isdir(path):
        return jsonify({"error": "Path does not exist or is not a directory"}), 400

    try:
        # Get files and folders in the path
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

        # Get folder size
        size = get_folder_size(path)
        size_formatted = format_size(size)

        return jsonify(
            {"files": sorted(files), "folders": sorted(folders), "size": size_formatted}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_backup_settings", methods=["GET"])
def get_backup_settings():
    """Get the current backup settings."""
    config = load_config()
    settings = config.get("backup_settings", {"maxVersions": 3, "compression": "none"})
    return jsonify({"success": True, "settings": settings})


@app.route("/save_backup_settings", methods=["POST"])
def save_backup_settings():
    """Save the backup settings."""
    try:
        data = request.get_json()
        settings = data.get("settings", {})

        config = load_config()
        if config["backup_settings"] != settings:
            config["backup_settings"] = settings

            # Save config and check for errors
            if not save_config(config):
                return (
                    jsonify(
                        {"success": False, "error": "Failed to save configuration"}
                    ),
                    500,
                )

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error saving backup settings: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def run(port=5000, debug=True):
    """
    Run the Flask web application.

    Args:
        port: The port to run the web server on
        debug: Whether to run in debug mode
    """
    app.run(port=port, debug=debug)
