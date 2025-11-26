#!/usr/bin/env python3
import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO, format="pytest_runner.py: [%(levelname)s] %(message)s"
)
logger = logging.getLogger("pytest_runner")


def main():
    # Prefer running pytest via venv python -m pytest
    if os.name == "nt":
        venv_python = os.path.join(".venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(".venv", "bin", "python")

    if os.path.exists(venv_python):
        logger.info(f"Using virtualenv python at {venv_python}")
        cmd = [
            f"{venv_python}",
            "-m",
            "pytest",
            "--cov=safecopy",
            "--cov-report=term-missing",
        ]
    else:
        cmd = ["pytest", "--cov=safecopy", "--cov-report=term-missing"]

    logger.info("Running: %s", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc == 0:
        logger.info("Tests completed successfully.")
    else:
        logger.error(f"pytest exited with code {rc}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
