"""Script to collect historical NBA data"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.helpers import setup_logging, get_season_from_date, get_years_back_date
from utils.database import DatabaseManager
from data_collectors.nba_data_collector import NBADataCollector
from config.config import HISTORICAL_YEARS

logger = setup_logging(__name__)


def collect_historical_data(years: int = HISTORICAL_YEARS):
    """Collect historical NBA data"""
    logger.info(f"Starting data collection for {years} years")
    
    db_manager = DatabaseManager()
    nba_collector = NBADataCollector()
    
    try:
        # Get all active players
        logger.info("Fetching player list...")
        all_players_df = nba_collector.get_all_players()
        
        if all_players_df.empty:
            logger.error("No players found")
            return
        
        logger.info(f"Found {len(all_players_df)} players")
        
        # Get all teams
        logger.info("Fetching team list...")
        all_teams_df = nba_collector.get_all_teams()
        
        # Collect data for each player (sample for testing - remove limit for full collection)
        sample_size = min(50, len(all_players_df))  # Limit for initial testing
        logger.info(f"Collecting data for {sample_size} players (sampling for testing)")
        
        for idx, player in all_players_df.head(sample_size).iterrows():
            player_id = player['id']
            player_name = player['full_name']
            
            logger.info(f"Processing player {player_name} (ID: {player_id})")
            
            try:
                # Collect historical player data
                player_data = nba_collector.collect_historical_player_data(player_id, years)
                
                if not player_data.empty:
                    # Add player name if not present
                    if 'player_name' not in player_data.columns:
                        player_data['player_name'] = player_name
                    
                    # Get team_id from first game if available (simplified - would need proper mapping)
                    # For now, set to None and let it be handled later
                    if 'team_id' not in player_data.columns:
                        player_data['team_id'] = None
                    if 'opponent_team_id' not in player_data.columns:
                        player_data['opponent_team_id'] = None
                    
                    try:
                        # Store in database
                        db_manager.insert_player_stats(player_data)
                        logger.info(f"Stored {len(player_data)} games for {player_name}")
                    except Exception as e:
                        logger.error(f"Error storing data for {player_name}: {e}")
                        # Try to insert row by row to identify problematic data
                        for idx, row in player_data.iterrows():
                            try:
                                db_manager.insert_player_stats(pd.DataFrame([row]))
                            except Exception as row_error:
                                logger.warning(f"Skipping row {idx} for {player_name}: {row_error}")
                
                # Collect player roster info
                player_info = nba_collector.get_player_info(player_id)
                if player_info:
                    roster_df = pd.DataFrame([{
                        'player_id': player_id,
                        'player_name': player_name,
                        'height_feet': player_info.get('HEIGHT_FEET'),
                        'height_inches': player_info.get('HEIGHT_INCHES'),
                        'weight_pounds': player_info.get('WEIGHT'),
                        'position': player_info.get('POSITION'),
                        'team_id': player_info.get('TEAM_ID'),
                        'season': get_season_from_date(datetime.now())
                    }])
                    db_manager.insert_player_roster(roster_df)
                
            except Exception as e:
                logger.error(f"Error processing player {player_name}: {e}")
                continue
        
        # Collect team stats
        logger.info("Collecting team statistics...")
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        for year_offset in range(years):
            year = current_year - year_offset
            if current_month >= 10:
                if year_offset == 0:
                    season = f"{year}-{str(year + 1)[2:]}"
                else:
                    season = f"{year - 1}-{str(year)[2:]}"
            else:
                season = f"{year - 1}-{str(year)[2:]}"
            
            logger.info(f"Collecting team stats for season {season}")
            
            for _, team in all_teams_df.iterrows():
                team_id = team['id']
                team_name = team['full_name']
                try:
                    logger.info(f"Collecting team stats for {team_name} (ID: {team_id})")
                    team_data = nba_collector.collect_team_stats_for_season(team_id, season)
                    if not team_data.empty:
                        # Ensure opponent_team_id is set (placeholder if not available)
                        if 'opponent_team_id' not in team_data.columns:
                            team_data['opponent_team_id'] = None
                        db_manager.insert_team_stats(team_data)
                        logger.info(f"Stored {len(team_data)} games for {team_name}, season {season}")
                    else:
                        logger.warning(f"No data collected for {team_name}, season {season}")
                except Exception as e:
                    logger.error(f"Error collecting team stats for {team_name}: {e}")
                    continue
        
        logger.info("Data collection completed")
        
    except Exception as e:
        logger.error(f"Error in data collection: {e}", exc_info=True)
    finally:
        db_manager.close()


if __name__ == "__main__":
    collect_historical_data()

