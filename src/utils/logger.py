import logging
from datetime import datetime

# ANSI escape sequences for colors
COLORS = {
    "WARNING": "\033[93m",  # Yellow
    "INFO": "\033[92m",  # Green
    "DEBUG": "\033[94m",  # Blue
    "CRITICAL": "\033[91m",  # Red
    "ERROR": "\033[91m",  # Red
    "ENDC": "\033[0m",  # Reset to default
}


class ColorFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        message = logging.Formatter.format(self, record)
        return f"{COLORS.get(levelname, '')}{message}{COLORS['ENDC']}"


def get_logger(app_package):
    # Create a custom logger
    logger = logging.getLogger(f"{app_package}_logger")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    # get date and time for the log file with hour and minute only
    date = datetime.now().strftime("%Y-%m-%d_%H-%M")

    # Check if the logger already has handlers
    if not logger.handlers:  # If no handlers, add them
        # Create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # Create formatter and add it to the handlers
        formatter = ColorFormatter(
            "%(levelname)s|%(pathname)s|%(lineno)s|%(name)s|%(asctime)s| %(message)s"
        )
        ch.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(ch)

        # Create a file handler object
        handler = logging.FileHandler(f"/tmp/app_{app_package}_{date}.log")
        # Create a formatter
        formatter = logging.Formatter(
            "%(levelname)s|%(pathname)s|%(lineno)s|%(name)s|%(asctime)s| %(message)s"
        )

        # Set the formatter to the handler
        handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


# shared config for logger across all modules
logger_app_package = "ab_testing_automation"
logger = get_logger(logger_app_package)
