"""
app_controller.py
-----------------
The main application controller.
Wires together the overlay, response panel, tray icon, and settings.

In Phase 1, the AI call and context extraction are stubbed out with
placeholder text so the full UI can be tested independently.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer

from modules.overlay import OverlayWindow
from modules.response_panel import ResponsePanel
from modules.settings_manager import SettingsManager
from modules.settings_dialog import SettingsDialog
from modules.tray_icon import TrayIcon


# ------------------------------------------------------------------ #
#  Stub worker — Phase 1 placeholder for AI + context extraction      #
#  (will be replaced in Phase 2 & 3)                                  #
# ------------------------------------------------------------------ #

class _StubWorker(QThread):
    """
    Simulates an async AI call.
    In Phase 2 this will be replaced by real UIAutomation + AI logic.
    """
    result_ready = pyqtSignal(str, str)   # (context_text, suggestion_text)
    error_occurred = pyqtSignal(str)

    def __init__(self, mode: str):
        super().__init__()
        self.mode = mode

    def run(self):
        import time
        time.sleep(1.5)   # simulate network latency

        if self.mode == "teams":
            context = (
                "Alice: Hey, are you joining the standup at 10?\n"
                "Bob: I might be 5 minutes late, go ahead without me."
            )
            suggestion = (
                "No worries, I'll catch up on the notes afterwards. "
                "Feel free to start without me!"
            )
        else:
            context = (
                "From: manager@company.com\n"
                "Subject: Q2 Budget Review\n\n"
                "Hi, could you please send over the updated budget figures "
                "for Q2 before end of day?"
            )
            suggestion = (
                "Hi,\n\n"
                "Thank you for reaching out. I will compile the updated Q2 budget "
                "figures and send them over to you before end of day today.\n\n"
                "Best regards"
            )

        self.result_ready.emit(context, suggestion)


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

        # ---- Show overlay ---- #
        self.overlay.show()

    # ------------------------------------------------------------------ #
    #  Icon click handler                                                   #
    # ------------------------------------------------------------------ #

    def _on_icon_clicked(self, mode: str):
        """Called when the user clicks the Teams or Outlook icon."""
        # Ensure settings are configured before proceeding
        if not self.settings.is_configured:
            self._open_settings()
            return

        panel = self._get_panel(mode)
        panel.show_loading("Detecting context…")

        # Cancel any running worker
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        # In Phase 1: use stub worker
        # In Phase 2+: replace with real context extractor + AI engine
        self._worker = _StubWorker(mode)
        self._worker.result_ready.connect(
            lambda ctx, sug: self._on_result(mode, ctx, sug)
        )
        self._worker.error_occurred.connect(
            lambda err: self._on_error(mode, err)
        )
        self._worker.start()

    def _on_result(self, mode: str, context: str, suggestion: str):
        panel = self._get_panel(mode)
        panel.set_context(context)
        panel.show_result(suggestion)

    def _on_error(self, mode: str, message: str):
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
