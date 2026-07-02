"""Betting line parser for various formats"""
import re
from typing import Optional, Dict, Tuple
import logging

from utils.helpers import setup_logging

logger = setup_logging(__name__)


class BettingLineParser:
    """Parses betting lines from various formats"""
    
    def __init__(self):
        pass
    
    def parse_american_odds(self, odds: int) -> float:
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def parse_decimal_odds(self, odds: float) -> float:
        """Convert decimal odds to implied probability"""
        return 1.0 / odds
    
    def parse_fractional_odds(self, odds_str: str) -> float:
        """Convert fractional odds to implied probability"""
        # Format: "5/2" or "5-2"
        match = re.match(r'(\d+)[/-](\d+)', odds_str)
        if match:
            numerator = int(match.group(1))
            denominator = int(match.group(2))
            decimal = (numerator / denominator) + 1
            return 1.0 / decimal
        return 0.0
    
    def parse_over_under_line(self, line_str: str) -> Optional[float]:
        """Parse over/under line value from string
        
        Examples:
            "O 10.5" -> 10.5
            "Over 10.5" -> 10.5
            "U 8" -> 8.0
            "Under 8" -> 8.0
        """
        # Remove common prefixes
        line_str = line_str.strip().upper()
        
        # Pattern for over/under with number
        patterns = [
            r'O\s*(\d+\.?\d*)',
            r'OVER\s*(\d+\.?\d*)',
            r'U\s*(\d+\.?\d*)',
            r'UNDER\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line_str)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def extract_line_from_market(self, market_data: Dict) -> Optional[float]:
        """Extract line value from market data"""
        # Try different possible fields
        for field in ['line', 'point', 'line_value', 'total', 'points']:
            if field in market_data:
                try:
                    return float(market_data[field])
                except (ValueError, TypeError):
                    continue
        
        # Try parsing from description or name
        for field in ['description', 'name', 'title']:
            if field in market_data:
                line = self.parse_over_under_line(str(market_data[field]))
                if line is not None:
                    return line
        
        return None
    
    def parse_betting_line(self, line_data: Dict) -> Dict:
        """Parse complete betting line data"""
        parsed = {
            'line_value': None,
            'over_odds': None,
            'under_odds': None,
            'over_implied_prob': None,
            'under_implied_prob': None
        }
        
        # Extract line value
        parsed['line_value'] = self.extract_line_from_market(line_data)
        
        # Extract odds
        if 'over_odds' in line_data:
            parsed['over_odds'] = line_data['over_odds']
            parsed['over_implied_prob'] = self.parse_american_odds(parsed['over_odds'])
        
        if 'under_odds' in line_data:
            parsed['under_odds'] = line_data['under_odds']
            parsed['under_implied_prob'] = self.parse_american_odds(parsed['under_odds'])
        
        return parsed


