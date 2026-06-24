import logging
import structlog


def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=logging.getLevelNamesMapping()[log_level.upper()],
        format="%(message)s",
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[log_level.upper()]
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


"""
Call configure_logging() once at application startup.
After that use logger = get_logger(__name__) wherever needed
"""
