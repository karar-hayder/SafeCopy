import json
import os

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {"mappings": [], "last_actions": []}


def init_config():
    from pathlib import Path
    import sys

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

    desktop = Path.home() / "Desktop"

    if sys.platform == "win32":
        shortcut_path = desktop / "SafeCopy.lnk"
    else:
        shortcut_path = desktop / "SafeCopy.desktop"

    if not shortcut_path.exists():
        create_desktop_shortcut()


def create_desktop_shortcut():
    """Create a shortcut on the desktop to launch the web UI."""
    import sys
    from pathlib import Path

    desktop = Path.home() / "Desktop"

    if sys.platform == "win32":
        from win32com.client import Dispatch

        shortcut_path = os.path.join(desktop, "SafeCopy.lnk")
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = "cmd"
        shortcut.Arguments = "/c start http://localhost:5000"
        shortcut.WorkingDirectory = str(Path.home())

        # Set icon if available
        static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
        logo_path = os.path.join(static_dir, "imgs", "logo.ico")
        print(logo_path)

        if logo_path:
            shortcut.IconLocation = logo_path

        shortcut.save()

    else:  # Linux/Mac
        desktop_entry = f"""[Desktop Entry]
Name=SafeCopy
Exec=xdg-open http://localhost:5000
Type=Application
Terminal=false
Categories=Utility;
"""
        shortcut_path = os.path.join(desktop, "SafeCopy.desktop")

        with open(shortcut_path, "w") as f:
            f.write(desktop_entry)

        # Make executable
        os.chmod(shortcut_path, 0o755)


def open_web_ui():
    """Open the web UI in the default browser."""
    import webbrowser

    webbrowser.open("http://localhost:5000")


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)
