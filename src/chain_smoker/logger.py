import logging
import sys


class CustomFormatter(logging.Formatter):
    """Color formatter from https://stackoverflow.com/a/56944256"""
    grey = '\x1b[38;20m'
    yellow = '\x1b[33;20m'
    red = '\x1b[1;31m'
    green = '\x1b[1;32m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
stdout_handler.setFormatter(CustomFormatter())
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.INFO,
    handlers=handlers
)
logger = logging.getLogger('SMOKE_TESTER')
