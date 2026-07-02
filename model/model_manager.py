"""Model persistence and version management"""
import pickle
import json
from pathlib import Path
from typing import Optional, Dict
import logging
from datetime import datetime

from config.config import MODELS_DIR

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages model saving, loading, and versioning"""
    
    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or MODELS_DIR
        self.models_dir.mkdir(exist_ok=True)
    
    def save_model(self, model, model_name: str, metadata: Optional[Dict] = None):
        """Save model to disk with metadata"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"{model_name}_{timestamp}.pkl"
        model_path = self.models_dir / model_filename
        
        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save metadata
        if metadata:
            metadata_filename = f"{model_name}_{timestamp}_metadata.json"
            metadata_path = self.models_dir / metadata_filename
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        return model_path
    
    def load_latest_model(self, model_name: str):
        """Load the most recent model by name"""
        model_files = list(self.models_dir.glob(f"{model_name}_*.pkl"))
        
        if not model_files:
            raise FileNotFoundError(f"No models found for {model_name}")
        
        # Get most recent model
        latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_model, 'rb') as f:
            model = pickle.load(f)
        
        logger.info(f"Loaded model from {latest_model}")
        return model
    
    def load_model_metadata(self, model_name: str) -> Optional[Dict]:
        """Load metadata for the most recent model"""
        metadata_files = list(self.models_dir.glob(f"{model_name}_*_metadata.json"))
        
        if not metadata_files:
            return None
        
        latest_metadata = max(metadata_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_metadata, 'r') as f:
            metadata = json.load(f)
        
        return metadata
    
    def list_models(self) -> list:
        """List all saved models"""
        model_files = list(self.models_dir.glob("*.pkl"))
        return [f.stem for f in model_files]


