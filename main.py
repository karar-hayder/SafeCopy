from safecopy import backup, config, scheduler, webui
import argparse


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


if __name__ == "__main__":
    args = parse_args()

    # Initialize configuration
    config.init_config()

    # Start the backup scheduler with the specified interval
    scheduler.start(interval_minutes=args.interval)

    # Run the web UI
    webui.run(port=args.port)
