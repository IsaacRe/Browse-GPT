import logging
import sys

IGNNORE_LOGS = [
    "urllib3.connectionpool",
    "selenium.webdriver.remote.remote_connection",
]

LOG_LEVELS = {
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def setup_logger(log_level: str):
    logging.basicConfig(level = LOG_LEVELS.get(log_level),
                        format = '%(asctime)s | %(name)s [%(levelname)s]: %(message)s')

    logger = logging.getLogger("app_logger")

    # Also log to console.
    console = logging.StreamHandler(sys.stdout)
    log_filter = LoggerFilter()
    console.addFilter(log_filter)
    for handler in logging.root.handlers:
        handler.addFilter(log_filter)
    logger.addHandler(console)


class LoggerFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        return not record.name in IGNNORE_LOGS
