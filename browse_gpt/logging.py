import logging
import os.path
from os import makedirs
import sys

LOG_LEVELS = {
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def setup_logger(log_level: str):
    logging.basicConfig(level = logging.INFO,
                        format = '%(asctime)s | %(name)s [%(levelname)s]: %(message)s')

    logger = logging.getLogger("app_logger")

    if LOG_LEVELS.get(log_level):
        logger.setLevel(LOG_LEVELS[log_level])

    # Also log to console.
    console = logging.StreamHandler(sys.stdout)
    logger.addHandler(console)
