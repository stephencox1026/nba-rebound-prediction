# Player Analysis GUI - Quick Start Guide

## Running the Player Analysis Window

You can run the player analysis window in two ways:

### Option 1: From Main GUI
1. Run the main application: `python main.py`
2. Click the "Player Analysis" button in the top toolbar
3. A new window will open for player analysis

### Option 2: Standalone
Run directly: `python run_player_analysis.py`

## Using the Player Analysis Window

1. **Select Team**: Choose "Los Angeles Lakers" from the dropdown (or any other team)
2. **Select Players**: Check up to 5 players from the list
3. **Click "Analyze Selected Players"**: The system will:
   - Load all games for the selected players this season
   - Generate predictions for each game
   - Display a chart showing actual vs predicted rebounds
   - Show a table with game-by-game data

## Features

- **Visual Chart**: Line graph showing actual rebounds (solid line) vs predicted rebounds (dashed line) for each player
- **Game-by-Game Table**: Detailed table showing:
  - Player name
  - Game date
  - Opponent
  - Actual rebounds
  - Predicted rebounds
  - Difference (predicted - actual)

## Notes

- The window automatically loads Lakers players when opened
- You can select any team from the dropdown
- Up to 5 players can be analyzed at once
- Predictions use the trained machine learning model
- If a player has no data in the database, they won't appear in results
