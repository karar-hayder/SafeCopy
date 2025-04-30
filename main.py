from safecopy import backup, config, scheduler, webui
import argparse
import threading
from safecopy.tray import SafeCopyTray


def parse_args():
    parser = argparse.ArgumentParser(description="SafeCopy - Automated Backup Tool")
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Backup interval in minutes (default: 10)",
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Web UI port (default: 5000)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the SafeCopy application."""
    args = parse_args()

    # Initialize configuration
    config.init_config()

    # Start the backup scheduler with the specified interval
    scheduler.start(interval_minutes=args.interval)

    # Create and start the system tray
    tray = SafeCopyTray(port=args.port)
    tray_thread = threading.Thread(target=tray.start, daemon=True)
    tray_thread.start()

    # Run the web UI in the main thread
    webui.run(port=args.port)


if __name__ == "__main__":
    main()
