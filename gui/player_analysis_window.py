"""Player analysis window with game-by-game rebound visualization"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import logging

from utils.helpers import setup_logging, format_date
from utils.database import DatabaseManager
from model.predictor import ReboundPredictor
from data_collectors.nba_data_collector import NBADataCollector
from nba_api.stats.static import teams

logger = setup_logging(__name__)


class PlayerAnalysisWindow:
    """Window for analyzing player rebound predictions"""
    
    def __init__(self, parent=None):
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("NBA Player Rebound Analysis - Season View")
        self.root.geometry("1400x900")
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.predictor = None
        self.nba_collector = NBADataCollector()
        
        # Data storage
        self.selected_players = []
        self.player_data = {}
        self.today_games = pd.DataFrame()
        
        # Try to load model
        try:
            self.predictor = ReboundPredictor()
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            messagebox.showwarning("Model Not Found", "No trained model found. Predictions will not be available.")
        
        self._create_widgets()
        self._setup_layout()
        
        # Load today's games
        self.root.after(100, self.load_todays_games)
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        # Top frame for team/player selection
        self.selection_frame = ttk.Frame(self.root, padding="10")
        
        # Team selection
        ttk.Label(self.selection_frame, text="Select Team:").grid(row=0, column=0, padx=5)
        self.team_var = tk.StringVar(value="Los Angeles Lakers")
        self.team_combo = ttk.Combobox(
            self.selection_frame,
            textvariable=self.team_var,
            width=25,
            state="readonly"
        )
        self.team_combo.grid(row=0, column=1, padx=5)
        self.team_combo.bind("<<ComboboxSelected>>", self.on_team_selected)
        
        # Load teams
        self.load_teams()
        
        # Player selection frame
        ttk.Label(self.selection_frame, text="Select Players (up to 5):").grid(row=1, column=0, padx=5, pady=10, sticky="w")
        
        self.player_list_frame = ttk.Frame(self.selection_frame)
        self.player_list_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # Player checkboxes will be created dynamically
        self.player_vars = {}
        self.player_checkboxes = {}
        
        # Buttons
        self.load_btn = ttk.Button(
            self.selection_frame,
            text="Load Today's Players",
            command=self.load_todays_games
        )
        self.load_btn.grid(row=0, column=2, padx=5)
        
        self.analyze_btn = ttk.Button(
            self.selection_frame,
            text="Analyze Selected Players",
            command=self.analyze_players,
            state="disabled"
        )
        self.analyze_btn.grid(row=1, column=2, padx=5)
        
        # Status label
        self.status_label = ttk.Label(
            self.selection_frame,
            text="Ready",
            foreground="green"
        )
        self.status_label.grid(row=3, column=0, columnspan=3, pady=5)
        
        # Chart frame
        self.chart_frame = ttk.Frame(self.root, padding="10")
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(14, 8), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Table frame for game-by-game data
        self.table_frame = ttk.Frame(self.root, padding="10")
        
        # Create treeview for game data
        columns = ("Player", "Game Date", "Opponent", "Actual Rebounds", "Predicted Rebounds", "Difference")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _setup_layout(self):
        """Setup widget layout"""
        self.selection_frame.pack(fill="x")
        self.chart_frame.pack(fill="both", expand=True)
        self.table_frame.pack(fill="both", expand=True)
    
    def load_teams(self):
        """Load NBA teams into combo box"""
        try:
            all_teams = teams.get_teams()
            team_names = [team['full_name'] for team in all_teams]
            self.team_combo['values'] = sorted(team_names)
        except Exception as e:
            logger.error(f"Error loading teams: {e}")
    
    def on_team_selected(self, event=None):
        """Handle team selection"""
        self.selected_players = []
        self.player_vars = {}
        self.player_checkboxes = {}
        
        # Clear existing checkboxes
        for widget in self.player_list_frame.winfo_children():
            widget.destroy()
        
        # Load players for selected team
        self.load_team_players()
    
    def load_team_players(self):
        """Load players for selected team"""
        try:
            team_name = self.team_var.get()
            all_teams = teams.get_teams()
            team_info = next((t for t in all_teams if t['full_name'] == team_name), None)
            
            if not team_info:
                return
            
            team_id = team_info['id']
            
            # Get today's games to find players
            self.status_label.config(text="Loading players...", foreground="orange")
            self.root.update()
            
            # Get roster for the team
            from nba_api.stats.endpoints import commonteamroster
            roster = commonteamroster.CommonTeamRoster(team_id=team_id, season='2024-25')
            roster_df = roster.get_data_frames()[0]
            
            if roster_df.empty:
                # Try current season
                roster = commonteamroster.CommonTeamRoster(team_id=team_id, season='2023-24')
                roster_df = roster.get_data_frames()[0]
            
            if not roster_df.empty:
                # Create checkboxes for each player
                row = 0
                col = 0
                for idx, player in roster_df.iterrows():
                    player_name = player.get('PLAYER', 'Unknown')
                    player_id = player.get('PLAYER_ID', None)
                    
                    if player_id:
                        var = tk.BooleanVar()
                        self.player_vars[player_id] = {'var': var, 'name': player_name}
                        
                        checkbox = ttk.Checkbutton(
                            self.player_list_frame,
                            text=player_name,
                            variable=var,
                            command=self.update_selection_count
                        )
                        checkbox.grid(row=row, column=col, padx=5, pady=2, sticky="w")
                        self.player_checkboxes[player_id] = checkbox
                        
                        col += 1
                        if col >= 5:  # 5 columns
                            col = 0
                            row += 1
                
                self.status_label.config(text=f"Loaded {len(roster_df)} players", foreground="green")
            else:
                self.status_label.config(text="No players found", foreground="red")
                
        except Exception as e:
            logger.error(f"Error loading team players: {e}")
            self.status_label.config(text=f"Error: {e}", foreground="red")
    
    def update_selection_count(self):
        """Update selection count and enable/disable analyze button"""
        selected_count = sum(1 for v in self.player_vars.values() if v['var'].get())
        
        if selected_count > 5:
            # Uncheck the last one
            for player_id, data in reversed(list(self.player_vars.items())):
                if data['var'].get():
                    data['var'].set(False)
                    selected_count = 4
                    break
        
        if selected_count > 0 and selected_count <= 5:
            self.analyze_btn.config(state="normal")
        else:
            self.analyze_btn.config(state="disabled")
    
    def load_todays_games(self):
        """Load today's NBA games"""
        try:
            self.status_label.config(text="Loading today's games...", foreground="orange")
            self.root.update()
            
            self.today_games = self.nba_collector.get_today_games()
            
            if not self.today_games.empty:
                self.status_label.config(
                    text=f"Found {len(self.today_games)} games today",
                    foreground="green"
                )
            else:
                self.status_label.config(
                    text="No games scheduled for today (or unable to fetch)",
                    foreground="orange"
                )
            
            # Auto-select Lakers if available
            if "Los Angeles Lakers" in self.team_combo['values']:
                self.team_var.set("Los Angeles Lakers")
                self.on_team_selected()
            else:
                # Just load Lakers players anyway
                self.team_var.set("Los Angeles Lakers")
                self.on_team_selected()
                
        except Exception as e:
            logger.error(f"Error loading today's games: {e}")
            # Still try to load Lakers
            try:
                self.team_var.set("Los Angeles Lakers")
                self.on_team_selected()
            except:
                pass
            self.status_label.config(text="Ready - Select team to load players", foreground="green")
    
    def analyze_players(self):
        """Analyze selected players"""
        # Get selected players
        selected = [
            (player_id, data['name'])
            for player_id, data in self.player_vars.items()
            if data['var'].get()
        ]
        
        if len(selected) == 0:
            messagebox.showwarning("No Selection", "Please select at least one player.")
            return
        
        if len(selected) > 5:
            messagebox.showwarning("Too Many", "Please select no more than 5 players.")
            return
        
        self.selected_players = selected
        self.status_label.config(text="Analyzing players...", foreground="orange")
        self.root.update()
        
        # Run analysis in background thread
        thread = threading.Thread(target=self._analyze_players_thread, daemon=True)
        thread.start()
    
    def _analyze_players_thread(self):
        """Analyze players in background thread"""
        try:
            all_game_data = []
            
            for player_id, player_name in self.selected_players:
                # Get player stats for current season
                player_stats = self.db_manager.get_player_stats(player_id=player_id)
                
                if player_stats.empty:
                    logger.warning(f"No stats found for {player_name}")
                    continue
                
                # Get current season
                current_season = "2024-25"
                season_stats = player_stats[player_stats['season'] == current_season]
                
                if season_stats.empty:
                    # Try previous season
                    season_stats = player_stats[player_stats['season'] == "2023-24"]
                
                if season_stats.empty:
                    season_stats = player_stats.sort_values('game_date').tail(82)  # Last season's worth
                
                season_stats = season_stats.sort_values('game_date')
                
                # Generate predictions for each game
                game_data = []
                for idx, game in season_stats.iterrows():
                    game_date = game['game_date']
                    actual_rebounds = game.get('rebounds', 0)
                    opponent_abbr = game.get('opponent_team_abbreviation', 'Unknown')
                    
                    # Get prediction
                    predicted_rebounds = 0.0
                    if self.predictor:
                        try:
                            team_id = game.get('team_id', 0)
                            opponent_team_id = game.get('opponent_team_id', 0)
                            
                            pred, lower, upper = self.predictor.predict_for_game(
                                player_id, team_id, opponent_team_id, game_date, self.db_manager
                            )
                            predicted_rebounds = pred
                        except Exception as e:
                            logger.warning(f"Error predicting for {player_name}, game {game_date}: {e}")
                            # Use season average as fallback
                            predicted_rebounds = season_stats['rebounds'].mean()
                    else:
                        # No model - use season average
                        predicted_rebounds = season_stats['rebounds'].mean()
                    
                    game_data.append({
                        'player_name': player_name,
                        'player_id': player_id,
                        'game_date': game_date,
                        'opponent': opponent_abbr,
                        'actual_rebounds': actual_rebounds,
                        'predicted_rebounds': predicted_rebounds,
                        'difference': predicted_rebounds - actual_rebounds
                    })
                
                all_game_data.extend(game_data)
                self.player_data[player_id] = {
                    'name': player_name,
                    'games': game_data
                }
            
            # Update UI in main thread
            self.root.after(0, lambda: self._update_display(all_game_data))
            
        except Exception as e:
            logger.error(f"Error in analysis thread: {e}", exc_info=True)
            self.root.after(0, lambda: self.status_label.config(
                text=f"Error: {e}",
                foreground="red"
            ))
    
    def _update_display(self, all_game_data):
        """Update chart and table display"""
        try:
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Clear chart
            self.ax.clear()
            
            if not all_game_data:
                self.status_label.config(text="No data to display", foreground="orange")
                return
            
            # Create DataFrame
            df = pd.DataFrame(all_game_data)
            
            # Populate table
            for _, row in df.iterrows():
                self.tree.insert("", "end", values=(
                    row['player_name'],
                    row['game_date'],
                    row['opponent'],
                    f"{row['actual_rebounds']:.1f}",
                    f"{row['predicted_rebounds']:.1f}",
                    f"{row['difference']:+.1f}"
                ))
            
            # Create chart
            self.ax.clear()
            
            # Plot for each player
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            
            for idx, (player_id, player_info) in enumerate(self.player_data.items()):
                games = player_info['games']
                if not games:
                    continue
                
                game_dates = [g['game_date'] for g in games]
                actual = [g['actual_rebounds'] for g in games]
                predicted = [g['predicted_rebounds'] for g in games]
                
                # Convert dates for plotting
                dates = pd.to_datetime(game_dates)
                
                color = colors[idx % len(colors)]
                player_name = player_info['name']
                
                # Plot actual rebounds
                self.ax.plot(dates, actual, 'o-', color=color, label=f"{player_name} (Actual)", 
                           linewidth=2, markersize=4, alpha=0.7)
                
                # Plot predicted rebounds
                self.ax.plot(dates, predicted, 's--', color=color, label=f"{player_name} (Predicted)",
                           linewidth=2, markersize=3, alpha=0.5)
            
            self.ax.set_xlabel('Game Date', fontsize=12)
            self.ax.set_ylabel('Rebounds', fontsize=12)
            self.ax.set_title('Actual vs Predicted Rebounds - Season View', fontsize=14, fontweight='bold')
            self.ax.legend(loc='best', fontsize=9)
            self.ax.grid(True, alpha=0.3)
            self.ax.tick_params(axis='x', rotation=45)
            
            self.fig.tight_layout()
            self.canvas.draw()
            
            self.status_label.config(
                text=f"Analysis complete: {len(df)} games displayed",
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
    app = PlayerAnalysisWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

