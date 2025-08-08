import logging
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format: str = "%(levelname)s: [%(asctime)s] %(name)s: %(message)s",
    propagate: bool = False,
) -> logging.Logger:
    """Configure and return a logger with the given name.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        format: Log message format
        propagate: Whether to propagate logs to parent loggers

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers if the logger already exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    logger.propagate = propagate
    return logger
