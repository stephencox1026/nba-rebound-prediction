"""Update manager for background data collection"""
import threading
import time
from datetime import datetime
from typing import Callable, Optional
import logging

from utils.helpers import setup_logging
from config.config import UPDATE_INTERVAL

logger = setup_logging(__name__)


class UpdateManager:
    """Manages background data updates"""
    
    def __init__(self, update_callback: Optional[Callable] = None):
        self.update_callback = update_callback
        self.update_interval = UPDATE_INTERVAL
        self.running = False
        self.thread = None
        self.last_update = None
    
    def start(self):
        """Start background update thread"""
        if self.running:
            logger.warning("Update manager already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info("Update manager started")
    
    def stop(self):
        """Stop background update thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Update manager stopped")
    
    def _update_loop(self):
        """Main update loop running in background thread"""
        while self.running:
            try:
                logger.info("Starting data update...")
                self.last_update = datetime.now()
                
                if self.update_callback:
                    self.update_callback()
                
                logger.info("Data update completed")
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
            
            # Wait for next update interval
            time.sleep(self.update_interval)
    
    def force_update(self):
        """Force an immediate update"""
        if self.update_callback:
            try:
                self.update_callback()
                self.last_update = datetime.now()
            except Exception as e:
                logger.error(f"Error in forced update: {e}")
    
    def get_status(self) -> dict:
        """Get update manager status"""
        return {
            'running': self.running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'update_interval': self.update_interval
        }


