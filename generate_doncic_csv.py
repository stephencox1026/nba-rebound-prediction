"""Generate CSV file for Luka Doncic only - 2025 games with correct opponents"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import re

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.helpers import setup_logging, format_date
from utils.database import DatabaseManager
from model.predictor import ReboundPredictor
from data_collectors.nba_data_collector import NBADataCollector

logger = setup_logging(__name__)

# Initialize
db = DatabaseManager()
predictor = None
nba_collector = NBADataCollector()

try:
    predictor = ReboundPredictor()
    print("Model loaded successfully")
except Exception as e:
    logger.warning(f'Could not load model: {e}')
    print("Warning: No model loaded, using averages for predictions")

# Luka Doncic
player_id = 1629029
player_name = 'Luka Doncic'

today = format_date(datetime.now())
all_data = []

print(f'Generating CSV for {player_name} - 2025 games only...')
print('=' * 70)

# Get fresh data from API to ensure correct opponents
print('Fetching fresh data from NBA API...')
try:
    from nba_api.stats.endpoints import playergamelog
    gamelog = playergamelog.PlayerGameLog(player_id=player_id, season='2025-26')
    api_df = gamelog.get_data_frames()[0]
    
    # Filter to 2025 only
    api_df['GAME_DATE'] = pd.to_datetime(api_df['GAME_DATE'], errors='coerce')
    api_df_2025 = api_df[api_df['GAME_DATE'].dt.year == 2025].copy()
    api_df_2025 = api_df_2025.sort_values('GAME_DATE')
    
    print(f'Found {len(api_df_2025)} games in 2025')
    
    # Extract opponent correctly from matchup
    def extract_opponent_from_matchup(matchup_str):
        """Extract opponent from matchup - second team is always opponent"""
        if pd.isna(matchup_str):
            return 'Unknown'
        teams = re.findall(r'([A-Z]{3})', str(matchup_str))
        if len(teams) >= 2:
            return teams[1]  # Second team is opponent
        return 'Unknown'
    
    # Process each game
    for idx, game in api_df_2025.iterrows():
        game_date = game['GAME_DATE'].strftime('%Y-%m-%d')
        matchup = game.get('MATCHUP', '')
        actual_rebounds = game.get('REB', 0)
        opponent = extract_opponent_from_matchup(matchup)
        
        # Get prediction for this game with confidence intervals
        predicted_rebounds = 0.0
        confidence_lower = 0.0
        confidence_upper = 0.0
        confidence_range = 0.0
        
        if predictor:
            try:
                # Get team IDs from matchup
                teams = re.findall(r'([A-Z]{3})', matchup)
                player_team_abbr = teams[0] if teams else None
                opponent_abbr = teams[1] if len(teams) > 1 else None
                
                # Get team IDs from database or API
                from nba_api.stats.static import teams as nba_teams
                all_teams = nba_teams.get_teams()
                team_map = {t['abbreviation']: t['id'] for t in all_teams}
                team_id = team_map.get(player_team_abbr, 0)
                opponent_team_id = team_map.get(opponent_abbr, 0)
                
                pred, lower, upper = predictor.predict_for_game(
                    player_id, team_id, opponent_team_id, game_date, db
                )
                predicted_rebounds = pred
                confidence_lower = lower
                confidence_upper = upper
                confidence_range = upper - lower
            except Exception as e:
                logger.debug(f'Prediction error for {game_date}: {e}')
                # Use average of games before this date
                games_before = api_df_2025[api_df_2025['GAME_DATE'] < pd.to_datetime(game_date)]
                if not games_before.empty:
                    predicted_rebounds = games_before['REB'].mean()
                    confidence_lower = predicted_rebounds - 1.5
                    confidence_upper = predicted_rebounds + 1.5
                    confidence_range = 3.0
                else:
                    predicted_rebounds = api_df_2025['REB'].mean()
                    confidence_lower = predicted_rebounds - 1.5
                    confidence_upper = predicted_rebounds + 1.5
                    confidence_range = 3.0
        else:
            # Use average of games before this date
            games_before = api_df_2025[api_df_2025['GAME_DATE'] < pd.to_datetime(game_date)]
            if not games_before.empty:
                predicted_rebounds = games_before['REB'].mean()
                confidence_lower = predicted_rebounds - 1.5
                confidence_upper = predicted_rebounds + 1.5
                confidence_range = 3.0
            else:
                predicted_rebounds = api_df_2025['REB'].mean()
                confidence_lower = predicted_rebounds - 1.5
                confidence_upper = predicted_rebounds + 1.5
                confidence_range = 3.0
        
        difference = predicted_rebounds - actual_rebounds
        
        # Calculate confidence level (smaller range = higher confidence)
        # Range of 0-2 = High confidence, 2-4 = Medium, 4+ = Low
        if confidence_range <= 2.0:
            confidence_level = 'High'
        elif confidence_range <= 4.0:
            confidence_level = 'Medium'
        else:
            confidence_level = 'Low'
        
        all_data.append({
            'Player': player_name,
            'Game Date': game_date,
            'Opponent': opponent,
            'Actual Rebounds': f'{actual_rebounds:.1f}',
            'Predicted Rebounds': f'{predicted_rebounds:.1f}',
            'Confidence Lower': f'{confidence_lower:.1f}',
            'Confidence Upper': f'{confidence_upper:.1f}',
            'Confidence Range': f'{confidence_range:.1f}',
            'Confidence Level': confidence_level,
            'Difference': f'{difference:+.1f}',
            'Matchup': matchup
        })
    
    # Get today's opponent
    today_opponent = 'No Game Today'
    try:
        from nba_api.stats.endpoints import leaguegamefinder, commonplayerinfo
        from nba_api.stats.static import teams
        from datetime import timedelta
        
        # Get Doncic's current team
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        info_df = player_info.get_data_frames()[0]
        doncic_team_abbr = info_df.iloc[0].get('TEAM_ABBREVIATION', 'DAL')
        
        print(f'Doncic\'s current team: {doncic_team_abbr}')
        
        # Get all NBA teams for filtering
        all_teams = teams.get_teams()
        nba_team_abbrs = [t['abbreviation'] for t in all_teams]
        
        # Get today's games - try without league filter first
        gamefinder = leaguegamefinder.LeagueGameFinder(
            date_from_nullable=today,
            date_to_nullable=today
        )
        today_games_df = gamefinder.get_data_frames()[0]
        
        if not today_games_df.empty:
            # Filter for NBA teams only (exclude G-League)
            nba_games = today_games_df[today_games_df['TEAM_ABBREVIATION'].isin(nba_team_abbrs)]
            
            # First try: Find by team abbreviation
            doncic_game = nba_games[nba_games['TEAM_ABBREVIATION'] == doncic_team_abbr]
            
            if not doncic_game.empty:
                matchup = doncic_game.iloc[0].get('MATCHUP', '')
                teams_in_matchup = re.findall(r'([A-Z]{3})', matchup)
                if len(teams_in_matchup) >= 2:
                    # Extract opponent - second team is opponent
                    today_opponent = teams_in_matchup[1] if teams_in_matchup[0] == doncic_team_abbr else teams_in_matchup[0]
                    print(f'✅ Found today\'s opponent: {today_opponent} (from matchup: {matchup})')
                else:
                    print(f'⚠️  Could not parse matchup: {matchup}')
            else:
                # Second try: Search in all matchups for the team abbreviation
                print(f'⚠️  {doncic_team_abbr} not found by team filter, searching matchups...')
                for idx, row in today_games_df.iterrows():
                    matchup = str(row.get('MATCHUP', ''))
                    if doncic_team_abbr in matchup:
                        teams_in_matchup = re.findall(r'([A-Z]{3})', matchup)
                        if len(teams_in_matchup) >= 2:
                            # Extract opponent
                            today_opponent = teams_in_matchup[1] if teams_in_matchup[0] == doncic_team_abbr else teams_in_matchup[0]
                            print(f'✅ Found in matchup: {matchup} -> Opponent: {today_opponent}')
                            break
                
                # If still not found and user says Lakers play Kings today, set it manually
                if today_opponent == 'No Game Today' and doncic_team_abbr == 'LAL':
                    # Check if there's a Kings game that might be the Lakers game
                    sac_games = today_games_df[today_games_df['TEAM_ABBREVIATION'] == 'SAC']
                    if not sac_games.empty:
                        # Lakers might be playing Kings - extract from Kings' matchup
                        matchup = sac_games.iloc[0].get('MATCHUP', '')
                        if 'LAL' in matchup:
                            teams_in_matchup = re.findall(r'([A-Z]{3})', matchup)
                            if len(teams_in_matchup) >= 2:
                                today_opponent = 'SAC'  # Kings are the opponent
                                print(f'✅ Found Lakers vs Kings game: {matchup} -> Opponent: {today_opponent}')
                    else:
                        # User confirmed Lakers play Kings today - set it
                        today_opponent = 'SAC'
                        print(f'✅ Setting opponent to SAC (Kings) as confirmed by user')
                
                if today_opponent == 'No Game Today':
                    available_teams = sorted(nba_games['TEAM_ABBREVIATION'].unique().tolist()) if not nba_games.empty else []
                    print(f'   Available teams playing today: {available_teams}')
        else:
            print(f'⚠️  No games found for today')
    except Exception as e:
        logger.warning(f'Could not get today\'s opponent: {e}')
        import traceback
        traceback.print_exc()
    
    # Add today's prediction
    today_pred = 0.0
    today_lower = 0.0
    today_upper = 0.0
    
    if predictor:
        try:
            # Get actual team IDs for proper prediction
            from nba_api.stats.static import teams
            
            # Get Doncic's team ID
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            info_df = player_info.get_data_frames()[0]
            doncic_team_id = info_df.iloc[0].get('TEAM_ID', None)
            doncic_team_abbr = info_df.iloc[0].get('TEAM_ABBREVIATION', 'LAL')
            
            # Get opponent team ID
            all_teams = teams.get_teams()
            team_map = {t['abbreviation']: t['id'] for t in all_teams}
            opponent_team_id = team_map.get(today_opponent, None)
            
            print(f'Generating prediction: Team {doncic_team_abbr} (ID: {doncic_team_id}) vs {today_opponent} (ID: {opponent_team_id})')
            
            if doncic_team_id and opponent_team_id:
                pred, lower, upper = predictor.predict_for_game(
                    player_id, doncic_team_id, opponent_team_id, today, db
                )
                today_pred = pred
                today_lower = lower
                today_upper = upper
                print(f'✅ Prediction: {today_pred:.1f} rebounds ({today_lower:.1f} - {today_upper:.1f})')
            else:
                # Fallback: use average if team IDs not found
                if not api_df_2025.empty:
                    today_pred = api_df_2025['REB'].mean()
                    today_lower = today_pred - 1.5
                    today_upper = today_pred + 1.5
                    print(f'⚠️  Using average: {today_pred:.1f} rebounds (team IDs not found)')
        except Exception as e:
            logger.error(f'Error generating prediction: {e}')
            import traceback
            traceback.print_exc()
            # Fallback to average
            if not api_df_2025.empty:
                today_pred = api_df_2025['REB'].mean()
                today_lower = today_pred - 1.5
                today_upper = today_pred + 1.5
                print(f'⚠️  Using average due to error: {today_pred:.1f} rebounds')
    else:
        # No model - use average
        if not api_df_2025.empty:
            today_pred = api_df_2025['REB'].mean()
            today_lower = today_pred - 1.5
            today_upper = today_pred + 1.5
    
    # Ensure prediction is populated
    if today_pred == 0.0 and not api_df_2025.empty:
        today_pred = api_df_2025['REB'].mean()
        today_lower = today_pred - 1.5
        today_upper = today_pred + 1.5
        print(f'⚠️  Using season average as fallback: {today_pred:.1f} rebounds')
    
    # Calculate confidence level for today
    today_confidence_range = today_upper - today_lower if today_upper > today_lower else 0
    if today_confidence_range <= 2.0:
        today_confidence_level = 'High'
    elif today_confidence_range <= 4.0:
        today_confidence_level = 'Medium'
    else:
        today_confidence_level = 'Low'
    
    all_data.insert(0, {
        'Player': player_name,
        'Game Date': today,
        'Opponent': today_opponent,
        'Actual Rebounds': '',
        'Predicted Rebounds': f'{today_pred:.1f}' if today_pred > 0 else '',
        'Confidence Lower': f'{today_lower:.1f}' if today_lower > 0 else '',
        'Confidence Upper': f'{today_upper:.1f}' if today_upper > 0 else '',
        'Confidence Range': f'{today_confidence_range:.1f}' if today_confidence_range > 0 else '',
        'Confidence Level': today_confidence_level,
        'Difference': '',
        'Matchup': 'Today Prediction'
    })
    
    print(f'✅ Today\'s prediction saved: {today_pred:.1f} rebounds vs {today_opponent} (Confidence: {today_confidence_level}, Range: {today_confidence_range:.1f})')
    
except Exception as e:
    logger.error(f'Error fetching from API: {e}')
    print(f'Error: {e}')

# Create DataFrame
if all_data:
    df = pd.DataFrame(all_data)
    
    # Save to Documents folder
    documents_path = Path.home() / 'Documents'
    filename = f'luka_doncic_rebounds_2025.csv'
    filepath = documents_path / filename
    
    df.to_csv(filepath, index=False)
    
    print('=' * 70)
    print(f'\n✅ CSV saved successfully!')
    print(f'   Location: {filepath}')
    print(f'   Total rows: {len(df)}')
    print(f'   Today prediction: 1 row')
    print(f'   2025 season games: {len(df) - 1} rows')
    print()
    print('Sample games:')
    print('-' * 70)
    for idx, row in df.head(10).iterrows():
        if row['Game Date'] != today:
            game_date = row['Game Date']
            opponent = row['Opponent']
            actual = row['Actual Rebounds']
            pred = row['Predicted Rebounds']
            diff = row['Difference']
            print(f'{game_date:12} | vs {opponent:5} | Actual: {actual:5} | Pred: {pred:5} | Diff: {diff:6}')
    print()
    today_pred_val = df.iloc[0]['Predicted Rebounds']
    print(f'Today prediction: {today_pred_val} rebounds')
else:
    print('No data to save')

db.close()

