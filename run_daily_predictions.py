"""Standalone script to run daily predictions window"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gui.daily_predictions_window import DailyPredictionsWindow
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = DailyPredictionsWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


