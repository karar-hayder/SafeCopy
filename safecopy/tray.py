"""
System tray functionality for SafeCopy.
"""

import os
import webbrowser
from pystray import Icon, Menu, MenuItem
from PIL import Image


class SafeCopyTray:
    """System tray icon for SafeCopy."""

    def __init__(self, port=5000):
        """Initialize the system tray icon.

        Args:
            port (int): The port number for the web UI.
        """
        self.port = port
        self.icon = None
        self.setup_icon()

    def setup_icon(self):
        """Set up the system tray icon and menu."""
        # Get the path to the icon file
        icon_path = os.path.join(
            os.path.dirname(__file__), "..", "static", "imgs", "logo.ico"
        )

        # Create the icon menu
        menu = Menu(
            MenuItem("Open Web UI", self.open_web_ui),
            MenuItem("Run Backup Now", self.run_backup),
            MenuItem("Exit", self.stop),
        )

        # Create the icon
        self.icon = Icon("safecopy", Image.open(icon_path), "SafeCopy", menu)

    def open_web_ui(self):
        """Open the web UI in the default browser."""
        webbrowser.open(f"http://localhost:{self.port}")

    def run_backup(self):
        """Run a backup immediately."""
        from safecopy import backup, config

        # Get mappings from config
        config_data = config.load_config()
        mappings = config_data.get("mappings", [])

        if not mappings:
            # No mappings configured
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("No backup mappings configured. Cannot run backup.")
            return

        # Run backup for each mapping
        for mapping in mappings:
            backup.run_backup(mapping)

    def stop(self):
        """Stop the system tray icon."""
        if self.icon:
            self.icon.stop()

    def start(self):
        """Start the system tray icon."""
        if self.icon:
            self.icon.run()
