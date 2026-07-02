"""Database utilities for NBA Rebound Prediction Model"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from config.config import DATABASE_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database and tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")
    
    def _create_tables(self):
        """Create all necessary tables"""
        cursor = self.conn.cursor()
        
        # Player stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                game_date TEXT NOT NULL,
                team_id INTEGER,
                team_abbreviation TEXT,
                opponent_team_id INTEGER,
                opponent_team_abbreviation TEXT,
                minutes_played REAL,
                rebounds INTEGER,
                offensive_rebounds INTEGER,
                defensive_rebounds INTEGER,
                points INTEGER,
                assists INTEGER,
                field_goals_attempted INTEGER,
                field_goals_made INTEGER,
                is_home INTEGER,
                season TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, game_date)
            )
        """)
        
        # Team stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                team_abbreviation TEXT NOT NULL,
                game_date TEXT NOT NULL,
                opponent_team_id INTEGER,
                opponent_team_abbreviation TEXT,
                pace REAL,
                field_goals_attempted INTEGER,
                field_goals_made INTEGER,
                field_goal_percentage REAL,
                three_pointers_attempted INTEGER,
                three_pointers_made INTEGER,
                total_rebounds INTEGER,
                offensive_rebounds INTEGER,
                defensive_rebounds INTEGER,
                points INTEGER,
                possessions REAL,
                is_home INTEGER,
                season TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, game_date)
            )
        """)
        
        # Game logs table (aggregated game information)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL UNIQUE,
                game_date TEXT NOT NULL,
                home_team_id INTEGER,
                home_team_abbreviation TEXT,
                away_team_id INTEGER,
                away_team_abbreviation TEXT,
                home_team_score INTEGER,
                away_team_score INTEGER,
                season TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Player roster information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_roster (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL UNIQUE,
                player_name TEXT NOT NULL,
                height_feet INTEGER,
                height_inches INTEGER,
                height_total_inches REAL,
                weight_pounds REAL,
                position TEXT,
                team_id INTEGER,
                season TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Betting lines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS betting_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                player_name TEXT,
                game_date TEXT NOT NULL,
                sportsbook TEXT,
                market_type TEXT,
                line_value REAL,
                over_odds INTEGER,
                under_odds INTEGER,
                over_implied_prob REAL,
                under_implied_prob REAL,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, game_date, sportsbook, market_type)
            )
        """)
        
        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                game_date TEXT NOT NULL,
                predicted_rebounds REAL,
                confidence_interval_lower REAL,
                confidence_interval_upper REAL,
                model_version TEXT,
                features_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, game_date)
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_date ON player_stats(game_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_stats(player_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_stats_date ON team_stats(game_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_stats_team ON team_stats(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_logs_date ON game_logs(game_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_betting_lines_date ON betting_lines(game_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(game_date)")
        
        self.conn.commit()
        logger.info("Database tables created successfully")
    
    def insert_player_stats(self, df: pd.DataFrame):
        """Insert player stats into database"""
        # Get expected columns from database schema
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(player_stats)")
        schema_columns = [row[1] for row in cursor.fetchall()]
        
        # Filter DataFrame to only include columns that exist in schema
        available_columns = [col for col in df.columns if col in schema_columns]
        if not available_columns:
            logger.warning("No matching columns found for player_stats table")
            return
        
        df_filtered = df[available_columns].copy()
        df_filtered.to_sql('player_stats', self.conn, if_exists='append', index=False)
        self.conn.commit()
        logger.info(f"Inserted {len(df_filtered)} player stats records")
    
    def insert_team_stats(self, df: pd.DataFrame):
        """Insert team stats into database"""
        # Get expected columns from database schema
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(team_stats)")
        schema_columns = [row[1] for row in cursor.fetchall()]
        
        # Filter DataFrame to only include columns that exist in schema
        available_columns = [col for col in df.columns if col in schema_columns]
        if not available_columns:
            logger.warning("No matching columns found for team_stats table")
            return
        
        df_filtered = df[available_columns].copy()
        df_filtered.to_sql('team_stats', self.conn, if_exists='append', index=False)
        self.conn.commit()
        logger.info(f"Inserted {len(df_filtered)} team stats records")
    
    def insert_game_logs(self, df: pd.DataFrame):
        """Insert game logs into database"""
        df.to_sql('game_logs', self.conn, if_exists='append', index=False)
        self.conn.commit()
        logger.info(f"Inserted {len(df)} game log records")
    
    def insert_player_roster(self, df: pd.DataFrame):
        """Insert or update player roster information"""
        df.to_sql('player_roster', self.conn, if_exists='replace', index=False)
        self.conn.commit()
        logger.info(f"Updated player roster with {len(df)} players")
    
    def insert_betting_lines(self, df: pd.DataFrame):
        """Insert betting lines into database"""
        df.to_sql('betting_lines', self.conn, if_exists='append', index=False)
        self.conn.commit()
        logger.info(f"Inserted {len(df)} betting line records")
    
    def insert_predictions(self, df: pd.DataFrame):
        """Insert predictions into database"""
        df.to_sql('predictions', self.conn, if_exists='replace', index=False)
        self.conn.commit()
        logger.info(f"Inserted {len(df)} prediction records")
    
    def get_player_stats(self, player_id: Optional[int] = None, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limit: Optional[int] = None) -> pd.DataFrame:
        """Query player stats from database"""
        query = "SELECT * FROM player_stats WHERE 1=1"
        params = []
        
        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)
        if start_date:
            query += " AND game_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND game_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY game_date DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_team_stats(self, team_id: Optional[int] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """Query team stats from database"""
        query = "SELECT * FROM team_stats WHERE 1=1"
        params = []
        
        if team_id:
            query += " AND team_id = ?"
            params.append(team_id)
        if start_date:
            query += " AND game_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND game_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY game_date DESC"
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_player_roster(self, player_id: Optional[int] = None) -> pd.DataFrame:
        """Query player roster information"""
        query = "SELECT * FROM player_roster WHERE 1=1"
        params = []
        
        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_betting_lines(self, player_id: Optional[int] = None,
                         game_date: Optional[str] = None) -> pd.DataFrame:
        """Query betting lines from database"""
        query = "SELECT * FROM betting_lines WHERE 1=1"
        params = []
        
        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)
        if game_date:
            query += " AND game_date = ?"
            params.append(game_date)
        
        query += " ORDER BY game_date DESC, timestamp DESC"
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_predictions(self, player_id: Optional[int] = None,
                       game_date: Optional[str] = None) -> pd.DataFrame:
        """Query predictions from database"""
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []
        
        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)
        if game_date:
            query += " AND game_date = ?"
            params.append(game_date)
        
        query += " ORDER BY game_date DESC"
        return pd.read_sql_query(query, self.conn, params=params)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

