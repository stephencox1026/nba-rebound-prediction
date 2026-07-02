"""Prediction engine for rebound predictions"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging

from utils.helpers import setup_logging
from model.model_manager import ModelManager
from features.feature_aggregator import FeatureAggregator
from utils.database import DatabaseManager

logger = setup_logging(__name__)


class ReboundPredictor:
    """Makes rebound predictions using trained model"""
    
    def __init__(self, model_name: str = 'rebound_predictor'):
        self.model_manager = ModelManager()
        self.feature_aggregator = FeatureAggregator()
        self.model = None
        self.model_name = model_name
        self.feature_names = None
        self._load_model()
    
    def _load_model(self):
        """Load the latest trained model"""
        try:
            self.model = self.model_manager.load_latest_model(self.model_name)
            # Try to get feature names if available
            metadata = self.model_manager.load_model_metadata(self.model_name)
            if metadata and 'feature_names' in metadata:
                self.feature_names = metadata['feature_names']
            logger.info("Model loaded successfully")
        except FileNotFoundError:
            logger.warning("No trained model found. Train a model first.")
            self.model = None
    
    def predict(self, features: Dict[str, float]) -> Tuple[float, float, float]:
        """Make prediction for a single game
        
        Returns:
            Tuple of (prediction, lower_bound, upper_bound)
        """
        if self.model is None:
            raise ValueError("No model loaded. Train a model first.")
        
        # Convert features to DataFrame
        features_df = pd.DataFrame([features])
        
        # Ensure all required features are present
        if self.feature_names:
            # Add missing features with 0
            for feat in self.feature_names:
                if feat not in features_df.columns:
                    features_df[feat] = 0.0
            # Select only required features in correct order
            features_df = features_df[self.feature_names]
        else:
            # Remove non-numeric columns
            features_df = features_df.select_dtypes(include=[np.number])
        
        # Make prediction
        prediction = self.model.predict(features_df)[0]
        
        # Calculate confidence interval (simplified - using prediction std)
        # In production, would use proper prediction intervals
        std_estimate = 1.5  # Estimated standard deviation
        lower_bound = max(0, prediction - 1.96 * std_estimate)
        upper_bound = prediction + 1.96 * std_estimate
        
        return prediction, lower_bound, upper_bound
    
    def predict_for_game(self, player_id: int, team_id: int,
                        opponent_team_id: int, game_date: str,
                        db_manager: DatabaseManager) -> Tuple[float, float, float]:
        """Make prediction for a specific game using database"""
        # Get features
        features = self.feature_aggregator.prepare_prediction_features(
            player_id, team_id, opponent_team_id, game_date, db_manager
        )
        
        # Make prediction
        return self.predict(features)
    
    def predict_batch(self, games: List[Dict], db_manager: DatabaseManager) -> pd.DataFrame:
        """Make predictions for multiple games"""
        predictions = []
        
        for game in games:
            try:
                player_id = game['player_id']
                team_id = game['team_id']
                opponent_team_id = game['opponent_team_id']
                game_date = game['game_date']
                player_name = game.get('player_name', 'Unknown')
                
                pred, lower, upper = self.predict_for_game(
                    player_id, team_id, opponent_team_id, game_date, db_manager
                )
                
                predictions.append({
                    'player_id': player_id,
                    'player_name': player_name,
                    'game_date': game_date,
                    'predicted_rebounds': pred,
                    'confidence_interval_lower': lower,
                    'confidence_interval_upper': upper
                })
            except Exception as e:
                logger.error(f"Error predicting for game {game}: {e}")
                continue
        
        return pd.DataFrame(predictions)
    
    def update_predictions_in_db(self, games: List[Dict], db_manager: DatabaseManager):
        """Update predictions in database"""
        predictions_df = self.predict_batch(games, db_manager)
        
        if not predictions_df.empty:
            # Add model version
            metadata = self.model_manager.load_model_metadata(self.model_name)
            model_version = metadata.get('training_date', 'unknown') if metadata else 'unknown'
            predictions_df['model_version'] = model_version
            
            # Store in database
            db_manager.insert_predictions(predictions_df)
            logger.info(f"Updated {len(predictions_df)} predictions in database")


