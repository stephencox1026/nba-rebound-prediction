"""NBA API data collector for player stats, team stats, and game logs"""
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging

from nba_api.stats.endpoints import (
    playergamelog,
    teamgamelog,
    commonplayerinfo,
    commonteamroster,
    leaguegamefinder,
    teamdashboardbygamesplits,
    playergamestreakfinder
)
from nba_api.stats.static import players, teams
from nba_api.live.nba.endpoints import scoreboard

from utils.helpers import setup_logging, get_season_from_date, format_date, retry_on_failure
from config.config import REQUEST_DELAY, HISTORICAL_YEARS

logger = setup_logging(__name__)


class NBADataCollector:
    """Collects NBA data using the nba_api library"""
    
    def __init__(self):
        self.request_delay = REQUEST_DELAY
        logger.info("NBA Data Collector initialized")
    
    def _delay(self):
        """Add delay between requests to avoid rate limiting"""
        time.sleep(self.request_delay)
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def get_player_game_log(self, player_id: int, season: str) -> pd.DataFrame:
        """Get game log for a specific player and season"""
        try:
            self._delay()
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season
            )
            df = gamelog.get_data_frames()[0]
            if not df.empty:
                df['player_id'] = player_id
            return df
        except Exception as e:
            logger.error(f"Error fetching game log for player {player_id}, season {season}: {e}")
            return pd.DataFrame()
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def get_team_game_log(self, team_id: int, season: str) -> pd.DataFrame:
        """Get game log for a specific team and season"""
        try:
            self._delay()
            # Try with explicit season type
            gamelog = teamgamelog.TeamGameLog(
                team_id=team_id,
                season=season,
                season_type_all_star='Regular Season'
            )
            df = gamelog.get_data_frames()[0]
            if not df.empty:
                df['team_id'] = team_id
                return df
            
            # If empty, try without season type
            logger.warning(f"Empty result with season type, trying without...")
            self._delay()
            gamelog = teamgamelog.TeamGameLog(
                team_id=team_id,
                season=season
            )
            df = gamelog.get_data_frames()[0]
            if not df.empty:
                df['team_id'] = team_id
            return df
        except Exception as e:
            logger.error(f"Error fetching game log for team {team_id}, season {season}: {e}")
            return pd.DataFrame()
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def get_team_games_by_date_range(self, team_id: int, start_date: str, end_date: str) -> pd.DataFrame:
        """Get team games using LeagueGameFinder for a date range"""
        try:
            self._delay()
            gamefinder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team_id,
                date_from_nullable=start_date,
                date_to_nullable=end_date,
                season_type_nullable='Regular Season'
            )
            df = gamefinder.get_data_frames()[0]
            if not df.empty:
                df['team_id'] = team_id
            return df
        except Exception as e:
            logger.error(f"Error fetching team games by date range: {e}")
            return pd.DataFrame()
    
    def get_player_info(self, player_id: int) -> Optional[Dict]:
        """Get player information including height, weight, position"""
        try:
            self._delay()
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            df = player_info.get_data_frames()[0]
            if not df.empty:
                return df.iloc[0].to_dict()
            return None
        except Exception as e:
            logger.error(f"Error fetching player info for {player_id}: {e}")
            return None
    
    def get_all_players(self) -> pd.DataFrame:
        """Get list of all NBA players"""
        try:
            self._delay()
            all_players = players.get_players()
            return pd.DataFrame(all_players)
        except Exception as e:
            logger.error(f"Error fetching all players: {e}")
            return pd.DataFrame()
    
    def get_all_teams(self) -> pd.DataFrame:
        """Get list of all NBA teams"""
        try:
            self._delay()
            all_teams = teams.get_teams()
            return pd.DataFrame(all_teams)
        except Exception as e:
            logger.error(f"Error fetching all teams: {e}")
            return pd.DataFrame()
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def get_games_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get all games within a date range"""
        try:
            self._delay()
            gamefinder = leaguegamefinder.LeagueGameFinder(
                date_from_nullable=start_date,
                date_to_nullable=end_date
            )
            df = gamefinder.get_data_frames()[0]
            return df
        except Exception as e:
            logger.error(f"Error fetching games from {start_date} to {end_date}: {e}")
            return pd.DataFrame()
    
    def get_team_dashboard_stats(self, team_id: int, season: str) -> pd.DataFrame:
        """Get team dashboard statistics including pace"""
        try:
            self._delay()
            dashboard = teamdashboardbygamesplits.TeamDashboardByGameSplits(
                team_id=team_id,
                season=season
            )
            # Get overall stats (first dataframe usually contains season totals)
            data_frames = dashboard.get_data_frames()
            if data_frames:
                df = data_frames[0]
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching team dashboard for {team_id}, season {season}: {e}")
            return pd.DataFrame()
    
    def get_team_season_pace(self, team_id: int, season: str) -> float:
        """Get team pace for a season"""
        dashboard_df = self.get_team_dashboard_stats(team_id, season)
        if dashboard_df.empty:
            return 100.0  # League average
        
        # Look for pace column (might be named differently)
        pace_cols = [col for col in dashboard_df.columns if 'PACE' in col.upper() or 'POSS' in col.upper()]
        if pace_cols:
            pace_value = dashboard_df.iloc[0][pace_cols[0]]
            try:
                return float(pace_value)
            except (ValueError, TypeError):
                pass
        
        return 100.0  # Default league average
    
    def get_today_games(self) -> pd.DataFrame:
        """Get today's NBA games"""
        try:
            self._delay()
            scoreboard_data = scoreboard.ScoreBoard()
            # ScoreBoard returns a dictionary, not dataframes
            if hasattr(scoreboard_data, 'get_data_frames'):
                games = scoreboard_data.get_data_frames()[0]
                return games
            else:
                # Try alternative approach
                games_data = scoreboard_data.game_header
                if games_data:
                    return pd.DataFrame(games_data)
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching today's games: {e}")
            return pd.DataFrame()
    
    def collect_player_stats_for_season(self, player_id: int, season: str) -> pd.DataFrame:
        """Collect and format player stats for a season"""
        df = self.get_player_game_log(player_id, season)
        if df.empty:
            return df
        
        # Rename columns to match database schema
        column_mapping = {
            'GAME_DATE': 'game_date',
            'MATCHUP': 'matchup',
            'WL': 'win_loss',
            'MIN': 'minutes_played',
            'REB': 'rebounds',
            'OREB': 'offensive_rebounds',
            'DREB': 'defensive_rebounds',
            'PTS': 'points',
            'AST': 'assists',
            'FGA': 'field_goals_attempted',
            'FGM': 'field_goals_made',
        }
        
        # Select and rename columns
        available_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=available_cols)
        
        # Extract opponent and home/away from matchup
        if 'matchup' in df.columns:
            df['is_home'] = df['matchup'].str.contains('vs.').astype(int)
            # Extract opponent team abbreviation from matchup
            # Matchup format: "DAL vs. LAL" (home) or "DAL @ LAL" (away)
            # We need the opponent, not the player's team
            def extract_opponent(matchup_str, player_team_abbr=None):
                if pd.isna(matchup_str):
                    return None
                import re
                teams = re.findall(r'([A-Z]{3})', str(matchup_str))
                if len(teams) >= 2:
                    # If we know player's team, return the other one
                    if player_team_abbr and player_team_abbr in teams:
                        teams.remove(player_team_abbr)
                        return teams[0] if teams else None
                    # Otherwise, if format is "TEAM vs. OPP" or "TEAM @ OPP", return second team
                    return teams[1] if len(teams) > 1 else teams[0]
                return None
            
            # Try to get player's team abbreviation from first game or use first team in matchup
            if not df.empty:
                first_matchup = df['matchup'].iloc[0] if 'matchup' in df.columns else ''
                import re
                first_teams = re.findall(r'([A-Z]{3})', str(first_matchup))
                player_team_abbr = first_teams[0] if first_teams else None
                
                df['opponent_team_abbreviation'] = df['matchup'].apply(
                    lambda x: extract_opponent(x, player_team_abbr)
                )
            else:
                df['opponent_team_abbreviation'] = df['matchup'].str.extract(r'([A-Z]{3})')
        
        # Add season
        df['season'] = season
        
        # Parse game_date - handle multiple date formats
        if 'game_date' in df.columns:
            try:
                df['game_date'] = pd.to_datetime(df['game_date'], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d')
            except:
                # Fallback to infer format
                df['game_date'] = pd.to_datetime(df['game_date'], errors='coerce').dt.strftime('%Y-%m-%d')
            # Drop rows with invalid dates
            df = df.dropna(subset=['game_date'])
        
        return df
    
    def collect_historical_player_data(self, player_id: int, years_back: int = 5) -> pd.DataFrame:
        """Collect historical player data for specified years"""
        all_data = []
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # NBA season starts in October
        for year_offset in range(years_back):
            year = current_year - year_offset
            if current_month >= 10:
                # Current season
                if year_offset == 0:
                    season = f"{year}-{str(year + 1)[2:]}"
                else:
                    season = f"{year - 1}-{str(year)[2:]}"
            else:
                # Past seasons
                season = f"{year - 1}-{str(year)[2:]}"
            
            logger.info(f"Collecting data for player {player_id}, season {season}")
            season_data = self.collect_player_stats_for_season(player_id, season)
            if not season_data.empty:
                all_data.append(season_data)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    def collect_team_stats_for_season(self, team_id: int, season: str) -> pd.DataFrame:
        """Collect and format team stats for a season"""
        df = self.get_team_game_log(team_id, season)
        
        # If empty, try using date range approach
        if df.empty:
            # Convert season to date range (NBA season: Oct - June)
            year_part = season.split('-')[0]
            start_year = int(year_part)
            start_date = f"{start_year}-10-01"
            end_date = f"{start_year + 1}-06-30"
            
            logger.info(f"Trying date range approach: {start_date} to {end_date}")
            df = self.get_team_games_by_date_range(team_id, start_date, end_date)
        
        if df.empty:
            return df
        
        # Rename columns
        column_mapping = {
            'GAME_DATE': 'game_date',
            'MATCHUP': 'matchup',
            'WL': 'win_loss',
            'FGA': 'field_goals_attempted',
            'FGM': 'field_goals_made',
            'FG_PCT': 'field_goal_percentage',
            'FG3A': 'three_pointers_attempted',
            'FG3M': 'three_pointers_made',
            'REB': 'total_rebounds',
            'OREB': 'offensive_rebounds',
            'DREB': 'defensive_rebounds',
            'PTS': 'points',
        }
        
        available_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=available_cols)
        
        # Add team_id and team_abbreviation (required by database)
        df['team_id'] = team_id
        if 'TEAM_ABBREVIATION' in df.columns:
            df['team_abbreviation'] = df['TEAM_ABBREVIATION']
        elif 'team_abbreviation' not in df.columns:
            # Try to get from team info if available
            df['team_abbreviation'] = None
        
        # Extract opponent from matchup
        if 'matchup' in df.columns:
            df['is_home'] = df['matchup'].str.contains('vs.').astype(int)
            # Extract opponent team abbreviation
            # Matchup format: "ATL vs. BOS" or "BOS @ ATL"
            opponent_match = df['matchup'].str.extract(r'(?:vs\.|@)\s*([A-Z]{3})')
            if not opponent_match.empty:
                df['opponent_team_abbreviation'] = opponent_match[0]
            else:
                df['opponent_team_abbreviation'] = None
        
        df['season'] = season
        
        # Get team pace for the season (from dashboard)
        team_pace = self.get_team_season_pace(team_id, season)
        df['pace'] = team_pace
        
        # Parse game_date - handle multiple date formats
        if 'game_date' in df.columns:
            try:
                df['game_date'] = pd.to_datetime(df['game_date'], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d')
            except:
                df['game_date'] = pd.to_datetime(df['game_date'], errors='coerce').dt.strftime('%Y-%m-%d')
            # Drop rows with invalid dates
            df = df.dropna(subset=['game_date'])
        
        # Ensure numeric columns are numeric
        numeric_cols = ['field_goals_attempted', 'field_goals_made', 'field_goal_percentage',
                       'three_pointers_attempted', 'three_pointers_made', 'total_rebounds',
                       'offensive_rebounds', 'defensive_rebounds', 'points', 'pace']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df

