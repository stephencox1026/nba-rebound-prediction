"""Helper utilities for NBA Rebound Prediction Model"""
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Any
import time

from config.config import LOG_DIR, LOG_LEVEL


def setup_logging(name: str = "nba_rebound_model") -> logging.Logger:
    """Setup logging configuration"""
    log_file = LOG_DIR / f"{name}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Setup logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError(f"Unable to parse date: {date_str}")


def format_date(dt: datetime) -> str:
    """Format datetime object to date string"""
    return dt.strftime("%Y-%m-%d")


def get_season_from_date(date: datetime) -> str:
    """Get NBA season string from date (e.g., '2023-24')"""
    if date.month >= 10:  # October onwards is start of new season
        return f"{date.year}-{str(date.year + 1)[2:]}"
    else:  # January-September is end of previous season
        return f"{date.year - 1}-{str(date.year)[2:]}"


def get_years_back_date(years: int) -> datetime:
    """Get date N years back from today"""
    return datetime.now() - timedelta(days=years * 365)


def convert_height_to_inches(feet: Optional[int], inches: Optional[int]) -> Optional[float]:
    """Convert height from feet and inches to total inches"""
    if feet is None or inches is None:
        return None
    return (feet * 12) + inches


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry function on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator


def validate_player_id(player_id: Any) -> bool:
    """Validate player ID is a positive integer"""
    try:
        return int(player_id) > 0
    except (ValueError, TypeError):
        return False


def validate_team_id(team_id: Any) -> bool:
    """Validate team ID is a positive integer"""
    try:
        return int(team_id) > 0
    except (ValueError, TypeError):
        return False


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_pace(possessions: float, minutes: float) -> float:
    """Calculate pace (possessions per 48 minutes)"""
    if minutes == 0:
        return 0.0
    return (possessions / minutes) * 48


def is_back_to_back(game_date: datetime, previous_game_date: Optional[datetime]) -> bool:
    """Check if game is part of back-to-back"""
    if previous_game_date is None:
        return False
    return (game_date - previous_game_date).days == 1


def get_day_of_week(game_date: datetime) -> int:
    """Get day of week (0=Monday, 6=Sunday)"""
    return game_date.weekday()


