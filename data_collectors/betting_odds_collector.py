"""Betting odds collector for player prop rebound over/under lines"""
import requests
import pandas as pd
import time
from datetime import datetime
from typing import Optional, List, Dict
import logging
import json

from utils.helpers import setup_logging, retry_on_failure, format_date
from config.config import ODDS_API_KEY, ODDS_API_BASE_URL, REQUEST_DELAY

logger = setup_logging(__name__)


class BettingOddsCollector:
    """Collects betting odds from The Odds API and other sources"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ODDS_API_KEY
        self.base_url = ODDS_API_BASE_URL
        self.request_delay = REQUEST_DELAY
        logger.info("Betting Odds Collector initialized")
    
    def _delay(self):
        """Add delay between requests"""
        time.sleep(self.request_delay)
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def get_player_props(self, sport: str = "basketball_nba", 
                        markets: str = "player_rebounds",
                        regions: str = "us") -> pd.DataFrame:
        """Get player prop bets from The Odds API"""
        if not self.api_key:
            logger.warning("No API key provided for betting odds. Using placeholder data.")
            return self._get_placeholder_odds()
        
        try:
            self._delay()
            url = f"{self.base_url}/sports/{sport}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": regions,
                "markets": markets,
                "oddsFormat": "american"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Parse the response into DataFrame
            return self._parse_odds_response(data)
            
        except Exception as e:
            logger.error(f"Error fetching betting odds: {e}")
            return self._get_placeholder_odds()
    
    def _parse_odds_response(self, data: List[Dict]) -> pd.DataFrame:
        """Parse The Odds API response into DataFrame"""
        records = []
        
        for game in data:
            game_date = game.get('commence_time', '')
            bookmakers = game.get('bookmakers', [])
            
            for bookmaker in bookmakers:
                sportsbook = bookmaker.get('title', '')
                markets_list = bookmaker.get('markets', [])
                
                for market in markets_list:
                    if market.get('key') == 'player_rebounds':
                        outcomes = market.get('outcomes', [])
                        
                        # Find over and under outcomes
                        over_outcome = None
                        under_outcome = None
                        line_value = None
                        
                        for outcome in outcomes:
                            name = outcome.get('name', '')
                            point = outcome.get('point', None)
                            
                            if 'over' in name.lower() or 'o ' in name.lower():
                                over_outcome = outcome
                                if point is not None:
                                    line_value = point
                            elif 'under' in name.lower() or 'u ' in name.lower():
                                under_outcome = outcome
                                if point is not None and line_value is None:
                                    line_value = point
                        
                        # Extract player name from outcome name
                        if over_outcome:
                            player_name = over_outcome.get('name', '').replace(' Over', '').replace(' O ', ' ').strip()
                            
                            record = {
                                'player_name': player_name,
                                'game_date': game_date,
                                'sportsbook': sportsbook,
                                'market_type': 'player_rebounds',
                                'line_value': line_value,
                                'over_odds': over_outcome.get('price', None),
                                'under_odds': under_outcome.get('price', None) if under_outcome else None,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Calculate implied probabilities
                            if record['over_odds']:
                                record['over_implied_prob'] = self._odds_to_probability(record['over_odds'])
                            if record['under_odds']:
                                record['under_implied_prob'] = self._odds_to_probability(record['under_odds'])
                            
                            records.append(record)
        
        if records:
            return pd.DataFrame(records)
        return pd.DataFrame()
    
    def _odds_to_probability(self, odds: int) -> float:
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def _get_placeholder_odds(self) -> pd.DataFrame:
        """Return placeholder odds data when API is unavailable"""
        logger.info("Using placeholder odds data. Configure API key for real data.")
        # Return empty DataFrame - will be populated when API is configured
        return pd.DataFrame(columns=[
            'player_name', 'game_date', 'sportsbook', 'market_type',
            'line_value', 'over_odds', 'under_odds', 'over_implied_prob',
            'under_implied_prob', 'timestamp'
        ])
    
    def get_historical_odds(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical odds for a date range"""
        # The Odds API may not support historical data on free tier
        # This would need to be implemented based on available API endpoints
        logger.warning("Historical odds collection not fully implemented")
        return pd.DataFrame()
    
    def search_player_props(self, player_name: str) -> pd.DataFrame:
        """Search for specific player's prop bets"""
        all_props = self.get_player_props()
        if all_props.empty:
            return all_props
        
        # Filter by player name
        filtered = all_props[
            all_props['player_name'].str.contains(player_name, case=False, na=False)
        ]
        return filtered
    
    def get_best_lines(self, player_name: str, bet_type: str = "over") -> pd.DataFrame:
        """Get best available lines for a player"""
        player_props = self.search_player_props(player_name)
        if player_props.empty:
            return player_props
        
        # Group by player and find best odds
        if bet_type.lower() == "over":
            best_lines = player_props.loc[player_props.groupby('player_name')['over_odds'].idxmax()]
        else:
            best_lines = player_props.loc[player_props.groupby('player_name')['under_odds'].idxmax()]
        
        return best_lines


