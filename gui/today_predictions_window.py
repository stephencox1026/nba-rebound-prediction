"""GUI window showing today's rebound predictions for all players"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import pandas as pd
import threading
import logging
from typing import List, Dict

from utils.helpers import setup_logging, format_date
from utils.database import DatabaseManager
from model.predictor import ReboundPredictor
from data_collectors.nba_data_collector import NBADataCollector
from nba_api.stats.endpoints import leaguegamefinder, commonplayerinfo
from nba_api.stats.static import teams

logger = setup_logging(__name__)


class TodayPredictionsWindow(tk.Toplevel):
    """Window displaying today's rebound predictions for all players"""
    
    def __init__(self, master, db_manager: DatabaseManager, 
                 nba_collector: NBADataCollector, predictor: ReboundPredictor):
        super().__init__(master)
        self.title("Today's Rebound Predictions")
        self.geometry("1400x900")
        
        self.db_manager = db_manager
        self.nba_collector = nba_collector
        self.predictor = predictor
        
        self.today = format_date(datetime.now())
        self.player_data = []
        
        self._create_widgets()
        self._setup_layout()
        self.load_predictions()
    
    def _create_widgets(self):
        """Create GUI widgets"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(header_frame, text=f"Today's Rebound Predictions - {self.today}", 
                 font=("Arial", 16, "bold")).pack(side="left")
        
        self.refresh_btn = ttk.Button(header_frame, text="Refresh", command=self.load_predictions)
        self.refresh_btn.pack(side="right", padx=5)
        
        # Status label
        self.status_label = ttk.Label(self, text="Loading predictions...", foreground="blue")
        self.status_label.pack(pady=5)
        
        # Notebook for confidence level tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create tabs for each confidence level
        self.high_frame = ttk.Frame(self.notebook)
        self.medium_frame = ttk.Frame(self.notebook)
        self.low_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.high_frame, text="High Confidence")
        self.notebook.add(self.medium_frame, text="Medium Confidence")
        self.notebook.add(self.low_frame, text="Low Confidence")
        
        # Create trees for each confidence level
        self._create_tree(self.high_frame, "high")
        self._create_tree(self.medium_frame, "medium")
        self._create_tree(self.low_frame, "low")
    
    def _create_tree(self, parent, confidence_type):
        """Create Treeview for a confidence level"""
        # Frame for tree and scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Treeview - simplified columns
        columns = ("Player", "Position", "Opponent", "Predicted REB", "Confidence Level")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=25)
        
        # Configure columns
        tree.heading("Player", text="Player")
        tree.heading("Position", text="Position")
        tree.heading("Opponent", text="Opponent")
        tree.heading("Predicted REB", text="Predicted REB")
        tree.heading("Confidence Level", text="Confidence Level")
        
        tree.column("Player", width=200)
        tree.column("Position", width=80)
        tree.column("Opponent", width=80)
        tree.column("Predicted REB", width=120)
        tree.column("Confidence Level", width=120)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Store tree reference
        setattr(self, f"{confidence_type}_tree", tree)
    
    def _setup_layout(self):
        """Setup window layout"""
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
    
    def load_predictions(self):
        """Load predictions in background thread"""
        self.status_label.config(text="Loading today's predictions...", foreground="blue")
        self.refresh_btn.config(state="disabled")
        threading.Thread(target=self._load_predictions_thread, daemon=True).start()
    
    def _load_predictions_thread(self):
        """Load predictions in background"""
        try:
            # Get today's games
            today_games = self._get_today_games()
            if today_games.empty:
                self.root.after(0, lambda: self.status_label.config(
                    text="No NBA games scheduled for today.", foreground="red"))
                return
            
            # Get all players playing today
            players_data = self._get_players_playing_today(today_games)
            
            # Filter by 20+ minutes average
            filtered_players = [p for p in players_data if p.get('avg_minutes', 0) >= 20.0]
            
            # Generate predictions
            predictions = []
            for player in filtered_players:
                try:
                    pred_data = self._generate_prediction(player)
                    if pred_data:
                        predictions.append(pred_data)
                except Exception as e:
                    logger.warning(f"Error predicting for {player.get('name', 'Unknown')}: {e}")
                    continue
            
            # Sort by confidence level and position
            sorted_predictions = self._sort_predictions(predictions)
            
            # Group by confidence level
            high_conf = [p for p in sorted_predictions if p['confidence_level'] == 'High']
            medium_conf = [p for p in sorted_predictions if p['confidence_level'] == 'Medium']
            low_conf = [p for p in sorted_predictions if p['confidence_level'] == 'Low']
            
            # Update GUI
            self.root.after(0, lambda: self._update_gui(high_conf, medium_conf, low_conf))
            
        except Exception as e:
            logger.error(f"Error loading predictions: {e}", exc_info=True)
            self.root.after(0, lambda: self.status_label.config(
                text=f"Error: {e}", foreground="red"))
        finally:
            self.root.after(0, lambda: self.refresh_btn.config(state="normal"))
    
    def _get_today_games(self) -> pd.DataFrame:
        """Get today's NBA games"""
        try:
            gamefinder = leaguegamefinder.LeagueGameFinder(
                date_from_nullable=self.today,
                date_to_nullable=self.today
            )
            df = gamefinder.get_data_frames()[0]
            
            # Filter for NBA teams only
            all_teams = teams.get_teams()
            nba_team_abbrs = [t['abbreviation'] for t in all_teams]
            nba_games = df[df['TEAM_ABBREVIATION'].isin(nba_team_abbrs)]
            
            return nba_games
        except Exception as e:
            logger.error(f"Error getting today's games: {e}")
            return pd.DataFrame()
    
    def _get_players_playing_today(self, today_games: pd.DataFrame) -> List[Dict]:
        """Get all players playing today with their stats"""
        players_data = []
        team_abbrs = today_games['TEAM_ABBREVIATION'].unique().tolist()
        
        for team_abbr in team_abbrs:
            try:
                # Get team roster
                team_info = [t for t in teams.get_teams() if t['abbreviation'] == team_abbr]
                if not team_info:
                    continue
                team_id = team_info[0]['id']
                
                # Get team roster from database or API
                roster = self.db_manager.get_player_roster()
                team_roster = roster[roster['team_id'] == team_id] if not roster.empty else pd.DataFrame()
                
                # Get player stats for this team
                team_stats = self.db_manager.get_player_stats()
                if team_stats.empty:
                    continue
                
                # Get unique players for this team
                team_players = team_stats[team_stats['team_abbreviation'] == team_abbr]
                player_ids = team_players['player_id'].unique()
                
                for player_id in player_ids:
                    player_games = team_players[team_players['player_id'] == player_id]
                    if player_games.empty:
                        continue
                    
                    # Calculate average minutes
                    avg_minutes = player_games['minutes_played'].mean() if 'minutes_played' in player_games.columns else 0
                    
                    # Get last 10 games average rebounds
                    last_10_games = player_games.sort_values('game_date').tail(10)
                    last_10_avg_reb = last_10_games['rebounds'].mean() if not last_10_games.empty else 0
                    
                    # Get player info
                    player_name = player_games.iloc[0].get('player_name', 'Unknown')
                    
                    # Get position from roster or API
                    position = 'N/A'
                    if not team_roster.empty:
                        player_roster = team_roster[team_roster['player_id'] == player_id]
                        if not player_roster.empty:
                            position = player_roster.iloc[0].get('position', 'N/A')
                    
                    # If position not found, try to get from API
                    if position == 'N/A' or position == '':
                        try:
                            player_info = self.nba_collector.get_player_info(player_id)
                            if player_info:
                                pos = player_info.get('POSITION', '')
                                if pos:
                                    # Keep original position format (PF, SF, C, PG, SG, etc.)
                                    position = pos
                        except Exception as e:
                            logger.debug(f"Could not get position for player {player_id}: {e}")
                    
                    # Get opponent for today
                    team_game = today_games[today_games['TEAM_ABBREVIATION'] == team_abbr]
                    opponent = 'TBD'
                    if not team_game.empty:
                        matchup = team_game.iloc[0].get('MATCHUP', '')
                        import re
                        teams_in_matchup = re.findall(r'([A-Z]{3})', matchup)
                        if len(teams_in_matchup) >= 2:
                            opponent = teams_in_matchup[1] if teams_in_matchup[0] == team_abbr else teams_in_matchup[0]
                    
                    players_data.append({
                        'player_id': player_id,
                        'name': player_name,
                        'team_abbr': team_abbr,
                        'team_id': team_id,
                        'opponent': opponent,
                        'position': position,
                        'avg_minutes': avg_minutes,
                        'last_10_avg_reb': last_10_avg_reb
                    })
                    
            except Exception as e:
                logger.warning(f"Error processing team {team_abbr}: {e}")
                continue
        
        return players_data
    
    def _generate_prediction(self, player: Dict) -> Dict:
        """Generate prediction for a player"""
        try:
            # Get opponent team ID
            all_teams = teams.get_teams()
            team_map = {t['abbreviation']: t['id'] for t in all_teams}
            opponent_team_id = team_map.get(player['opponent'], None)
            
            if not opponent_team_id:
                return None
            
            # Generate prediction
            pred, lower, upper = self.predictor.predict_for_game(
                player['player_id'],
                player['team_id'],
                opponent_team_id,
                self.today,
                self.db_manager
            )
            
            # Calculate confidence level
            confidence_range = upper - lower
            if confidence_range <= 2.0:
                confidence_level = 'High'
            elif confidence_range <= 4.0:
                confidence_level = 'Medium'
            else:
                confidence_level = 'Low'
            
            return {
                **player,
                'predicted_rebounds': pred,
                'confidence_lower': lower,
                'confidence_upper': upper,
                'confidence_range': confidence_range,
                'confidence_level': confidence_level
            }
        except Exception as e:
            logger.warning(f"Error generating prediction for {player.get('name', 'Unknown')}: {e}")
            return None
    
    def _sort_predictions(self, predictions: List[Dict]) -> List[Dict]:
        """Sort predictions: F and C first, then by confidence level"""
        # Separate by position - check if position contains F or C
        def is_forward_or_center(pos):
            if not pos or pos == 'N/A':
                return False
            pos_upper = str(pos).upper()
            # Check for Forward or Center positions
            return any(x in pos_upper for x in ['F', 'C']) and 'G' not in pos_upper
        
        forwards_centers = [p for p in predictions if is_forward_or_center(p.get('position', ''))]
        others = [p for p in predictions if p not in forwards_centers]
        
        # Sort each group by confidence level (High -> Medium -> Low)
        # Then by confidence range (smaller = better)
        def sort_key(p):
            conf_order = {'High': 0, 'Medium': 1, 'Low': 2}
            return (conf_order.get(p.get('confidence_level', 'Low'), 2), p.get('confidence_range', 999))
        
        forwards_centers.sort(key=sort_key)
        others.sort(key=sort_key)
        
        return forwards_centers + others
    
    def _update_gui(self, high_conf: List[Dict], medium_conf: List[Dict], low_conf: List[Dict]):
        """Update GUI with predictions"""
        # Clear existing data
        for tree_name in ['high_tree', 'medium_tree', 'low_tree']:
            tree = getattr(self, tree_name)
            for item in tree.get_children():
                tree.delete(item)
        
        # Populate trees
        self._populate_tree(self.high_tree, high_conf)
        self._populate_tree(self.medium_tree, medium_conf)
        self._populate_tree(self.low_tree, low_conf)
        
        # Update status
        total = len(high_conf) + len(medium_conf) + len(low_conf)
        self.status_label.config(
            text=f"Loaded {total} players: {len(high_conf)} High, {len(medium_conf)} Medium, {len(low_conf)} Low confidence",
            foreground="green"
        )
    
    def _populate_tree(self, tree: ttk.Treeview, predictions: List[Dict]):
        """Populate treeview with predictions"""
        for pred in predictions:
            tree.insert("", "end", values=(
                pred.get('name', 'Unknown'),
                pred.get('position', 'N/A'),
                pred.get('opponent', 'TBD'),
                f"{pred.get('predicted_rebounds', 0):.1f}",
                pred.get('confidence_level', 'Low')
            ))

