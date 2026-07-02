"""Configuration settings for NBA Rebound Prediction Model"""
import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Database configuration
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATA_DIR / "nba_rebounds.db"

# Models directory
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

# API Keys (load from environment variables)
NBA_API_KEY = os.getenv("NBA_API_KEY", None)  # Not typically needed for nba_api
ODDS_API_KEY = os.getenv("ODDS_API_KEY", None)  # The Odds API key
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# ESPN scraping settings
ESPN_BASE_URL = "https://www.espn.com/nba"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # Seconds between requests to avoid rate limiting

# Model configuration
HISTORICAL_YEARS = 5
ROLLING_WINDOW = 10  # Last N games for rolling averages
TRAIN_TEST_SPLIT = 0.8  # 80% train, 20% test
VALIDATION_SPLIT = 0.2  # 20% of training data for validation

# Feature engineering
MIN_GAMES_FOR_ROLLING = 5  # Minimum games needed to calculate rolling stats
MISSING_VALUE_STRATEGY = "median"  # Strategy for handling missing values

# GUI configuration
UPDATE_INTERVAL = 300  # Seconds between automatic updates
GUI_REFRESH_RATE = 60  # Seconds between GUI refreshes

# Logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_LEVEL = "INFO"

# Value bet thresholds
HIGH_VALUE_THRESHOLD = 0.15  # 15% edge for high value
MEDIUM_VALUE_THRESHOLD = 0.05  # 5% edge for medium value
MIN_CONFIDENCE = 0.6  # Minimum confidence level to show prediction


