"""Player feature engineering for rebound prediction"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

from utils.helpers import setup_logging
from config.config import ROLLING_WINDOW, MIN_GAMES_FOR_ROLLING

logger = setup_logging(__name__)


class PlayerFeatures:
    """Calculate player-specific features"""
    
    def __init__(self, rolling_window: int = ROLLING_WINDOW):
        self.rolling_window = rolling_window
        self.min_games = MIN_GAMES_FOR_ROLLING
    
    def calculate_last_n_game_average(self, df: pd.DataFrame, 
                                     stat_column: str,
                                     n: Optional[int] = None) -> pd.Series:
        """Calculate rolling average for last N games"""
        if n is None:
            n = self.rolling_window
        
        # Sort by date
        df_sorted = df.sort_values('game_date')
        
        # Calculate rolling average
        rolling_avg = df_sorted[stat_column].rolling(
            window=n, 
            min_periods=self.min_games
        ).mean()
        
        return rolling_avg
    
    def get_last_10_game_rebound_avg(self, player_stats: pd.DataFrame) -> pd.Series:
        """Get last 10 game rebound average"""
        if 'rebounds' not in player_stats.columns:
            logger.warning("Rebounds column not found in player stats")
            return pd.Series(dtype=float)
        
        return self.calculate_last_n_game_average(
            player_stats, 
            'rebounds', 
            n=self.rolling_window
        )
    
    def get_last_10_game_minutes_avg(self, player_stats: pd.DataFrame) -> pd.Series:
        """Get last 10 game minutes played average"""
        if 'minutes_played' not in player_stats.columns:
            logger.warning("Minutes played column not found in player stats")
            return pd.Series(dtype=float)
        
        return self.calculate_last_n_game_average(
            player_stats,
            'minutes_played',
            n=self.rolling_window
        )
    
    def calculate_momentum(self, df: pd.DataFrame, stat_column: str) -> pd.Series:
        """Calculate momentum (trend) for a stat"""
        df_sorted = df.sort_values('game_date')
        
        # Compare last 5 games to previous 5 games
        recent_avg = df_sorted[stat_column].rolling(window=5, min_periods=3).mean()
        previous_avg = df_sorted[stat_column].shift(5).rolling(window=5, min_periods=3).mean()
        
        momentum = recent_avg - previous_avg
        return momentum
    
    def get_rebound_momentum(self, player_stats: pd.DataFrame) -> pd.Series:
        """Get rebound momentum indicator"""
        if 'rebounds' not in player_stats.columns:
            return pd.Series(dtype=float)
        
        return self.calculate_momentum(player_stats, 'rebounds')
    
    def get_season_average(self, player_stats: pd.DataFrame, stat_column: str) -> float:
        """Get season average for a stat"""
        if stat_column not in player_stats.columns:
            return 0.0
        
        return player_stats[stat_column].mean()
    
    def get_career_average(self, player_stats: pd.DataFrame, stat_column: str) -> float:
        """Get career average for a stat (all available data)"""
        if stat_column not in player_stats.columns:
            return 0.0
        
        return player_stats[stat_column].mean()
    
    def calculate_rebound_rate(self, player_stats: pd.DataFrame) -> pd.Series:
        """Calculate rebound rate (rebounds per minute)"""
        if 'rebounds' not in player_stats.columns or 'minutes_played' not in player_stats.columns:
            return pd.Series(dtype=float)
        
        # Avoid division by zero
        minutes = player_stats['minutes_played'].replace(0, np.nan)
        rebound_rate = player_stats['rebounds'] / minutes
        return rebound_rate.fillna(0)
    
    def get_all_player_features(self, player_stats: pd.DataFrame) -> pd.DataFrame:
        """Calculate all player features"""
        if player_stats.empty:
            return pd.DataFrame()
        
        features = pd.DataFrame(index=player_stats.index)
        
        # Sort by date for rolling calculations
        player_stats_sorted = player_stats.sort_values('game_date').copy()
        
        # Last 10 game averages
        features['last_10_rebound_avg'] = self.get_last_10_game_rebound_avg(player_stats_sorted)
        features['last_10_minutes_avg'] = self.get_last_10_game_minutes_avg(player_stats_sorted)
        
        # Momentum
        features['rebound_momentum'] = self.get_rebound_momentum(player_stats_sorted)
        
        # Rebound rate
        features['rebound_rate'] = self.calculate_rebound_rate(player_stats_sorted)
        
        # Season averages (up to current game)
        features['season_rebound_avg'] = player_stats_sorted['rebounds'].expanding().mean()
        features['season_minutes_avg'] = player_stats_sorted['minutes_played'].expanding().mean()
        
        # Recent form (last 3 games) - use smaller min_periods
        features['last_3_rebound_avg'] = player_stats_sorted['rebounds'].rolling(
            window=3, 
            min_periods=1
        ).mean()
        
        # Variability (standard deviation of last 10 games)
        features['rebound_std'] = player_stats_sorted['rebounds'].rolling(
            window=self.rolling_window, 
            min_periods=self.min_games
        ).std()
        
        # Fill NaN values with 0 or forward fill
        features = features.ffill().fillna(0)
        
        return features

