"""Logging package for Friday AI Assistant."""

from loguru import logger

from app.logging.logger_config import LoggingManager

__all__ = ["LoggingManager", "logger"]
