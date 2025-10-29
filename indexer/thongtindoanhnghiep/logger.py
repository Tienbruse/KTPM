import logging
from datetime import datetime

import pytz


def initial_logger():
    # Create a logger
    logger = logging.getLogger("app")

    # Remmove duplicate log in cloudwatch
    logger.propagate = False

    # Set the logging level
    logger.setLevel(logging.INFO)

    # Set the timezone to Vietnam
    vietnam_timezone = pytz.timezone("Asia/Ho_Chi_Minh")

    # Configure logging with the Vietnam timezone
    logging.Formatter.converter = (
        lambda *args: pytz.utc.localize(datetime.utcnow())
        .astimezone(vietnam_timezone)
        .timetuple()
    )

    # Define the log format
    console_log_format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(console_log_format, datefmt=date_format)
    )
    logger.addHandler(console_handler)
    return logger


logger = initial_logger()
