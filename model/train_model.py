"""Model training for rebound prediction"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import logging
from typing import Dict, Tuple, Optional

from utils.helpers import setup_logging
from model.model_manager import ModelManager
from config.config import TRAIN_TEST_SPLIT, VALIDATION_SPLIT

logger = setup_logging(__name__)


class ModelTrainer:
    """Trains and evaluates rebound prediction models"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.models = {}
        self.best_model = None
        self.best_model_name = None
    
    def prepare_data(self, features_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare data for training"""
        if features_df.empty:
            raise ValueError("Features DataFrame is empty")
        
        # Separate features and target
        if 'target' not in features_df.columns:
            raise ValueError("Target column not found in features DataFrame")
        
        X = features_df.drop('target', axis=1)
        y = features_df['target']
        
        # Remove any remaining non-numeric columns
        X = X.select_dtypes(include=[np.number])
        
        # Fill any remaining NaN values
        X = X.fillna(X.median())
        
        return X, y
    
    def train_xgboost(self, X_train: pd.DataFrame, y_train: pd.Series,
                     X_val: Optional[pd.DataFrame] = None,
                     y_val: Optional[pd.Series] = None) -> xgb.XGBRegressor:
        """Train XGBoost model"""
        logger.info("Training XGBoost model...")
        
        params = {
            'objective': 'reg:squarederror',
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1
        }
        
        model = xgb.XGBRegressor(**params)
        
        if X_val is not None and y_val is not None:
            try:
                # Try with early stopping (newer XGBoost versions)
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=False
                )
            except TypeError:
                # Fallback for older XGBoost versions
                model.fit(X_train, y_train)
        else:
            model.fit(X_train, y_train)
        
        logger.info("XGBoost model trained")
        return model
    
    def train_random_forest(self, X_train: pd.DataFrame, y_train: pd.Series) -> RandomForestRegressor:
        """Train Random Forest model"""
        logger.info("Training Random Forest model...")
        
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        logger.info("Random Forest model trained")
        return model
    
    def train_gradient_boosting(self, X_train: pd.DataFrame, y_train: pd.Series) -> GradientBoostingRegressor:
        """Train Gradient Boosting model"""
        logger.info("Training Gradient Boosting model...")
        
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        logger.info("Gradient Boosting model trained")
        return model
    
    def evaluate_model(self, model, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """Evaluate model performance"""
        y_pred = model.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # Calculate accuracy for over/under classification (within 1 rebound)
        within_one = np.abs(y_test - y_pred) <= 1.0
        accuracy = within_one.mean()
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'accuracy_within_one': accuracy
        }
        
        logger.info(f"Model metrics - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R2: {r2:.3f}, Accuracy: {accuracy:.3f}")
        
        return metrics
    
    def train_all_models(self, features_df: pd.DataFrame) -> Dict:
        """Train all models and select the best one"""
        X, y = self.prepare_data(features_df)
        
        # Time-based split (important for time series data)
        split_idx = int(len(X) * TRAIN_TEST_SPLIT)
        X_train_full = X.iloc[:split_idx]
        y_train_full = y.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_test = y.iloc[split_idx:]
        
        # Further split training data for validation
        val_idx = int(len(X_train_full) * (1 - VALIDATION_SPLIT))
        X_train = X_train_full.iloc[:val_idx]
        y_train = y_train_full.iloc[:val_idx]
        X_val = X_train_full.iloc[val_idx:]
        y_val = y_train_full.iloc[val_idx:]
        
        logger.info(f"Training set: {len(X_train)}, Validation set: {len(X_val)}, Test set: {len(X_test)}")
        
        results = {}
        
        # Train XGBoost
        try:
            xgb_model = self.train_xgboost(X_train, y_train, X_val, y_val)
            xgb_metrics = self.evaluate_model(xgb_model, X_test, y_test)
            results['xgboost'] = {
                'model': xgb_model,
                'metrics': xgb_metrics
            }
            self.models['xgboost'] = xgb_model
        except Exception as e:
            logger.error(f"Error training XGBoost: {e}")
        
        # Train Random Forest
        try:
            rf_model = self.train_random_forest(X_train, y_train)
            rf_metrics = self.evaluate_model(rf_model, X_test, y_test)
            results['random_forest'] = {
                'model': rf_model,
                'metrics': rf_metrics
            }
            self.models['random_forest'] = rf_model
        except Exception as e:
            logger.error(f"Error training Random Forest: {e}")
        
        # Train Gradient Boosting
        try:
            gb_model = self.train_gradient_boosting(X_train, y_train)
            gb_metrics = self.evaluate_model(gb_model, X_test, y_test)
            results['gradient_boosting'] = {
                'model': gb_model,
                'metrics': gb_metrics
            }
            self.models['gradient_boosting'] = gb_model
        except Exception as e:
            logger.error(f"Error training Gradient Boosting: {e}")
        
        # Select best model based on MAE
        if results:
            best_model_name = min(results.keys(), key=lambda k: results[k]['metrics']['mae'])
            self.best_model = results[best_model_name]['model']
            self.best_model_name = best_model_name
            
            logger.info(f"Best model: {best_model_name} with MAE: {results[best_model_name]['metrics']['mae']:.2f}")
        
        return results
    
    def save_best_model(self, metadata: Optional[Dict] = None):
        """Save the best model"""
        if self.best_model is None:
            raise ValueError("No model trained yet")
        
        if metadata is None:
            metadata = {
                'model_type': self.best_model_name,
                'training_date': pd.Timestamp.now().isoformat()
            }
        
        self.model_manager.save_model(self.best_model, 'rebound_predictor', metadata)
        logger.info(f"Best model ({self.best_model_name}) saved")

