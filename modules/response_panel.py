"""
response_panel.py
-----------------
The response panel that appears when the user clicks a mode icon.
Shows:
  - The detected/extracted context text (read-only preview)
  - The AI-generated suggestion (editable)
  - Copy, Regenerate, and Close buttons
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFrame, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QClipboard


class ResponsePanel(QDialog):
    """
    A floating, frameless modal that displays the AI suggestion.
    Emits `regenerate_requested` when the user wants a new suggestion.
    """

    regenerate_requested = pyqtSignal()

    # ------------------------------------------------------------------ #
    #  Construction                                                         #
    # ------------------------------------------------------------------ #

    def __init__(self, mode: str = "teams", parent=None):
        """
        Parameters
        ----------
        mode : str
            Either 'teams' or 'outlook'. Controls the colour theme and labels.
        """
        super().__init__(parent)
        self.mode = mode
        self._drag_pos = QPoint()

        # ---- Window flags ---- #
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ---- Theme colours ---- #
        self._accent = "#6264A7" if mode == "teams" else "#0078D4"
        self._mode_label = "Teams Reply" if mode == "teams" else "Outlook Reply"

        self._build_ui()
        self.setFixedWidth(420)

    # ------------------------------------------------------------------ #
    #  UI Construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        # ---- Inner container (gives us the rounded card look) ---- #
        self._card = QFrame(self)
        self._card.setObjectName("card")
        self._card.setStyleSheet(f"""
            QFrame#card {{
                background-color: #1e1e1e;
                border-radius: 12px;
                border: 1px solid #3a3a3a;
            }}
        """)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # ---- Header row ---- #
        header = QHBoxLayout()
        title_lbl = QLabel(self._mode_label)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {self._accent};")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover { color: white; }
        """)
        close_btn.clicked.connect(self.hide)

        header.addWidget(title_lbl)
        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # ---- Divider ---- #
        card_layout.addWidget(self._divider())

        # ---- Context preview section ---- #
        ctx_lbl = QLabel("Detected Context")
        ctx_lbl.setFont(QFont("Segoe UI", 9))
        ctx_lbl.setStyleSheet("color: #888888;")
        card_layout.addWidget(ctx_lbl)

        self.context_box = QTextEdit()
        self.context_box.setReadOnly(True)
        self.context_box.setFixedHeight(90)
        self.context_box.setPlaceholderText("Context will appear here after detection…")
        self.context_box.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #cccccc;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 10px;
            }
        """)
        card_layout.addWidget(self.context_box)

        # ---- Suggestion section ---- #
        sug_lbl = QLabel("Suggested Reply")
        sug_lbl.setFont(QFont("Segoe UI", 9))
        sug_lbl.setStyleSheet("color: #888888;")
        card_layout.addWidget(sug_lbl)

        self.suggestion_box = QTextEdit()
        self.suggestion_box.setFixedHeight(120)
        self.suggestion_box.setPlaceholderText("AI suggestion will appear here…")
        self.suggestion_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid {self._accent}88;
                border-radius: 6px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 11px;
            }}
            QTextEdit:focus {{
                border: 1px solid {self._accent};
            }}
        """)
        card_layout.addWidget(self.suggestion_box)

        # ---- Status label (shown during loading) ---- #
        self.status_lbl = QLabel("")
        self.status_lbl.setFont(QFont("Segoe UI", 9))
        self.status_lbl.setStyleSheet("color: #888888;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_lbl)

        # ---- Action buttons ---- #
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.copy_btn = self._make_action_button("Copy", self._accent, filled=True)
        self.copy_btn.clicked.connect(self._copy_suggestion)

        self.regen_btn = self._make_action_button("Regenerate", self._accent, filled=False)
        self.regen_btn.clicked.connect(self.regenerate_requested.emit)

        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.regen_btn)
        card_layout.addLayout(btn_row)

        outer.addWidget(self._card)
        self.setLayout(outer)

    # ------------------------------------------------------------------ #
    #  Helper widget factories                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #3a3a3a;")
        line.setFixedHeight(1)
        return line

    @staticmethod
    def _make_action_button(text: str, accent: str, filled: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 10))
        if filled:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0 16px;
                }}
                QPushButton:hover {{ background-color: {accent}CC; }}
                QPushButton:pressed {{ background-color: {accent}99; }}
                QPushButton:disabled {{ background-color: #444; color: #888; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {accent};
                    border: 1px solid {accent};
                    border-radius: 6px;
                    padding: 0 16px;
                }}
                QPushButton:hover {{ background-color: {accent}22; }}
                QPushButton:pressed {{ background-color: {accent}44; }}
                QPushButton:disabled {{ color: #555; border-color: #555; }}
            """)
        return btn

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def show_loading(self, context_text: str = ""):
        """Call this immediately after the icon is clicked to show a loading state."""
        self.context_box.setPlainText(context_text)
        self.suggestion_box.setPlainText("")
        self.status_lbl.setText("⏳  Generating suggestion…")
        self.copy_btn.setEnabled(False)
        self.regen_btn.setEnabled(False)
        self._position_near_overlay()
        self.show()
        QApplication.processEvents()

    def show_result(self, suggestion: str):
        """Call this when the AI response is ready."""
        self.suggestion_box.setPlainText(suggestion)
        self.status_lbl.setText("")
        self.copy_btn.setEnabled(True)
        self.regen_btn.setEnabled(True)
        self._position_near_overlay()
        self.show()
        self.raise_()
        self.activateWindow()

    def show_error(self, message: str):
        """Call this when an error occurs during context capture or AI call."""
        self.suggestion_box.setPlainText(message)
        self.status_lbl.setText("⚠️  See details above")
        self.copy_btn.setEnabled(False)
        self.regen_btn.setEnabled(True)
        self._position_near_overlay()
        self.show()
        self.raise_()
        self.activateWindow()

    def set_context(self, text: str):
        self.context_box.setPlainText(text)

    # ------------------------------------------------------------------ #
    #  Positioning                                                          #
    # ------------------------------------------------------------------ #

    def _position_near_overlay(self):
        """Position the panel below the overlay window (or its parent)."""
        if self.parent():
            overlay_geo = self.parent().geometry()
            x = overlay_geo.right() - self.width()
            y = overlay_geo.bottom() + 8
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 16
            y = screen.top() + 70

        # Clamp to screen
        screen = QApplication.primaryScreen().availableGeometry()
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - 300))
        self.move(x, y)

    # ------------------------------------------------------------------ #
    #  Actions                                                              #
    # ------------------------------------------------------------------ #

    def _copy_suggestion(self):
        text = self.suggestion_box.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.copy_btn.setText("Copied ✓")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copy"))

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
