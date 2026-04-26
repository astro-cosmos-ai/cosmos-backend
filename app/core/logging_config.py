import logging
import logging.config


def setup_logging(debug: bool = False) -> None:
    app_level = "DEBUG" if debug else "INFO"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Suppress per-request access lines — errors still surface via uvicorn.error
            "uvicorn.access": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": "INFO",    "handlers": ["console"], "propagate": False},
            "uvicorn":       {"level": "INFO",    "handlers": ["console"], "propagate": False},
            # App loggers
            "app":           {"level": app_level, "handlers": ["console"], "propagate": False},
            # Third-party noise suppression
            "httpx":         {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "httpcore":      {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "anthropic":     {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "langsmith":     {"level": "WARNING", "handlers": ["console"], "propagate": False},
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(config)
