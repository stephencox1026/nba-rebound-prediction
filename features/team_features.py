"""Team feature engineering for rebound prediction"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

from utils.helpers import setup_logging, safe_divide

logger = setup_logging(__name__)


class TeamFeatures:
    """Calculate team-specific features"""
    
    def __init__(self):
        pass
    
    def get_team_shots_attempted(self, team_stats: pd.DataFrame, 
                                team_id: int,
                                game_date: str) -> float:
        """Get team shots attempted for a specific game"""
        # Return default if team_id is placeholder (0) or team_stats is empty
        if team_id == 0 or team_stats.empty:
            return 85.0  # League average FGA
        
        game_stats = team_stats[
            (team_stats['team_id'] == team_id) & 
            (team_stats['game_date'] == game_date)
        ]
        
        if game_stats.empty:
            # Get average from recent games
            recent_stats = team_stats[
                (team_stats['team_id'] == team_id) &
                (team_stats['game_date'] < game_date)
            ].tail(10)
            
            if not recent_stats.empty and 'field_goals_attempted' in recent_stats.columns:
                return recent_stats['field_goals_attempted'].mean()
            return 85.0  # League average
        
        return game_stats.iloc[0].get('field_goals_attempted', 85.0)
    
    def get_team_fg_percentage(self, team_stats: pd.DataFrame,
                              team_id: int,
                              game_date: str) -> float:
        """Get team field goal percentage"""
        # Return default if team_id is placeholder
        if team_id == 0 or team_stats.empty:
            return 0.45  # League average
        
        game_stats = team_stats[
            (team_stats['team_id'] == team_id) &
            (team_stats['game_date'] == game_date)
        ]
        
        if game_stats.empty:
            # Get average from recent games
            recent_stats = team_stats[
                (team_stats['team_id'] == team_id) &
                (team_stats['game_date'] < game_date)
            ].tail(10)
            
            if not recent_stats.empty and 'field_goal_percentage' in recent_stats.columns:
                return recent_stats['field_goal_percentage'].mean()
            return 0.45  # League average
        
        return game_stats.iloc[0].get('field_goal_percentage', 0.45)
    
    def get_team_pace(self, team_stats: pd.DataFrame,
                     team_id: int,
                     game_date: str) -> float:
        """Get team pace (possessions per 48 minutes)"""
        # Return default if team_id is placeholder
        if team_id == 0 or team_stats.empty:
            return 100.0  # League average pace
        
        game_stats = team_stats[
            (team_stats['team_id'] == team_id) &
            (team_stats['game_date'] == game_date)
        ]
        
        if game_stats.empty:
            # Get average from recent games
            recent_stats = team_stats[
                (team_stats['team_id'] == team_id) &
                (team_stats['game_date'] < game_date)
            ].tail(10)
            
            if not recent_stats.empty and 'pace' in recent_stats.columns:
                return recent_stats['pace'].mean()
            return 100.0  # League average pace
        
        return game_stats.iloc[0].get('pace', 100.0)
    
    def get_opponent_shots_attempted(self, team_stats: pd.DataFrame,
                                    opponent_team_id: int,
                                    game_date: str) -> float:
        """Get opponent shots attempted"""
        return self.get_team_shots_attempted(team_stats, opponent_team_id, game_date)
    
    def get_opponent_fg_percentage(self, team_stats: pd.DataFrame,
                                  opponent_team_id: int,
                                  game_date: str) -> float:
        """Get opponent field goal percentage"""
        return self.get_team_fg_percentage(team_stats, opponent_team_id, game_date)
    
    def get_opponent_pace(self, team_stats: pd.DataFrame,
                         opponent_team_id: int,
                         game_date: str) -> float:
        """Get opponent pace"""
        return self.get_team_pace(team_stats, opponent_team_id, game_date)
    
    def calculate_missed_shots_opportunity(self, fga: float, fg_pct: float) -> float:
        """Calculate missed shots (rebound opportunities)"""
        return fga * (1 - fg_pct)
    
    def get_team_features_for_game(self, team_stats: pd.DataFrame,
                                  team_id: int,
                                  opponent_team_id: int,
                                  game_date: str) -> dict:
        """Get all team features for a specific game"""
        features = {}
        
        # Team stats
        features['team_fga'] = self.get_team_shots_attempted(team_stats, team_id, game_date)
        features['team_fg_pct'] = self.get_team_fg_percentage(team_stats, team_id, game_date)
        features['team_pace'] = self.get_team_pace(team_stats, team_id, game_date)
        features['team_missed_shots'] = self.calculate_missed_shots_opportunity(
            features['team_fga'], features['team_fg_pct']
        )
        
        # Opponent stats
        features['opponent_fga'] = self.get_opponent_shots_attempted(
            team_stats, opponent_team_id, game_date
        )
        features['opponent_fg_pct'] = self.get_opponent_fg_percentage(
            team_stats, opponent_team_id, game_date
        )
        features['opponent_pace'] = self.get_opponent_pace(
            team_stats, opponent_team_id, game_date
        )
        features['opponent_missed_shots'] = self.calculate_missed_shots_opportunity(
            features['opponent_fga'], features['opponent_fg_pct']
        )
        
        # Combined metrics
        features['total_missed_shots'] = features['team_missed_shots'] + features['opponent_missed_shots']
        features['avg_pace'] = (features['team_pace'] + features['opponent_pace']) / 2
        
        return features
    
    def get_team_rebound_stats(self, team_stats: pd.DataFrame,
                              team_id: int,
                              game_date: str) -> dict:
        """Get team rebounding statistics"""
        recent_stats = team_stats[
            (team_stats['team_id'] == team_id) &
            (team_stats['game_date'] < game_date)
        ].tail(10)
        
        if recent_stats.empty:
            return {
                'team_avg_rebounds': 0.0,
                'team_avg_offensive_rebounds': 0.0,
                'team_avg_defensive_rebounds': 0.0
            }
        
        return {
            'team_avg_rebounds': recent_stats.get('total_rebounds', pd.Series()).mean() or 0.0,
            'team_avg_offensive_rebounds': recent_stats.get('offensive_rebounds', pd.Series()).mean() or 0.0,
            'team_avg_defensive_rebounds': recent_stats.get('defensive_rebounds', pd.Series()).mean() or 0.0
        }

