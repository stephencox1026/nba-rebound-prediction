"""Generate CSV file with daily predictions and season data"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

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

# Player IDs
player_ids = {
    'Luka Doncic': 1629029,
    'Deandre Ayton': 1629028,
    'LeBron James': 2544,
    'Austin Reaves': 1630559
}

today = format_date(datetime.now())
all_data = []

print('Generating CSV data for 4 players...')
print('=' * 60)

for player_name, player_id in player_ids.items():
    print(f'Processing {player_name}...')
    
    # Get player stats
    player_stats = db.get_player_stats(player_id=player_id)
    
    if player_stats.empty:
        print(f'  ⚠ No data for {player_name}')
        continue
    
    # Get current season - check what season format we have
    # NBA seasons: 2024-25, 2025-26, etc.
    current_date = datetime.now()
    if current_date.month >= 10:
        # October onwards - current season started
        current_season = f"{current_date.year}-{str(current_date.year + 1)[2:]}"
    else:
        # Before October - still in previous season
        current_season = f"{current_date.year - 1}-{str(current_date.year)[2:]}"
    
    # Try to get current season data
    season_stats = player_stats[player_stats['season'] == current_season].copy()
    
    # If empty, try the most recent season we have
    if season_stats.empty:
        available_seasons = sorted(player_stats['season'].unique().tolist(), reverse=True)
        if available_seasons:
            # Use most recent season
            most_recent_season = available_seasons[0]
            season_stats = player_stats[player_stats['season'] == most_recent_season].copy()
            current_season = most_recent_season
            print(f'  Using most recent season: {current_season}')
    
    # If still empty, get most recent games (current season)
    if season_stats.empty:
        # Get games from current calendar year
        current_year = current_date.year
        season_start = f"{current_year}-10-01" if current_date.month >= 10 else f"{current_year - 1}-10-01"
        season_stats = player_stats[player_stats['game_date'] >= season_start].copy()
        if not season_stats.empty:
            current_season = f"{current_date.year}-{str(current_date.year + 1)[2:]}" if current_date.month >= 10 else f"{current_date.year - 1}-{str(current_date.year)[2:]}"
            print(f'  Using games from current season period: {len(season_stats)} games')
    
    if season_stats.empty:
        print(f'  ⚠ No current season data available for {player_name}')
        continue
    
    season_stats = season_stats.sort_values('game_date')
    print(f'  Found {len(season_stats)} games for {current_season}')
    
    # Generate today's prediction
    today_pred = None
    today_lower = None
    today_upper = None
    
    if predictor:
        try:
            if not season_stats.empty:
                last_game = season_stats.iloc[-1]
                team_id = last_game.get('team_id', 0)
                opponent_team_id = last_game.get('opponent_team_id', 0)
                
                pred, lower, upper = predictor.predict_for_game(
                    player_id, team_id, opponent_team_id, today, db
                )
                today_pred = pred
                today_lower = lower
                today_upper = upper
                print(f'  Today prediction: {today_pred:.1f} rebounds ({today_lower:.1f} - {today_upper:.1f})')
        except Exception as e:
            logger.warning(f'Error predicting for {player_name}: {e}')
            if not season_stats.empty:
                today_pred = season_stats['rebounds'].mean()
                today_lower = today_pred - 1.5
                today_upper = today_pred + 1.5
                print(f'  Today prediction (avg): {today_pred:.1f} rebounds')
    else:
        if not season_stats.empty:
            today_pred = season_stats['rebounds'].mean()
            today_lower = today_pred - 1.5
            today_upper = today_pred + 1.5
            print(f'  Today prediction (avg): {today_pred:.1f} rebounds')
    
    # Add today's prediction row
    all_data.append({
        'Player': player_name,
        'Game Date': today,
        'Opponent': 'TBD',
        'Actual Rebounds': '',
        'Predicted Rebounds': f'{today_pred:.1f}' if today_pred else '',
        'Confidence Lower': f'{today_lower:.1f}' if today_lower else '',
        'Confidence Upper': f'{today_upper:.1f}' if today_upper else '',
        'Difference': '',
        'Type': 'Today Prediction',
        'Season': current_season
    })
    
    # Process season games - ensure opponent matches date
    for idx, game in season_stats.iterrows():
        game_date = game['game_date']
        actual_rebounds = game.get('rebounds', 0)
        
        # Get opponent - ensure it matches the game date
        opponent_abbr = game.get('opponent_team_abbreviation', None)
        matchup = game.get('matchup', '')
        
        # Extract opponent from matchup string if available (more reliable)
        if matchup:
            import re
            # Matchup format: "LAL vs. GSW" or "GSW @ LAL" or "LAL @ GSW"
            # Extract team abbreviations (3 letters)
            teams = re.findall(r'([A-Z]{3})', matchup)
            if teams:
                # Get player's team abbreviation
                player_team_abbr = game.get('team_abbreviation', '')
                # If we have player's team, opponent is the other one
                if player_team_abbr and player_team_abbr in teams:
                    teams.remove(player_team_abbr)
                    if teams:
                        opponent_abbr = teams[0]
                elif len(teams) == 2:
                    # Two teams found, use the second one (usually opponent)
                    opponent_abbr = teams[1]
                elif len(teams) == 1 and not player_team_abbr:
                    # Only one team found, might be opponent
                    opponent_abbr = teams[0]
        
        # Ensure we have a valid opponent
        if not opponent_abbr or opponent_abbr == 'Unknown' or pd.isna(opponent_abbr):
            opponent_abbr = 'Unknown'
        
        # Verify opponent by checking game logs if possible
        # For now, use what we have from the data
        
        # Get prediction for this game
        predicted_rebounds = 0.0
        if predictor:
            try:
                team_id = game.get('team_id', 0)
                opponent_team_id = game.get('opponent_team_id', 0)
                
                pred, _, _ = predictor.predict_for_game(
                    player_id, team_id, opponent_team_id, game_date, db
                )
                predicted_rebounds = pred
            except Exception as e:
                logger.debug(f'Prediction error for {player_name} on {game_date}: {e}')
                # Use average of games before this date
                games_before = season_stats[season_stats['game_date'] < game_date]
                if not games_before.empty:
                    predicted_rebounds = games_before['rebounds'].mean()
                else:
                    predicted_rebounds = season_stats['rebounds'].mean()
        else:
            # Use average of games before this date
            games_before = season_stats[season_stats['game_date'] < game_date]
            if not games_before.empty:
                predicted_rebounds = games_before['rebounds'].mean()
            else:
                predicted_rebounds = season_stats['rebounds'].mean()
        
        difference = predicted_rebounds - actual_rebounds
        
        all_data.append({
            'Player': player_name,
            'Game Date': game_date,
            'Opponent': opponent_abbr,
            'Actual Rebounds': f'{actual_rebounds:.1f}',
            'Predicted Rebounds': f'{predicted_rebounds:.1f}',
            'Confidence Lower': '',
            'Confidence Upper': '',
            'Difference': f'{difference:+.1f}',
            'Type': 'Season Game',
            'Season': current_season
        })

# Create DataFrame
df = pd.DataFrame(all_data)

# Save to Documents folder
documents_path = Path.home() / 'Documents'
filename = f'nba_rebound_predictions_{today}.csv'
filepath = documents_path / filename

df.to_csv(filepath, index=False)

print('=' * 60)
print(f'\n✅ CSV saved successfully!')
print(f'   Location: {filepath}')
print(f'   Total rows: {len(df)}')
print(f'   Today predictions: {len(df[df["Type"] == "Today Prediction"])}')
print(f'   Season games: {len(df[df["Type"] == "Season Game"])}')
print(f'\n📊 Columns:')
for col in df.columns:
    print(f'   - {col}')

db.close()

