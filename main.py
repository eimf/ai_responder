"""
main.py
-------
Entry point for the AI Responder desktop overlay application.

Run with:
    python main.py
"""

import sys
import os

# Ensure the project root is on the path so `modules` is importable
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from modules.app_controller import AppController


def main():
    # Enable High-DPI scaling (important for Windows 10 with display scaling)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Responder")
    app.setApplicationVersion("0.1.0")

    # Prevent the app from quitting when the last visible window is closed
    # (the overlay and tray icon keep it alive)
    app.setQuitOnLastWindowClosed(False)

    controller = AppController()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
