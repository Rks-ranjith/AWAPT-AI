import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Industrial grade formatting
    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # 1. Console Handler (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)

    # 2. File Handler (Rotating log files for production)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "awap-ai.log"),
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)

    # Root Logger Configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Specific silencing for noisy external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("AWAP-AI Industrial Logging Subsystem initialized.")

if __name__ == "__main__":
    setup_logging()
