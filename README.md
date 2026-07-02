# NBA Rebound Prediction Model

A comprehensive machine learning system for predicting NBA player rebounds and identifying value betting opportunities by comparing model predictions to gambling lines.

## Features

- **Historical Data Collection**: Collects 5 years of NBA player and team statistics
- **Advanced Feature Engineering**: 
  - Last 10 game rolling averages
  - Team metrics (pace, FG%, shots attempted)
  - Matchup features (height advantage, primary defender estimation)
  - Dynamic time-based features
- **Machine Learning Models**: Trains XGBoost, Random Forest, and Gradient Boosting models
- **Dynamic Predictions**: Generates predictions for each game based on latest data
- **Value Bet Identification**: Compares predictions to betting lines to find profitable opportunities
- **Desktop GUI**: Easy-to-use interface with color-coded value bets and real-time updates

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Setup

1. Clone or download this repository

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### API Keys

The system uses The Odds API for betting lines. While the NBA API (nba_api library) doesn't require an API key, betting odds do.

1. **Get The Odds API Key**:
   - Visit [The Odds API](https://the-odds-api.com/)
   - Sign up for a free account (500 requests/month on free tier)
   - Get your API key

2. **Set Environment Variable**:
   ```bash
   export ODDS_API_KEY="your_api_key_here"
   ```
   
   On Windows:
   ```cmd
   set ODDS_API_KEY=your_api_key_here
   ```

   Or create a `.env` file in the project root (not included in repo for security).

### Database

The system uses SQLite for local data storage. The database will be created automatically at `data/nba_rebounds.db` on first run.

## Usage

### Step 1: Collect Historical Data

Before training the model, you need to collect historical NBA data:

```bash
python collect_data.py
```

This script will:
- Fetch player statistics for the last 5 years
- Collect team statistics
- Store player roster information (height, position, etc.)
- Save everything to the SQLite database

**Note**: This process can take several hours depending on the number of players. The script includes rate limiting to avoid API restrictions.

### Step 2: Train the Model

Once you have collected data, train the machine learning model:

```bash
python train_model_script.py
```

This will:
- Load historical data from the database
- Engineer features for each game
- Train multiple models (XGBoost, Random Forest, Gradient Boosting)
- Evaluate and select the best model
- Save the model for predictions

### Step 3: Run the Application

Launch the GUI application:

```bash
python main.py
```

The GUI provides:
- **Table View**: All player props with predictions and betting lines
- **Value Bet Highlighting**: 
  - Green: High value bets (15%+ edge)
  - Yellow: Medium value bets (5-15% edge)
  - Red: Low value or no edge
- **Filters**: Filter by value category, sort by various metrics
- **Auto-Update**: Toggle automatic data refresh
- **Manual Refresh**: Update data on demand

## Project Structure

```
Project 3/
├── data_collectors/      # Data collection modules
│   ├── nba_data_collector.py
│   ├── espn_data_collector.py
│   └── betting_odds_collector.py
├── features/            # Feature engineering
│   ├── player_features.py
│   ├── team_features.py
│   ├── matchup_features.py
│   └── feature_aggregator.py
├── model/               # ML models
│   ├── train_model.py
│   ├── model_manager.py
│   └── predictor.py
├── analysis/            # Value bet analysis
│   ├── value_calculator.py
│   └── line_parser.py
├── gui/                 # GUI application
│   ├── main_window.py
│   └── update_manager.py
├── config/              # Configuration
│   └── config.py
├── utils/               # Utilities
│   ├── database.py
│   └── helpers.py
├── data/                # Database storage
├── models/              # Saved models
├── logs/                # Application logs
├── main.py             # Main entry point
├── collect_data.py     # Data collection script
├── train_model_script.py  # Model training script
└── requirements.txt    # Python dependencies
```

## Features Explained

### Player Features
- **Last 10 Game Rebound Average**: Rolling average of rebounds
- **Last 10 Game Minutes Average**: Rolling average of minutes played
- **Rebound Momentum**: Trend indicator comparing recent vs. previous performance
- **Rebound Rate**: Rebounds per minute
- **Season Averages**: Expanding averages for the season

### Team Features
- **Team Shots Attempted**: Offensive rebound opportunities
- **Opponent Shots Attempted**: Defensive rebound opportunities
- **Field Goal Percentage**: Missed shots = rebound opportunities
- **Pace of Play**: Possessions per 48 minutes (more possessions = more rebounds)

### Matchup Features
- **Height Advantage**: Player height vs. primary defender height
- **Team Size Metrics**: Average height of players on court
- **Historical Head-to-Head**: Performance against specific opponent

### Value Bet Calculation

The system calculates:
- **Win Probability**: Based on model prediction and line value
- **Expected Value (EV)**: Expected profit/loss for a $100 bet
- **Edge**: Difference between model probability and implied probability from odds
- **Value Category**: High (15%+), Medium (5-15%), or Low (<5%)

## Model Performance

The model is evaluated using:
- **MAE (Mean Absolute Error)**: Average prediction error in rebounds
- **RMSE (Root Mean Squared Error)**: Penalizes larger errors more
- **R² Score**: Proportion of variance explained
- **Accuracy**: Percentage of predictions within 1 rebound

Typical performance metrics:
- MAE: ~1.5-2.0 rebounds
- RMSE: ~2.0-2.5 rebounds
- R²: ~0.4-0.6
- Accuracy (within 1): ~40-50%

## Troubleshooting

### Model Not Found Error
If you see "Model Not Found", you need to train a model first:
```bash
python train_model_script.py
```

### No Data in Database
If the database is empty, collect data:
```bash
python collect_data.py
```

### API Rate Limiting
The NBA API has rate limits. The system includes delays between requests. If you encounter rate limiting:
- Increase `REQUEST_DELAY` in `config/config.py`
- Reduce the number of players in `collect_data.py` (sample_size)

### Betting Odds Not Available
If betting odds are not showing:
- Verify your ODDS_API_KEY is set correctly
- Check your API quota at The Odds API dashboard
- The free tier allows 500 requests/month

## Limitations

1. **Primary Defender Data**: The system estimates primary defenders based on position matching. Actual lineup data would improve accuracy.

2. **Betting API**: Free tier of The Odds API has limited requests. Consider upgrading for production use.

3. **Real-time Updates**: Data collection takes time. Predictions are based on available data at prediction time.

4. **Model Accuracy**: Predictions are probabilistic. Always use proper bankroll management when betting.

## Future Enhancements

- Injury report integration
- Rest days and back-to-back game analysis
- Home/away splits
- Advanced matchup analysis (defensive rebounding rates)
- Kelly Criterion for bet sizing
- Historical betting line tracking
- Multiple sportsbook line comparison

## License

This project is for educational purposes. Use at your own risk when making betting decisions.

## Disclaimer

This software is provided "as is" without warranty. Sports betting involves risk. The predictions and value calculations are estimates based on historical data and should not be considered guarantees. Always gamble responsibly and within your means.

## Support

For issues or questions:
1. Check the logs in the `logs/` directory
2. Review the configuration in `config/config.py`
3. Ensure all dependencies are installed correctly

## Acknowledgments

- NBA API data provided by [nba_api](https://github.com/swar/nba_api)
- Betting odds from [The Odds API](https://the-odds-api.com/)


