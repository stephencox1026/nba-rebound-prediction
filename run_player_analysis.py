"""Standalone script to run player analysis window"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gui.player_analysis_window import PlayerAnalysisWindow
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = PlayerAnalysisWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


