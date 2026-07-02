"""Matchup feature engineering for rebound prediction"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
import logging

from utils.helpers import setup_logging, convert_height_to_inches

logger = setup_logging(__name__)


class MatchupFeatures:
    """Calculate matchup-specific features"""
    
    def __init__(self):
        pass
    
    def get_player_height(self, player_roster: pd.DataFrame, player_id: int) -> Optional[float]:
        """Get player height in inches"""
        player_info = player_roster[player_roster['player_id'] == player_id]
        
        if player_info.empty:
            return None
        
        # Try total inches first
        if 'height_total_inches' in player_info.columns:
            height = player_info.iloc[0]['height_total_inches']
            if pd.notna(height):
                return float(height)
        
        # Otherwise calculate from feet and inches
        if 'height_feet' in player_info.columns and 'height_inches' in player_info.columns:
            feet = player_info.iloc[0]['height_feet']
            inches = player_info.iloc[0]['height_inches']
            if pd.notna(feet) and pd.notna(inches):
                return convert_height_to_inches(int(feet), int(inches))
        
        return None
    
    def estimate_primary_defender(self, player_roster: pd.DataFrame,
                                 player_id: int,
                                 opponent_team_id: int,
                                 player_position: Optional[str] = None) -> Optional[int]:
        """Estimate primary defender based on position matching"""
        # Get player position
        player_info = player_roster[player_roster['player_id'] == player_id]
        if player_info.empty:
            return None
        
        player_pos = player_info.iloc[0].get('position', None)
        if not player_pos:
            return None
        
        # Get opponent team roster
        opponent_roster = player_roster[
            (player_roster['team_id'] == opponent_team_id) |
            (player_roster['team_id'].isna())  # Include players not on specific team
        ]
        
        if opponent_roster.empty:
            return None
        
        # Match by position (simplified - would need actual lineup data)
        # For now, find players with similar position
        position_map = {
            'PG': ['PG', 'G'],
            'SG': ['SG', 'G'],
            'SF': ['SF', 'F'],
            'PF': ['PF', 'F'],
            'C': ['C', 'F', 'PF']
        }
        
        matching_positions = position_map.get(player_pos, [player_pos])
        matching_players = opponent_roster[
            opponent_roster['position'].isin(matching_positions)
        ]
        
        if matching_players.empty:
            return None
        
        # Return first matching player ID (in real implementation, would use lineup data)
        return matching_players.iloc[0]['player_id']
    
    def calculate_height_advantage(self, player_height: Optional[float],
                                   defender_height: Optional[float]) -> float:
        """Calculate height advantage in inches"""
        if player_height is None or defender_height is None:
            return 0.0
        
        return player_height - defender_height
    
    def get_team_size_metric(self, player_roster: pd.DataFrame,
                            team_id: int) -> float:
        """Calculate average height of team (size metric)"""
        team_roster = player_roster[player_roster['team_id'] == team_id]
        
        if team_roster.empty:
            return 0.0
        
        heights = []
        for _, player in team_roster.iterrows():
            height = self.get_player_height(player_roster, player['player_id'])
            if height:
                heights.append(height)
        
        if heights:
            return np.mean(heights)
        return 0.0
    
    def get_historical_head_to_head(self, player_stats: pd.DataFrame,
                                   opponent_team_id: int) -> Dict[str, float]:
        """Get historical performance against specific opponent"""
        h2h_stats = player_stats[player_stats['opponent_team_id'] == opponent_team_id]
        
        if h2h_stats.empty:
            return {
                'h2h_rebound_avg': 0.0,
                'h2h_games_played': 0
            }
        
        return {
            'h2h_rebound_avg': h2h_stats['rebounds'].mean() if 'rebounds' in h2h_stats.columns else 0.0,
            'h2h_games_played': len(h2h_stats)
        }
    
    def get_matchup_features(self, player_roster: pd.DataFrame,
                            player_id: int,
                            opponent_team_id: int,
                            player_stats: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """Get all matchup features"""
        features = {}
        
        # Player height
        player_height = self.get_player_height(player_roster, player_id)
        features['player_height'] = player_height or 0.0
        
        # Primary defender estimation
        defender_id = self.estimate_primary_defender(player_roster, player_id, opponent_team_id)
        if defender_id:
            defender_height = self.get_player_height(player_roster, defender_id)
            features['defender_height'] = defender_height or 0.0
            features['height_advantage'] = self.calculate_height_advantage(
                player_height, defender_height
            )
        else:
            features['defender_height'] = 0.0
            features['height_advantage'] = 0.0
        
        # Team size metrics
        player_info = player_roster[player_roster['player_id'] == player_id]
        if not player_info.empty:
            team_id = player_info.iloc[0].get('team_id', None)
            if team_id:
                features['team_avg_height'] = self.get_team_size_metric(player_roster, team_id)
                features['opponent_avg_height'] = self.get_team_size_metric(player_roster, opponent_team_id)
            else:
                features['team_avg_height'] = 0.0
                features['opponent_avg_height'] = 0.0
        else:
            features['team_avg_height'] = 0.0
            features['opponent_avg_height'] = 0.0
        
        # Historical head-to-head
        if player_stats is not None:
            h2h = self.get_historical_head_to_head(player_stats, opponent_team_id)
            features.update(h2h)
        else:
            features['h2h_rebound_avg'] = 0.0
            features['h2h_games_played'] = 0
        
        return features

