"""Logging configuration for the application"""
import logging
import sys
from typing import Optional

# Color codes for terminal output (optional, works on most terminals)
class LogColors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    GRAY = '\033[90m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    COLORS = {
        logging.DEBUG: LogColors.GRAY,
        logging.INFO: LogColors.GREEN,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.RED,
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelno, LogColors.RESET)
        record.levelname = f"{color}[{record.levelname}]{LogColors.RESET}"
        return super().format(record)


class SimpleFormatter(logging.Formatter):
    """Simple formatter without colors"""
    
    def format(self, record):
        record.levelname = f"[{record.levelname}]"
        return super().format(record)


def setup_logging(verbose: bool = False, use_colors: bool = True) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        verbose: If True, set level to DEBUG, otherwise INFO
        use_colors: If True, use colored output
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("transcriber")
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Set level
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Set formatter
    if use_colors and sys.stdout.isatty():
        formatter = ColoredFormatter('%(levelname)s %(message)s')
    else:
        formatter = SimpleFormatter('%(levelname)s %(message)s')
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance"""
    if name:
        return logging.getLogger(f"transcriber.{name}")
    return logging.getLogger("transcriber")
