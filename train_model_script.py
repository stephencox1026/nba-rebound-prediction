"""Script to train the rebound prediction model"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.helpers import setup_logging
from utils.database import DatabaseManager
from features.feature_aggregator import FeatureAggregator
from model.train_model import ModelTrainer

logger = setup_logging(__name__)


def train_model():
    """Train the rebound prediction model"""
    logger.info("Starting model training")
    
    db_manager = DatabaseManager()
    
    try:
        # Get all data from database
        logger.info("Loading data from database...")
        player_stats = db_manager.get_player_stats()
        team_stats = db_manager.get_team_stats()
        player_roster = db_manager.get_player_roster()
        
        if player_stats.empty:
            logger.error("No player stats found in database. Please collect data first.")
            return
        
        logger.info(f"Loaded {len(player_stats)} player stat records")
        logger.info(f"Loaded {len(team_stats)} team stat records")
        logger.info(f"Loaded {len(player_roster)} player roster records")
        
        # Create features
        logger.info("Creating features...")
        feature_aggregator = FeatureAggregator()
        features_df = feature_aggregator.create_training_dataset(
            player_stats, team_stats, player_roster
        )
        
        if features_df.empty:
            logger.error("No features created. Check data quality.")
            return
        
        logger.info(f"Created {len(features_df)} feature records with {len(features_df.columns) - 1} features")
        
        # Train models
        logger.info("Training models...")
        trainer = ModelTrainer()
        results = trainer.train_all_models(features_df)
        
        # Save best model
        if trainer.best_model:
            metadata = {
                'model_type': trainer.best_model_name,
                'training_date': pd.Timestamp.now().isoformat(),
                'n_samples': len(features_df),
                'n_features': len(features_df.columns) - 1,
                'metrics': results[trainer.best_model_name]['metrics'],
                'feature_names': list(features_df.drop('target', axis=1).columns)
            }
            trainer.save_best_model(metadata)
            logger.info("Model training completed and saved")
        else:
            logger.error("No model was successfully trained")
        
    except Exception as e:
        logger.error(f"Error in model training: {e}", exc_info=True)
    finally:
        db_manager.close()


if __name__ == "__main__":
    import pandas as pd
    train_model()


