"""Main GUI window for NBA Rebound Prediction Model"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import pandas as pd
import threading
import logging

from utils.helpers import setup_logging, format_date
from utils.database import DatabaseManager
from model.predictor import ReboundPredictor
from analysis.value_calculator import ValueCalculator
from data_collectors.betting_odds_collector import BettingOddsCollector
from data_collectors.nba_data_collector import NBADataCollector
from gui.update_manager import UpdateManager
from gui.player_analysis_window import PlayerAnalysisWindow
from gui.daily_predictions_window import DailyPredictionsWindow
from config.config import HIGH_VALUE_THRESHOLD, MEDIUM_VALUE_THRESHOLD

logger = setup_logging(__name__)


class MainWindow:
    """Main application window"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NBA Rebound Prediction Model - Value Bet Finder")
        self.root.geometry("1400x800")
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.predictor = None
        self.value_calculator = ValueCalculator()
        self.betting_collector = BettingOddsCollector()
        self.nba_collector = NBADataCollector()
        self.update_manager = UpdateManager(update_callback=self.update_data)
        
        # Data storage
        self.value_bets_df = pd.DataFrame()
        self.current_date = datetime.now().date()
        
        # Try to load model
        try:
            self.predictor = ReboundPredictor()
            logger.info("Model loaded successfully")
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Could not load model: {e}")
            # Don't show warning immediately - allow user to proceed
            # They can train model later
            self.predictor = None
        
        self._create_widgets()
        self._setup_layout()
        
        # Load initial data
        self.root.after(100, self.refresh_data)
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        # Top frame for controls
        self.control_frame = ttk.Frame(self.root, padding="10")
        
        # Date selection
        ttk.Label(self.control_frame, text="Game Date:").grid(row=0, column=0, padx=5)
        self.date_var = tk.StringVar(value=format_date(datetime.now()))
        self.date_entry = ttk.Entry(self.control_frame, textvariable=self.date_var, width=12)
        self.date_entry.grid(row=0, column=1, padx=5)
        
        # Refresh button
        self.refresh_btn = ttk.Button(
            self.control_frame,
            text="Refresh Data",
            command=self.refresh_data
        )
        self.refresh_btn.grid(row=0, column=2, padx=5)
        
        # Auto-update toggle
        self.auto_update_var = tk.BooleanVar(value=False)
        self.auto_update_btn = ttk.Checkbutton(
            self.control_frame,
            text="Auto-Update",
            variable=self.auto_update_var,
            command=self.toggle_auto_update
        )
        self.auto_update_btn.grid(row=0, column=3, padx=5)
        
        # Player Analysis button
        self.analysis_btn = ttk.Button(
            self.control_frame,
            text="Player Analysis",
            command=self.open_player_analysis
        )
        self.analysis_btn.grid(row=0, column=4, padx=5)
        
        # Daily Predictions button
        self.daily_btn = ttk.Button(
            self.control_frame,
            text="Daily Predictions (Top 4)",
            command=self.open_daily_predictions
        )
        self.daily_btn.grid(row=0, column=5, padx=5)
        
        # Today's Predictions button
        self.today_btn = ttk.Button(
            self.control_frame,
            text="Today's Predictions (All Players)",
            command=self.open_today_predictions
        )
        self.today_btn.grid(row=0, column=6, padx=5)
        
        # Status label
        self.status_label = ttk.Label(
            self.control_frame,
            text="Ready",
            foreground="green"
        )
        self.status_label.grid(row=0, column=4, padx=10)
        
        # Filter frame
        self.filter_frame = ttk.Frame(self.root, padding="10")
        
        ttk.Label(self.filter_frame, text="Filter by:").grid(row=0, column=0, padx=5)
        
        # Value category filter
        ttk.Label(self.filter_frame, text="Value:").grid(row=0, column=1, padx=5)
        self.value_filter_var = tk.StringVar(value="All")
        value_filter = ttk.Combobox(
            self.filter_frame,
            textvariable=self.value_filter_var,
            values=["All", "High", "Medium", "Low"],
            state="readonly",
            width=10
        )
        value_filter.grid(row=0, column=2, padx=5)
        value_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Sort by
        ttk.Label(self.filter_frame, text="Sort by:").grid(row=0, column=3, padx=5)
        self.sort_var = tk.StringVar(value="Expected Value")
        sort_combo = ttk.Combobox(
            self.filter_frame,
            textvariable=self.sort_var,
            values=["Expected Value", "Edge", "Confidence", "Player Name"],
            state="readonly",
            width=15
        )
        sort_combo.grid(row=0, column=4, padx=5)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Main table frame
        self.table_frame = ttk.Frame(self.root, padding="10")
        
        # Create treeview for table
        columns = (
            "Player", "Game Date", "Prediction", "Line", "Bet Type",
            "Edge", "Expected Value", "Win Prob", "Odds", "Sportsbook", "Value"
        )
        
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=25)
        
        # Configure columns
        column_widths = {
            "Player": 150,
            "Game Date": 100,
            "Prediction": 80,
            "Line": 60,
            "Bet Type": 70,
            "Edge": 80,
            "Expected Value": 100,
            "Win Prob": 80,
            "Odds": 60,
            "Sportsbook": 100,
            "Value": 80
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100), anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack table and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        
        # Configure row colors
        self.tree.tag_configure("high_value", background="#90EE90")  # Light green
        self.tree.tag_configure("medium_value", background="#FFE4B5")  # Moccasin
        self.tree.tag_configure("low_value", background="#FFB6C1")  # Light pink
    
    def _setup_layout(self):
        """Setup widget layout"""
        self.control_frame.pack(fill="x")
        self.filter_frame.pack(fill="x")
        self.table_frame.pack(fill="both", expand=True)
    
    def refresh_data(self):
        """Refresh data and update display"""
        self.status_label.config(text="Updating...", foreground="orange")
        self.root.update()
        
        try:
            # Run update in background thread
            thread = threading.Thread(target=self._update_data_thread, daemon=True)
            thread.start()
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            self.status_label.config(text="Error", foreground="red")
            messagebox.showerror("Error", f"Failed to refresh data: {e}")
    
    def _update_data_thread(self):
        """Update data in background thread"""
        try:
            # Get predictions and betting lines
            game_date = self.date_var.get()
            
            # Get predictions from database
            predictions_df = self.db_manager.get_predictions(game_date=game_date)
            
            # If no predictions and model is available, generate predictions
            if predictions_df.empty and self.predictor is not None:
                # This would require getting upcoming games - simplified for now
                logger.info("No predictions in database. Train model and generate predictions first.")
            
            # Get betting lines
            betting_lines_df = self.betting_collector.get_player_props()
            
            if not predictions_df.empty and not betting_lines_df.empty:
                # Find value bets
                self.value_bets_df = self.value_calculator.find_value_bets(
                    predictions_df, betting_lines_df
                )
                
                # Rank value bets
                if not self.value_bets_df.empty:
                    self.value_bets_df = self.value_calculator.rank_value_bets(self.value_bets_df)
            else:
                self.value_bets_df = pd.DataFrame()
                if predictions_df.empty:
                    logger.info("No predictions available")
                if betting_lines_df.empty:
                    logger.info("No betting lines available")
            
            # Update UI in main thread
            self.root.after(0, self._update_display)
            self.root.after(0, lambda: self.status_label.config(
                text=f"Updated: {datetime.now().strftime('%H:%M:%S')}",
                foreground="green"
            ))
        except Exception as e:
            logger.error(f"Error in update thread: {e}", exc_info=True)
            self.root.after(0, lambda: self.status_label.config(
                text="Update Failed",
                foreground="red"
            ))
    
    def _update_display(self):
        """Update the table display"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if self.value_bets_df.empty:
            return
        
        # Apply filters
        filtered_df = self._apply_filters_to_df(self.value_bets_df)
        
        # Populate table
        for _, row in filtered_df.iterrows():
            value_category = row.get('value_category', 'low')
            tag = f"{value_category}_value"
            
            values = (
                row.get('player_name', 'Unknown'),
                row.get('game_date', ''),
                f"{row.get('predicted_rebounds', 0):.1f}",
                f"{row.get('line_value', 0):.1f}",
                row.get('bet_type', ''),
                f"{row.get('edge', 0):.1%}",
                f"${row.get('expected_value', 0):.2f}",
                f"{row.get('win_probability', 0):.1%}",
                f"{row.get('odds', 0):+d}",
                row.get('sportsbook', 'Unknown'),
                value_category.title()
            )
            
            self.tree.insert("", "end", values=values, tags=(tag,))
    
    def _apply_filters_to_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply filters to dataframe"""
        filtered = df.copy()
        
        # Value category filter
        value_filter = self.value_filter_var.get()
        if value_filter != "All":
            filtered = filtered[filtered['value_category'] == value_filter.lower()]
        
        # Sort
        sort_by = self.sort_var.get()
        if sort_by == "Expected Value":
            filtered = filtered.sort_values('expected_value', ascending=False)
        elif sort_by == "Edge":
            filtered = filtered.sort_values('edge', ascending=False)
        elif sort_by == "Confidence":
            filtered = filtered.sort_values('confidence_level', ascending=False)
        elif sort_by == "Player Name":
            filtered = filtered.sort_values('player_name')
        
        return filtered
    
    def apply_filters(self):
        """Apply filters and refresh display"""
        self._update_display()
    
    def update_data(self):
        """Callback for automatic updates"""
        self.refresh_data()
    
    def toggle_auto_update(self):
        """Toggle automatic updates"""
        if self.auto_update_var.get():
            self.update_manager.start()
        else:
            self.update_manager.stop()
    
    def open_player_analysis(self):
        """Open player analysis window"""
        try:
            analysis_window = PlayerAnalysisWindow(self.root)
        except Exception as e:
            logger.error(f"Error opening player analysis window: {e}")
            messagebox.showerror("Error", f"Failed to open player analysis: {e}")
    
    def open_daily_predictions(self):
        """Open daily predictions window"""
        if self.predictor is None:
            messagebox.showwarning("Model Not Loaded", "Please train a model first before getting daily predictions.")
            return
        try:
            DailyPredictionsWindow(self.root, self.db_manager, self.nba_collector, self.predictor)
        except Exception as e:
            logger.error(f"Error opening daily predictions window: {e}")
    
    def open_today_predictions(self):
        """Open today's predictions window for all players"""
        if self.predictor is None:
            messagebox.showwarning("Model Not Loaded", "Please train a model first before getting predictions.")
            return
        try:
            from gui.today_predictions_window import TodayPredictionsWindow
            TodayPredictionsWindow(self.root, self.db_manager, self.nba_collector, self.predictor)
        except Exception as e:
            logger.error(f"Error opening today's predictions window: {e}")
            messagebox.showerror("Error", f"Could not open today's predictions window: {e}")
            messagebox.showerror("Error", f"Failed to open daily predictions: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        self.update_manager.stop()
        self.db_manager.close()
        self.root.destroy()


def main():
    """Main entry point for GUI"""
    root = tk.Tk()
    app = MainWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

