"""
tray_icon.py
------------
System tray icon that provides a right-click context menu with:
  - Show / Hide overlay
  - Settings
  - Quit
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QObject


def _make_tray_icon_pixmap(size: int = 32) -> QPixmap:
    """Generate a simple coloured 'AI' pixmap for the tray icon."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0078D4"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.setPen(QColor("white"))
    font = QFont("Segoe UI", int(size * 0.35), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
    painter.end()
    return px


class TrayIcon(QObject):
    """
    Wraps QSystemTrayIcon and exposes signals for the main app controller.
    """

    show_overlay_requested = pyqtSignal()
    hide_overlay_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        px = _make_tray_icon_pixmap(32)
        self._tray = QSystemTrayIcon(QIcon(px), parent)
        self._tray.setToolTip("AI Responder")

        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #3a3a3a;
                font-family: 'Segoe UI';
                font-size: 10px;
            }
            QMenu::item:selected {
                background-color: #0078D4;
            }
            QMenu::separator {
                height: 1px;
                background: #3a3a3a;
                margin: 4px 8px;
            }
        """)

        self._action_toggle = self._menu.addAction("Hide Overlay")
        self._action_toggle.triggered.connect(self._toggle_overlay)

        self._menu.addSeparator()

        action_settings = self._menu.addAction("⚙  Settings")
        action_settings.triggered.connect(self.settings_requested.emit)

        self._menu.addSeparator()

        action_quit = self._menu.addAction("✕  Quit")
        action_quit.triggered.connect(self.quit_requested.emit)

        self._tray.setContextMenu(self._menu)
        self._overlay_visible = True

    def show(self):
        self._tray.show()

    def _toggle_overlay(self):
        if self._overlay_visible:
            self._overlay_visible = False
            self._action_toggle.setText("Show Overlay")
            self.hide_overlay_requested.emit()
        else:
            self._overlay_visible = True
            self._action_toggle.setText("Hide Overlay")
            self.show_overlay_requested.emit()

    def set_overlay_visible(self, visible: bool):
        self._overlay_visible = visible
        self._action_toggle.setText("Hide Overlay" if visible else "Show Overlay")
