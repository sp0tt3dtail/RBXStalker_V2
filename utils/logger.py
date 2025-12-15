import logging
import logging.handlers
import os
import sys

LOG_DIR = "logs"
LOG_FILE_NAME = "rbxstalker.log"

def setup_logger():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger("RBXStalker")
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicates if re-initialized
    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console_handler)

    # 2. Rotating File Handler (Max 5 files, 5MB each)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(LOG_DIR, LOG_FILE_NAME),
        maxBytes=5 * 1024 * 1024, # 5MB
        backupCount=5,            # Keep 5 backups
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))
    logger.addHandler(file_handler)

    return logger