"""Value bet calculator for identifying profitable opportunities"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import logging

from utils.helpers import setup_logging
from analysis.line_parser import BettingLineParser
from config.config import HIGH_VALUE_THRESHOLD, MEDIUM_VALUE_THRESHOLD, MIN_CONFIDENCE

logger = setup_logging(__name__)


class ValueCalculator:
    """Calculates expected value and identifies value bets"""
    
    def __init__(self):
        self.line_parser = BettingLineParser()
    
    def calculate_win_probability(self, predicted_rebounds: float, 
                                 line_value: float,
                                 bet_type: str = "over") -> float:
        """Calculate win probability based on prediction and line
        
        Uses a simple normal distribution assumption
        """
        # Assume prediction follows normal distribution with std = 1.5
        std = 1.5
        
        if bet_type.lower() == "over":
            # Probability of going over
            z_score = (line_value - predicted_rebounds) / std
            prob = 1 - self._normal_cdf(z_score)
        else:
            # Probability of going under
            z_score = (line_value - predicted_rebounds) / std
            prob = self._normal_cdf(z_score)
        
        return max(0.0, min(1.0, prob))
    
    def _normal_cdf(self, z: float) -> float:
        """Cumulative distribution function for standard normal"""
        # Approximation using error function
        return 0.5 * (1 + np.sign(z) * (1 - np.exp(-2 * z**2 / np.pi)))
    
    def calculate_expected_value(self, win_probability: float,
                                odds: int,
                                bet_amount: float = 100.0) -> float:
        """Calculate expected value for a bet
        
        Returns:
            Expected value in dollars for the bet amount
        """
        if odds > 0:
            payout = bet_amount * (odds / 100)
        else:
            payout = bet_amount * (100 / abs(odds))
        
        # EV = (win_prob * payout) - (lose_prob * bet_amount)
        ev = (win_probability * payout) - ((1 - win_probability) * bet_amount)
        
        return ev
    
    def calculate_value_score(self, predicted_rebounds: float,
                             line_value: float,
                             over_odds: Optional[int] = None,
                             under_odds: Optional[int] = None) -> Dict[str, float]:
        """Calculate value score for both over and under bets"""
        results = {}
        
        # Over bet
        if over_odds is not None:
            over_win_prob = self.calculate_win_probability(predicted_rebounds, line_value, "over")
            over_ev = self.calculate_expected_value(over_win_prob, over_odds)
            over_edge = over_win_prob - self.line_parser.parse_american_odds(over_odds)
            
            results['over'] = {
                'win_probability': over_win_prob,
                'expected_value': over_ev,
                'edge': over_edge,
                'odds': over_odds,
                'implied_prob': self.line_parser.parse_american_odds(over_odds)
            }
        
        # Under bet
        if under_odds is not None:
            under_win_prob = self.calculate_win_probability(predicted_rebounds, line_value, "under")
            under_ev = self.calculate_expected_value(under_win_prob, under_odds)
            under_edge = under_win_prob - self.line_parser.parse_american_odds(under_odds)
            
            results['under'] = {
                'win_probability': under_win_prob,
                'expected_value': under_ev,
                'edge': under_edge,
                'odds': under_odds,
                'implied_prob': self.line_parser.parse_american_odds(under_odds)
            }
        
        # Determine best bet
        if results:
            best_bet = max(results.keys(), 
                          key=lambda k: results[k]['expected_value'])
            results['best_bet'] = best_bet
            results['best_value'] = results[best_bet]['expected_value']
            results['best_edge'] = results[best_bet]['edge']
        else:
            results['best_bet'] = None
            results['best_value'] = 0.0
            results['best_edge'] = 0.0
        
        return results
    
    def classify_value_bet(self, edge: float) -> str:
        """Classify value bet based on edge"""
        if edge >= HIGH_VALUE_THRESHOLD:
            return "high"
        elif edge >= MEDIUM_VALUE_THRESHOLD:
            return "medium"
        else:
            return "low"
    
    def find_value_bets(self, predictions_df: pd.DataFrame,
                       betting_lines_df: pd.DataFrame) -> pd.DataFrame:
        """Find value bets by comparing predictions to betting lines"""
        value_bets = []
        
        # Merge predictions with betting lines
        merged = pd.merge(
            predictions_df,
            betting_lines_df,
            on=['player_id', 'game_date'],
            how='inner',
            suffixes=('_pred', '_line')
        )
        
        for _, row in merged.iterrows():
            predicted_rebounds = row.get('predicted_rebounds', 0)
            line_value = row.get('line_value', 0)
            over_odds = row.get('over_odds', None)
            under_odds = row.get('under_odds', None)
            confidence = row.get('confidence_interval_upper', 0) - row.get('confidence_interval_lower', 0)
            confidence_level = 1.0 - (confidence / (predicted_rebounds + 1))  # Normalized confidence
            
            if confidence_level < MIN_CONFIDENCE:
                continue
            
            # Calculate value
            value_scores = self.calculate_value_score(
                predicted_rebounds, line_value, over_odds, under_odds
            )
            
            best_bet = value_scores.get('best_bet')
            if best_bet and value_scores['best_edge'] > 0:
                bet_info = value_scores[best_bet]
                
                value_bet = {
                    'player_id': row.get('player_id'),
                    'player_name': row.get('player_name', 'Unknown'),
                    'game_date': row.get('game_date'),
                    'predicted_rebounds': predicted_rebounds,
                    'line_value': line_value,
                    'bet_type': best_bet.upper(),
                    'edge': value_scores['best_edge'],
                    'expected_value': value_scores['best_value'],
                    'win_probability': bet_info['win_probability'],
                    'implied_probability': bet_info['implied_prob'],
                    'odds': bet_info['odds'],
                    'sportsbook': row.get('sportsbook', 'Unknown'),
                    'confidence_level': confidence_level,
                    'value_category': self.classify_value_bet(value_scores['best_edge'])
                }
                
                value_bets.append(value_bet)
        
        if value_bets:
            return pd.DataFrame(value_bets).sort_values('expected_value', ascending=False)
        return pd.DataFrame()
    
    def rank_value_bets(self, value_bets_df: pd.DataFrame) -> pd.DataFrame:
        """Rank value bets by various criteria"""
        if value_bets_df.empty:
            return value_bets_df
        
        # Calculate composite score
        # Weighted combination of edge, EV, and confidence
        value_bets_df['composite_score'] = (
            value_bets_df['edge'] * 0.4 +
            (value_bets_df['expected_value'] / 100) * 0.3 +
            value_bets_df['confidence_level'] * 0.3
        )
        
        # Sort by composite score
        ranked = value_bets_df.sort_values('composite_score', ascending=False)
        
        return ranked


