"""Daily predictions window for specific players"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import pandas as pd
import threading
import logging

from utils.helpers import setup_logging, format_date
from utils.database import DatabaseManager
from model.predictor import ReboundPredictor
from data_collectors.nba_data_collector import NBADataCollector

logger = setup_logging(__name__)


class DailyPredictionsWindow:
    """Window showing today's predictions and season history for specific players"""
    
    def __init__(self, parent=None):
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("Daily Rebound Predictions - Top Players")
        self.root.geometry("1600x900")
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.predictor = None
        self.nba_collector = NBADataCollector()
        
        # Player IDs - we'll look these up
        self.target_players = [
            "Luka Doncic",
            "Deandre Ayton", 
            "LeBron James",
            "Austin Reaves"
        ]
        
        self.player_ids = {}
        self.today_predictions = {}
        self.season_data = {}
        
        # Try to load model
        try:
            self.predictor = ReboundPredictor()
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
        
        self._create_widgets()
        self._setup_layout()
        
        # Load data
        self.root.after(100, self.load_data)
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        # Title frame
        title_frame = ttk.Frame(self.root, padding="10")
        title_label = ttk.Label(
            title_frame,
            text="Daily Rebound Predictions",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        today_label = ttk.Label(
            title_frame,
            text=f"Today: {format_date(datetime.now())}",
            font=("Arial", 12)
        )
        today_label.pack()
        title_frame.pack(fill="x")
        
        # Today's predictions frame
        self.today_frame = ttk.LabelFrame(self.root, text="Today's Predictions", padding="10")
        
        # Create grid for today's predictions
        headers = ["Player", "Today's Predicted Rebounds", "Confidence Range"]
        for col, header in enumerate(headers):
            label = ttk.Label(self.today_frame, text=header, font=("Arial", 11, "bold"))
            label.grid(row=0, column=col, padx=10, pady=5, sticky="w")
        
        # Player prediction labels (will be filled dynamically)
        self.today_labels = {}
        for i in range(4):
            for col in range(3):
                label = ttk.Label(self.today_frame, text="Loading...", font=("Arial", 10))
                label.grid(row=i+1, column=col, padx=10, pady=5, sticky="w")
                if col == 0:
                    self.today_labels[i] = {'player': label, 'prediction': None, 'confidence': None}
                elif col == 1:
                    self.today_labels[i]['prediction'] = label
                else:
                    self.today_labels[i]['confidence'] = label
        
        self.today_frame.pack(fill="x", padx=10, pady=10)
        
        # Season data frame
        self.season_frame = ttk.LabelFrame(self.root, text="Season History - Actual vs Predicted Rebounds", padding="10")
        
        # Create treeview for season data
        columns = ("Player", "Game Date", "Opponent", "Actual Rebounds", "Predicted Rebounds", "Difference")
        self.tree = ttk.Treeview(self.season_frame, columns=columns, show="headings", height=25)
        
        # Configure columns
        column_widths = {
            "Player": 150,
            "Game Date": 120,
            "Opponent": 100,
            "Actual Rebounds": 130,
            "Predicted Rebounds": 150,
            "Difference": 120
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 120), anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(self.season_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(self.season_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack table and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.season_frame.grid_rowconfigure(0, weight=1)
        self.season_frame.grid_columnconfigure(0, weight=1)
        
        self.season_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Status label
        self.status_label = ttk.Label(
            self.root,
            text="Loading player data...",
            foreground="orange"
        )
        self.status_label.pack(pady=5)
    
    def _setup_layout(self):
        """Setup widget layout - already done in _create_widgets"""
        pass
    
    def find_player_ids(self):
        """Find player IDs for target players"""
        try:
            from nba_api.stats.static import players
            all_players = players.get_players()
            
            # Create mapping
            player_map = {}
            for player in all_players:
                name = player['full_name'].lower()
                player_map[name] = player['id']
            
            # Find our players
            found = {}
            search_names = {
                "Luka Doncic": ["luka doncic", "luka"],
                "Deandre Ayton": ["deandre ayton", "deandre", "ayton"],
                "LeBron James": ["lebron james", "lebron", "le bron"],
                "Austin Reaves": ["austin reaves", "austin"]
            }
            
            for display_name, search_terms in search_names.items():
                for term in search_terms:
                    for name, player_id in player_map.items():
                        if term in name:
                            found[display_name] = player_id
                            logger.info(f"Found {display_name}: ID {player_id}")
                            break
                    if display_name in found:
                        break
            
            return found
            
        except Exception as e:
            logger.error(f"Error finding player IDs: {e}")
            return {}
    
    def load_data(self):
        """Load all data for the 4 players"""
        self.status_label.config(text="Finding players...", foreground="orange")
        self.root.update()
        
        # Find player IDs
        self.player_ids = self.find_player_ids()
        
        if len(self.player_ids) < 4:
            self.status_label.config(
                text=f"Warning: Only found {len(self.player_ids)}/4 players",
                foreground="orange"
            )
        
        # Load data in background thread
        thread = threading.Thread(target=self._load_data_thread, daemon=True)
        thread.start()
    
    def _load_data_thread(self):
        """Load data in background thread"""
        try:
            today = format_date(datetime.now())
            
            # Get today's games to see if players are playing
            try:
                today_games = self.nba_collector.get_today_games()
            except:
                today_games = pd.DataFrame()
            
            all_season_data = []
            
            for display_name, player_id in self.player_ids.items():
                self.root.after(0, lambda name=display_name: self.status_label.config(
                    text=f"Loading data for {name}...",
                    foreground="orange"
                ))
                
                # Get player stats
                player_stats = self.db_manager.get_player_stats(player_id=player_id)
                
                # If no data, try to collect it
                if player_stats.empty:
                    try:
                        logger.info(f"Collecting data for {display_name}...")
                        player_data = self.nba_collector.collect_historical_player_data(player_id, years_back=2)
                        if not player_data.empty:
                            player_data['player_name'] = display_name
                            if 'player_id' not in player_data.columns:
                                player_data['player_id'] = player_id
                            self.db_manager.insert_player_stats(player_data)
                            player_stats = self.db_manager.get_player_stats(player_id=player_id)
                    except Exception as e:
                        logger.error(f"Error collecting data for {display_name}: {e}")
                
                if player_stats.empty:
                    logger.warning(f"No data for {display_name}")
                    continue
                
                # Get current season data
                current_season = "2024-25"
                season_stats = player_stats[player_stats['season'] == current_season]
                
                if season_stats.empty:
                    season_stats = player_stats[player_stats['season'] == "2023-24"]
                
                if season_stats.empty:
                    season_stats = player_stats.sort_values('game_date').tail(82)
                
                season_stats = season_stats.sort_values('game_date')
                
                # Generate today's prediction
                today_pred = None
                today_lower = None
                today_upper = None
                
                if self.predictor:
                    try:
                        # Get most recent game info
                        if not season_stats.empty:
                            last_game = season_stats.iloc[-1]
                            team_id = last_game.get('team_id', 0)
                            opponent_team_id = last_game.get('opponent_team_id', 0)
                            
                            # For today, we'd need to know opponent - use placeholder
                            # In real scenario, would get from schedule
                            pred, lower, upper = self.predictor.predict_for_game(
                                player_id, team_id, opponent_team_id, today, self.db_manager
                            )
                            today_pred = pred
                            today_lower = lower
                            today_upper = upper
                    except Exception as e:
                        logger.warning(f"Error predicting for {display_name}: {e}")
                        # Use season average as fallback
                        if not season_stats.empty:
                            today_pred = season_stats['rebounds'].mean()
                            today_lower = today_pred - 1.5
                            today_upper = today_pred + 1.5
                
                self.today_predictions[display_name] = {
                    'prediction': today_pred,
                    'lower': today_lower,
                    'upper': today_upper
                }
                
                # Process season games
                for idx, game in season_stats.iterrows():
                    game_date = game['game_date']
                    actual_rebounds = game.get('rebounds', 0)
                    opponent_abbr = game.get('opponent_team_abbreviation', 'Unknown')
                    
                    # Get prediction for this game
                    predicted_rebounds = 0.0
                    if self.predictor:
                        try:
                            team_id = game.get('team_id', 0)
                            opponent_team_id = game.get('opponent_team_id', 0)
                            
                            pred, _, _ = self.predictor.predict_for_game(
                                player_id, team_id, opponent_team_id, game_date, self.db_manager
                            )
                            predicted_rebounds = pred
                        except:
                            # Use average up to that point
                            games_before = season_stats[season_stats['game_date'] < game_date]
                            if not games_before.empty:
                                predicted_rebounds = games_before['rebounds'].mean()
                            else:
                                predicted_rebounds = 0.0
                    else:
                        # No model - use average
                        games_before = season_stats[season_stats['game_date'] < game_date]
                        if not games_before.empty:
                            predicted_rebounds = games_before['rebounds'].mean()
                        else:
                            predicted_rebounds = 0.0
                    
                    all_season_data.append({
                        'player_name': display_name,
                        'game_date': game_date,
                        'opponent': opponent_abbr,
                        'actual_rebounds': actual_rebounds,
                        'predicted_rebounds': predicted_rebounds,
                        'difference': predicted_rebounds - actual_rebounds
                    })
            
            # Update UI in main thread
            self.root.after(0, lambda: self._update_display(all_season_data))
            
        except Exception as e:
            logger.error(f"Error in load thread: {e}", exc_info=True)
            self.root.after(0, lambda: self.status_label.config(
                text=f"Error: {e}",
                foreground="red"
            ))
    
    def _update_display(self, season_data):
        """Update the display with loaded data"""
        try:
            # Update today's predictions
            player_list = list(self.player_ids.keys())
            for i, display_name in enumerate(player_list[:4]):
                if display_name in self.today_predictions:
                    pred_data = self.today_predictions[display_name]
                    pred = pred_data.get('prediction', 0)
                    lower = pred_data.get('lower', pred - 1.5)
                    upper = pred_data.get('upper', pred + 1.5)
                    
                    self.today_labels[i]['player'].config(text=display_name)
                    if pred:
                        self.today_labels[i]['prediction'].config(
                            text=f"{pred:.1f} rebounds",
                            font=("Arial", 10, "bold"),
                            foreground="blue"
                        )
                        self.today_labels[i]['confidence'].config(
                            text=f"{lower:.1f} - {upper:.1f}",
                            font=("Arial", 9),
                            foreground="gray"
                        )
                    else:
                        self.today_labels[i]['prediction'].config(text="No prediction available")
                        self.today_labels[i]['confidence'].config(text="")
                else:
                    self.today_labels[i]['player'].config(text=display_name)
                    self.today_labels[i]['prediction'].config(text="No data")
                    self.today_labels[i]['confidence'].config(text="")
            
            # Clear and populate season table
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Sort by player, then by date
            df = pd.DataFrame(season_data)
            if not df.empty:
                df = df.sort_values(['player_name', 'game_date'])
                
                for _, row in df.iterrows():
                    # Color code based on accuracy
                    diff = row['difference']
                    if abs(diff) <= 1:
                        tag = "good"
                    elif abs(diff) <= 2:
                        tag = "ok"
                    else:
                        tag = "poor"
                    
                    self.tree.insert("", "end", values=(
                        row['player_name'],
                        row['game_date'],
                        row['opponent'],
                        f"{row['actual_rebounds']:.1f}",
                        f"{row['predicted_rebounds']:.1f}",
                        f"{diff:+.1f}"
                    ), tags=(tag,))
                
                # Configure tags for color coding
                self.tree.tag_configure("good", background="#d4edda")  # Light green
                self.tree.tag_configure("ok", background="#fff3cd")    # Light yellow
                self.tree.tag_configure("poor", background="#f8d7da")   # Light red
            
            self.status_label.config(
                text=f"Loaded data for {len(self.player_ids)} players, {len(season_data)} games",
                foreground="green"
            )
            
        except Exception as e:
            logger.error(f"Error updating display: {e}", exc_info=True)
            self.status_label.config(text=f"Error updating display: {e}", foreground="red")
    
    def on_closing(self):
        """Handle window closing"""
        self.db_manager.close()
        self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = DailyPredictionsWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()


