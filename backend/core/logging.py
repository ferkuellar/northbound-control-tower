import logging
import sys

from core.config import settings
from observability.logging import SafeJsonFormatter


def configure_logging() -> None:
    logging.captureWarnings(True)

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format.lower() == "json":
        formatter = SafeJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d")
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())
