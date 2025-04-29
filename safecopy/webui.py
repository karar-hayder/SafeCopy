import os
import json
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_caching import Cache
from safecopy.config import load_config, save_config
from safecopy.utils import get_available_drives, get_folder_size, format_size
from safecopy.backup import perform_backup

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)
app.config["CACHE_TYPE"] = "simple"  # Simple in-memory cache (for demo purposes)
app.config["SECRET_KEY"] = os.urandom(24)  # For flash messages
cache = Cache(app)


@app.route("/", methods=["GET", "POST"])
def settings():
    drives = get_available_drives()
    if request.method == "POST":
        new_mapping = {
            "source": request.form["source"],
            "destination": request.form["destination"],
        }

        config = load_config()
        config["mappings"].append(new_mapping)
        save_config(config)
        flash("Mapping added successfully!", "success")
        return redirect("/")

    config = load_config()
    return render_template("settings.html", config=config, drives=drives)


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
        config["mappings"] = data["mappings"]
        save_config(config)

        return jsonify({"success": True})
    except Exception as e:
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
        successful, failed = perform_backup()

        if not successful and not failed:
            return jsonify(
                {"success": False, "error": "No backup mappings configured."}
            )
        elif successful and not failed:
            return jsonify(
                {
                    "success": True,
                    "message": f"Backup completed successfully! {len(successful)} backup(s) performed.",
                }
            )
        elif successful and failed:
            return jsonify(
                {
                    "success": True,
                    "message": f"Backup partially completed. {len(successful)} successful, {len(failed)} failed.",
                    "failed": failed,
                }
            )
        else:
            error_messages = [
                f"Error backing up {src} to {dst}: {error}"
                for src, dst, error in failed
            ]
            return jsonify(
                {
                    "success": False,
                    "error": f"Backup failed for all {len(failed)} mapping(s).",
                    "details": error_messages,
                }
            )
    except Exception as e:
        return jsonify({"success": False, "error": f"Backup process failed: {str(e)}"})


@app.route("/browse_folders")
def browse_folders():
    """Browse folders on the server for the file browser dialog."""
    path = request.args.get("path", "/")

    # Handle root path (show drives)
    if path == "/":
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


def run(port=5000, debug=True):
    """
    Run the Flask web application.

    Args:
        port: The port to run the web server on
        debug: Whether to run in debug mode
    """
    app.run(port=port, debug=debug)
