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

    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. Console Output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console_handler)

    # 2. File Output with Rotation (Max 5MB per file, keeps 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(LOG_DIR, LOG_FILE_NAME),
        maxBytes=5 * 1024 * 1024, # 5MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))
    logger.addHandler(file_handler)

    return logger