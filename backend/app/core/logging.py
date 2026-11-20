"""Logging setup: one consistent format, UTC timestamps."""

import logging
import logging.config
import time


def configure_logging(level: str = "INFO") -> None:
    logging.Formatter.converter = time.gmtime  # UTC, matching the project's time rule
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)sZ %(levelname)s %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                }
            },
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
            "root": {"level": level, "handlers": ["console"]},
        }
    )
