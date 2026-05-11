import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from core.config import settings


def configure_logging() -> None:
    logging.captureWarnings(True)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())
