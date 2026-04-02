"""
app_controller.py
-----------------
The main application controller.
Wires together the overlay, response panel, tray icon, settings,
context manager, and AI engine.

Phase 2: Real UIAutomation context extraction is wired in.
         Overlay is hidden before capture so the target app regains focus.
         AI call is still stubbed — will be replaced in Phase 3.
"""

import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer

from modules.overlay import OverlayWindow
from modules.response_panel import ResponsePanel
from modules.settings_manager import SettingsManager
from modules.settings_dialog import SettingsDialog
from modules.tray_icon import TrayIcon
from modules.context_manager import ContextManager
from modules.text_extractor import ExtractedContext


# ------------------------------------------------------------------ #
#  Context + AI Worker                                                 #
# ------------------------------------------------------------------ #

class _ContextWorker(QThread):
    """
    Runs context extraction and AI suggestion generation in a background
    thread so the UI stays responsive.

    The overlay is hidden by the controller BEFORE this thread starts,
    giving the target app time to regain foreground focus.
    """
    result_ready = pyqtSignal(str, str)   # (context_text, suggestion_text)
    error_occurred = pyqtSignal(str)

    def __init__(self, mode: str, settings):
        super().__init__()
        self.mode = mode
        self.settings = settings

    def run(self):
        try:
            # Brief pause to ensure the target app has regained focus
            # after the overlay was hidden (300ms is enough for Win32 focus switch)
            time.sleep(0.35)

            # ---- Step 1: Extract context ---- #
            ctx_manager = ContextManager()
            extracted: ExtractedContext = ctx_manager.capture_sync(self.mode)

            if not extracted.has_content():
                error_msg = extracted.error or (
                    f"Could not read content from "
                    f"{'Teams' if self.mode == 'teams' else 'Outlook'}.\n"
                    "Make sure the application window is open and visible "
                    "and not minimised."
                )
                self.error_occurred.emit(error_msg)
                return

            context_text = extracted.to_prompt_context()

            # ---- Step 2: Generate AI suggestion (Phase 3 stub) ---- #
            # TODO: Replace with real Azure OpenAI call in Phase 3
            suggestion = self._stub_ai_suggestion(context_text, self.mode)

            self.result_ready.emit(context_text, suggestion)

        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")

    def _stub_ai_suggestion(self, context: str, mode: str) -> str:
        """
        Phase 3 stub — returns a placeholder suggestion.
        Will be replaced by a real Azure OpenAI call in Phase 3.
        """
        if mode == "teams":
            return (
                "[AI suggestion will appear here in Phase 3]\n\n"
                "--- Detected context preview ---\n"
                f"{context[:400]}{'...' if len(context) > 400 else ''}"
            )
        else:
            return (
                "[AI email draft will appear here in Phase 3]\n\n"
                "--- Detected context preview ---\n"
                f"{context[:400]}{'...' if len(context) > 400 else ''}"
            )


# ------------------------------------------------------------------ #
#  Main Controller                                                     #
# ------------------------------------------------------------------ #

class AppController(QObject):
    """
    Orchestrates all UI components and business logic.
    """

    def __init__(self):
        super().__init__()

        self.settings = SettingsManager()

        # ---- Overlay ---- #
        self.overlay = OverlayWindow()
        self.overlay.teams_clicked.connect(lambda: self._on_icon_clicked("teams"))
        self.overlay.outlook_clicked.connect(lambda: self._on_icon_clicked("outlook"))

        # ---- Response panels (one per mode, lazily created) ---- #
        self._panels: dict[str, ResponsePanel] = {}

        # ---- Tray icon ---- #
        self.tray = TrayIcon()
        self.tray.show_overlay_requested.connect(self.overlay.show)
        self.tray.hide_overlay_requested.connect(self.overlay.hide)
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.quit_requested.connect(QApplication.instance().quit)
        self.tray.show()

        # ---- Active worker ---- #
        self._worker: QThread | None = None
        self._pending_mode: str = ""

        # ---- Show overlay ---- #
        self.overlay.show()

    # ------------------------------------------------------------------ #
    #  Icon click handler                                                   #
    # ------------------------------------------------------------------ #

    def _on_icon_clicked(self, mode: str):
        """
        Called when the user clicks the Teams or Outlook icon.

        Flow:
          1. Hide the overlay so the target app regains foreground focus
          2. After a short delay, start the extraction worker
          3. When the worker finishes, restore the overlay and show the panel
        """
        # Cancel any running worker
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self._pending_mode = mode

        # Step 1: Hide the overlay so the target app becomes foreground
        self.overlay.hide()

        # Step 2: After 400ms (enough for Win32 focus switch), start worker
        QTimer.singleShot(400, lambda: self._start_capture(mode))

    def _start_capture(self, mode: str):
        """Start the context extraction worker after the overlay has been hidden."""
        self._worker = _ContextWorker(mode, self.settings)
        self._worker.result_ready.connect(
            lambda ctx, sug: self._on_result(mode, ctx, sug)
        )
        self._worker.error_occurred.connect(
            lambda err: self._on_error(mode, err)
        )
        self._worker.start()

    def _on_result(self, mode: str, context: str, suggestion: str):
        """Called when extraction + suggestion generation succeeds."""
        # Restore the overlay first
        self.overlay.show()

        panel = self._get_panel(mode)
        panel.set_context(context)
        panel.show_result(suggestion)

    def _on_error(self, mode: str, message: str):
        """Called when extraction fails."""
        # Restore the overlay even on error
        self.overlay.show()

        panel = self._get_panel(mode)
        panel.show_error(message)

    # ------------------------------------------------------------------ #
    #  Panel management                                                     #
    # ------------------------------------------------------------------ #

    def _get_panel(self, mode: str) -> ResponsePanel:
        if mode not in self._panels:
            panel = ResponsePanel(mode=mode, parent=self.overlay)
            panel.regenerate_requested.connect(lambda: self._on_icon_clicked(mode))
            self._panels[mode] = panel
        return self._panels[mode]

    # ------------------------------------------------------------------ #
    #  Settings                                                             #
    # ------------------------------------------------------------------ #

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, parent=self.overlay)
        dlg.exec()
