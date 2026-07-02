"""Feature aggregator to combine all features for model training"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
from datetime import datetime

from utils.helpers import setup_logging, format_date, is_back_to_back, get_day_of_week
from features.player_features import PlayerFeatures
from features.team_features import TeamFeatures
from features.matchup_features import MatchupFeatures
from config.config import MISSING_VALUE_STRATEGY

logger = setup_logging(__name__)


class FeatureAggregator:
    """Aggregates all features for model training and prediction"""
    
    def __init__(self):
        self.player_features = PlayerFeatures()
        self.team_features = TeamFeatures()
        self.matchup_features = MatchupFeatures()
    
    def aggregate_features_for_game(self,
                                   player_stats: pd.DataFrame,
                                   team_stats: pd.DataFrame,
                                   player_roster: pd.DataFrame,
                                   player_id: int,
                                   team_id: int,
                                   opponent_team_id: int,
                                   game_date: str) -> Dict[str, float]:
        """Aggregate all features for a specific game"""
        features = {}
        
        # Get player stats up to this game
        historical_stats = player_stats[
            (player_stats['player_id'] == player_id) &
            (player_stats['game_date'] < game_date)
        ].sort_values('game_date')
        
        # Player features
        if not historical_stats.empty:
            player_feat_df = self.player_features.get_all_player_features(historical_stats)
            if not player_feat_df.empty:
                # Get most recent features
                latest_features = player_feat_df.iloc[-1]
                for col in player_feat_df.columns:
                    features[col] = latest_features.get(col, 0.0)
        else:
            # Default values if no history
            features.update({
                'last_10_rebound_avg': 0.0,
                'last_10_minutes_avg': 0.0,
                'rebound_momentum': 0.0,
                'rebound_rate': 0.0,
                'season_rebound_avg': 0.0,
                'season_minutes_avg': 0.0,
                'last_3_rebound_avg': 0.0,
                'rebound_std': 0.0
            })
        
        # Team features
        team_feat = self.team_features.get_team_features_for_game(
            team_stats, team_id, opponent_team_id, game_date
        )
        features.update(team_feat)
        
        # Team rebound stats
        team_rebound_stats = self.team_features.get_team_rebound_stats(
            team_stats, team_id, game_date
        )
        features.update(team_rebound_stats)
        
        # Matchup features
        matchup_feat = self.matchup_features.get_matchup_features(
            player_roster, player_id, opponent_team_id, historical_stats
        )
        features.update(matchup_feat)
        
        # Time-based features
        game_dt = datetime.strptime(game_date, '%Y-%m-%d')
        features['day_of_week'] = get_day_of_week(game_dt)
        
        # Check for back-to-back
        if not historical_stats.empty:
            last_game_date = pd.to_datetime(historical_stats.iloc[-1]['game_date'])
            features['is_back_to_back'] = 1.0 if is_back_to_back(game_dt, last_game_date) else 0.0
        else:
            features['is_back_to_back'] = 0.0
        
        # Home/away (would need to get from game data)
        features['is_home'] = 0.0  # Default, should be set from game data
        
        return features
    
    def create_training_dataset(self,
                              player_stats: pd.DataFrame,
                              team_stats: pd.DataFrame,
                              player_roster: pd.DataFrame) -> pd.DataFrame:
        """Create training dataset with all features"""
        all_features = []
        all_targets = []
        
        # Group by player
        for player_id in player_stats['player_id'].unique():
            player_data = player_stats[player_stats['player_id'] == player_id].sort_values('game_date')
            
            # Get player's team - use placeholder if not available
            if player_data.empty:
                continue
            
            # Use placeholder team_id if not available - we'll create features without team data
            team_id = player_data.iloc[0].get('team_id', 0)  # Use 0 as placeholder
            if team_id is None:
                team_id = 0
            
            # Process each game
            for idx, game in player_data.iterrows():
                game_date = game['game_date']
                opponent_team_id = game.get('opponent_team_id', 0)
                if opponent_team_id is None:
                    opponent_team_id = 0
                
                # Get features for this game (using data before this game)
                features = self.aggregate_features_for_game(
                    player_stats,
                    team_stats,
                    player_roster,
                    player_id,
                    team_id,
                    opponent_team_id,
                    game_date
                )
                
                # Get target (rebounds for this game)
                target = game.get('rebounds', 0)
                
                all_features.append(features)
                all_targets.append(target)
        
        # Create DataFrame
        if not all_features:
            return pd.DataFrame()
        
        features_df = pd.DataFrame(all_features)
        features_df['target'] = all_targets
        
        # Handle missing values
        if not features_df.empty:
            features_df = self._handle_missing_values(features_df)
        
        return features_df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in feature DataFrame"""
        if MISSING_VALUE_STRATEGY == "median":
            return df.fillna(df.median())
        elif MISSING_VALUE_STRATEGY == "mean":
            return df.fillna(df.mean())
        elif MISSING_VALUE_STRATEGY == "forward_fill":
            return df.ffill().fillna(0)
        else:
            return df.fillna(0)
    
    def prepare_prediction_features(self,
                                   player_id: int,
                                   team_id: int,
                                   opponent_team_id: int,
                                   game_date: str,
                                   db_manager) -> Dict[str, float]:
        """Prepare features for prediction using database"""
        # Get data from database
        player_stats = db_manager.get_player_stats(player_id=player_id)
        team_stats = db_manager.get_team_stats()
        player_roster = db_manager.get_player_roster()
        
        # Aggregate features
        features = self.aggregate_features_for_game(
            player_stats,
            team_stats,
            player_roster,
            player_id,
            team_id,
            opponent_team_id,
            game_date
        )
        
        return features

