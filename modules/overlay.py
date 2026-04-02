"""
overlay.py
----------
The floating, always-on-top overlay window containing the Teams and Outlook icons.
Supports dragging, hover tooltips, and click-to-trigger context detection.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QCursor, QColor, QPainter, QBrush, QPen


class OverlayWindow(QWidget):
    """
    A small, semi-transparent, frameless, always-on-top window
    that floats in the top-right corner of the screen.
    Emits signals when the user clicks the Teams or Outlook icon.
    """

    teams_clicked = pyqtSignal()
    outlook_clicked = pyqtSignal()

    # ------------------------------------------------------------------ #
    #  Construction                                                         #
    # ------------------------------------------------------------------ #

    def __init__(self, parent=None):
        super().__init__(parent)

        # ---- Window flags: frameless, always on top, tool window ---- #
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool                   # keeps it off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # don't steal focus

        # ---- State ---- #
        self._drag_pos = QPoint()
        self._is_expanded = False

        # ---- Build UI ---- #
        self._build_ui()
        self._position_top_right()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # ---- Teams button ---- #
        self.btn_teams = self._make_icon_button(
            label="T",
            color="#6264A7",          # Microsoft Teams purple
            tooltip="AI Reply — Teams",
        )
        self.btn_teams.clicked.connect(self.teams_clicked.emit)

        # ---- Outlook button ---- #
        self.btn_outlook = self._make_icon_button(
            label="O",
            color="#0078D4",          # Microsoft Outlook blue
            tooltip="AI Reply — Outlook",
        )
        self.btn_outlook.clicked.connect(self.outlook_clicked.emit)

        layout.addWidget(self.btn_teams)
        layout.addWidget(self.btn_outlook)
        self.setLayout(layout)

        # Fixed collapsed size
        self.setFixedSize(90, 44)

    @staticmethod
    def _make_icon_button(label: str, color: str, tooltip: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        btn.setFont(font)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 16px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {color}CC;
                border: 2px solid white;
            }}
            QPushButton:pressed {{
                background-color: {color}99;
            }}
        """)
        return btn

    # ------------------------------------------------------------------ #
    #  Positioning                                                          #
    # ------------------------------------------------------------------ #

    def _position_top_right(self):
        """Place the overlay in the top-right corner with a small margin."""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 16
        y = screen.top() + 16
        self.move(x, y)

    # ------------------------------------------------------------------ #
    #  Painting — rounded pill background                                   #
    # ------------------------------------------------------------------ #

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark pill
        brush = QBrush(QColor(30, 30, 30, 200))
        painter.setBrush(brush)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 22, 22)

    # ------------------------------------------------------------------ #
    #  Dragging                                                             #
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()
        event.accept()
