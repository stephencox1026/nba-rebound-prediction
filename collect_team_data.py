"""Script to collect team statistics data"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.helpers import setup_logging, get_season_from_date, get_years_back_date
from utils.database import DatabaseManager
from data_collectors.nba_data_collector import NBADataCollector
from config.config import HISTORICAL_YEARS

logger = setup_logging(__name__)


def collect_team_data(years: int = HISTORICAL_YEARS):
    """Collect team statistics data"""
    logger.info(f"Starting team data collection for {years} years")
    
    db_manager = DatabaseManager()
    nba_collector = NBADataCollector()
    
    try:
        # Get all teams
        logger.info("Fetching team list...")
        all_teams_df = nba_collector.get_all_teams()
        
        if all_teams_df.empty:
            logger.error("No teams found")
            return
        
        logger.info(f"Found {len(all_teams_df)} teams")
        
        # Collect team stats for each season
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        total_games = 0
        
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
            
            for idx, team in all_teams_df.iterrows():
                team_id = team['id']
                team_name = team['full_name']
                
                try:
                    logger.info(f"Collecting stats for {team_name} (ID: {team_id})")
                    team_data = nba_collector.collect_team_stats_for_season(team_id, season)
                    
                    if not team_data.empty:
                        # Add opponent_team_id placeholder (would need team mapping)
                        if 'opponent_team_id' not in team_data.columns:
                            team_data['opponent_team_id'] = None
                        
                        db_manager.insert_team_stats(team_data)
                        total_games += len(team_data)
                        logger.info(f"Stored {len(team_data)} games for {team_name}, season {season}")
                    else:
                        logger.warning(f"No data collected for {team_name}, season {season}")
                        
                except Exception as e:
                    logger.error(f"Error collecting team stats for {team_name}: {e}")
                    continue
        
        logger.info(f"Team data collection completed. Total games stored: {total_games}")
        
    except Exception as e:
        logger.error(f"Error in team data collection: {e}", exc_info=True)
    finally:
        db_manager.close()


if __name__ == "__main__":
    collect_team_data()


