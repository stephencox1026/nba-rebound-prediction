"""Main entry point for NBA Rebound Prediction Model"""
import sys
import logging
import tkinter as tk
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.helpers import setup_logging
from gui.main_window import MainWindow
from config.config import LOG_LEVEL

# Setup logging
logger = setup_logging("nba_rebound_model")


def main():
    """Main application entry point"""
    try:
        logger.info("Starting NBA Rebound Prediction Model")
        
        # Create and run GUI
        root = tk.Tk()
        app = MainWindow(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


