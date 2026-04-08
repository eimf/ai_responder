"""
app_controller.py
-----------------
The main application controller.
Wires together the overlay, response panel, tray icon, settings,
context manager, and AI engine.

Phase 2: Real UIAutomation context extraction with full debug logging.
         AI call is still stubbed — will be replaced in Phase 3.
"""

import time
import logging
import traceback

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer

from modules.overlay import OverlayWindow
from modules.response_panel import ResponsePanel
from modules.settings_manager import SettingsManager
from modules.settings_dialog import SettingsDialog
from modules.tray_icon import TrayIcon
from modules.context_manager import ContextManager
from modules.text_extractor import ExtractedContext
from modules.ai_engine import generate_suggestion

# Set up logging to console so we can see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
# Suppress noisy comtypes pointer-release DEBUG spam
logging.getLogger("comtypes").setLevel(logging.INFO)
logging.getLogger("comtypes._post_coinit.unknwn").setLevel(logging.INFO)

log = logging.getLogger("AppController")


# ------------------------------------------------------------------ #
#  Context + AI Worker                                                 #
# ------------------------------------------------------------------ #

class _ContextWorker(QThread):
    """
    Runs context extraction and AI suggestion generation in a background
    thread so the UI stays responsive.
    """
    result_ready = pyqtSignal(str, str)   # (context_text, suggestion_text)
    error_occurred = pyqtSignal(str)

    def __init__(self, mode: str, settings):
        super().__init__()
        self.mode = mode
        self.settings = settings

    def run(self):
        log.debug(f"Worker started for mode={self.mode}")
        try:
            # Brief pause to ensure the target app has regained focus
            # (the overlay already waited 400ms before starting this worker)
            time.sleep(0.2)

            # ---- Step 1: Detect foreground app ---- #
            from modules.app_detector import detect_foreground_app
            app_ctx = detect_foreground_app()
            log.debug(f"Detected app: {app_ctx}")

            # If we didn't detect the expected app, retry once after a short wait
            if app_ctx.app_type == "unknown":
                log.debug("App not detected, retrying after 500ms...")
                time.sleep(0.5)
                app_ctx = detect_foreground_app()
                log.debug(f"Retry detected app: {app_ctx}")

            # ---- Step 2: Extract context ---- #
            from modules.text_extractor import extract_context
            extracted = extract_context(app_ctx)
            log.debug(
                f"Extraction method={extracted.extraction_method} "
                f"has_content={extracted.has_content()} "
                f"error={extracted.error!r} "
                f"body_len={len(extracted.body)} "
                f"raw_len={len(extracted.raw_text)}"
            )

            if extracted.error:
                log.warning(f"Extraction error: {extracted.error}")

            if not extracted.has_content():
                # Show what we know even if content is empty
                debug_info = (
                    f"Window: {app_ctx.window_title!r}\n"
                    f"Process: {app_ctx.process_name!r}\n"
                    f"App type: {app_ctx.app_type}\n"
                    f"Method tried: {extracted.extraction_method}\n"
                    f"Error: {extracted.error or 'none'}\n\n"
                    "Tips:\n"
                    "• Make sure an email/chat is open or selected\n"
                    "• The window must not be minimized\n"
                    "• Try clicking on the message body before using AI Responder"
                )
                self.error_occurred.emit(debug_info)
                return

            context_text = extracted.to_prompt_context()
            log.debug(f"Context text (first 200 chars): {context_text[:200]!r}")

            # ---- Step 3: Generate AI suggestion ---- #
            suggestion = generate_suggestion(context_text, self.mode, self.settings)
            self.result_ready.emit(context_text, suggestion)

        except Exception as e:
            tb = traceback.format_exc()
            log.error(f"Worker exception:\n{tb}")
            self.error_occurred.emit(f"Error during extraction:\n{str(e)}\n\n{tb}")


# ------------------------------------------------------------------ #
#  Main Controller                                                     #
# ------------------------------------------------------------------ #

class AppController(QObject):

    def __init__(self):
        super().__init__()
        log.debug("AppController initialising")

        self.settings = SettingsManager()

        self.overlay = OverlayWindow()
        self.overlay.teams_clicked.connect(lambda: self._on_icon_clicked("teams"))
        self.overlay.outlook_clicked.connect(lambda: self._on_icon_clicked("outlook"))
        self.overlay.jabber_clicked.connect(lambda: self._on_icon_clicked("jabber"))

        self._panels: dict[str, ResponsePanel] = {}

        self.tray = TrayIcon()
        self.tray.show_overlay_requested.connect(self.overlay.show)
        self.tray.hide_overlay_requested.connect(self.overlay.hide)
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.quit_requested.connect(QApplication.instance().quit)
        self.tray.show()

        self._worker: QThread | None = None
        self.overlay.show()
        log.debug("AppController ready")

    def _on_icon_clicked(self, mode: str):
        log.debug(f"Icon clicked: mode={mode}")

        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        # Hide overlay so target app regains focus
        self.overlay.hide()
        log.debug("Overlay hidden, scheduling capture in 400ms")

        QTimer.singleShot(400, lambda: self._start_capture(mode))

    def _start_capture(self, mode: str):
        log.debug(f"Starting capture worker for mode={mode}")
        self._worker = _ContextWorker(mode, self.settings)
        self._worker.result_ready.connect(
            lambda ctx, sug: self._on_result(mode, ctx, sug)
        )
        self._worker.error_occurred.connect(
            lambda err: self._on_error(mode, err)
        )
        self._worker.start()

    def _on_result(self, mode: str, context: str, suggestion: str):
        log.debug(f"Result received for mode={mode}, showing panel")
        self.overlay.show()
        panel = self._get_panel(mode)
        panel.set_context(context)
        panel.show_result(suggestion)

    def _on_error(self, mode: str, message: str):
        log.warning(f"Error for mode={mode}: {message[:100]}")
        self.overlay.show()
        panel = self._get_panel(mode)
        panel.show_error(message)

    def _get_panel(self, mode: str) -> ResponsePanel:
        if mode not in self._panels:
            panel = ResponsePanel(mode=mode, parent=self.overlay)
            panel.regenerate_requested.connect(lambda: self._on_icon_clicked(mode))
            self._panels[mode] = panel
        return self._panels[mode]

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, parent=self.overlay)
        dlg.exec()
