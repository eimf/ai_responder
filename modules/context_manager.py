"""
context_manager.py
------------------
Orchestrates the full context capture pipeline:
  1. Detect foreground app (Teams or Outlook)
  2. Extract text content from the window
  3. Return a clean ExtractedContext ready for the AI engine

This is the single entry point called by the overlay UI when the user
clicks a Teams or Outlook icon.
"""

import threading
from typing import Callable, Optional

from .app_detector import detect_foreground_app, APP_TEAMS, APP_OUTLOOK, APP_JABBER, APP_UNKNOWN
from .text_extractor import extract_context, ExtractedContext


class ContextManager:
    """
    Manages context capture with support for async (threaded) operation
    so the UI remains responsive during extraction.
    """

    def __init__(self):
        self._current_thread: Optional[threading.Thread] = None

    def capture(
        self,
        requested_app: str,
        on_success: Callable[[ExtractedContext], None],
        on_error: Callable[[str], None],
    ) -> None:
        """
        Capture context for the requested app type asynchronously.

        Args:
            requested_app: APP_TEAMS or APP_OUTLOOK — which icon the user clicked
            on_success: callback called with ExtractedContext on success
            on_error: callback called with an error message string on failure
        """
        # Cancel any in-progress capture
        if self._current_thread and self._current_thread.is_alive():
            # Threads cannot be forcibly stopped; we just let the new one proceed
            pass

        self._current_thread = threading.Thread(
            target=self._capture_worker,
            args=(requested_app, on_success, on_error),
            daemon=True,
        )
        self._current_thread.start()

    def _capture_worker(
        self,
        requested_app: str,
        on_success: Callable[[ExtractedContext], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Worker thread that performs detection and extraction."""
        try:
            # Step 1: Detect foreground app
            app_ctx = detect_foreground_app()

            # Step 2: Validate — check if the detected app matches what was requested
            if app_ctx.app_type == APP_UNKNOWN:
                # App not detected — still try extraction based on requested type
                # (user may have clicked before switching focus)
                from .app_detector import AppContext
                app_ctx = AppContext(
                    app_type=requested_app,
                    hwnd=app_ctx.hwnd,
                    window_title=app_ctx.window_title,
                    process_name=app_ctx.process_name,
                )

            elif app_ctx.app_type != requested_app:
                # Detected a different app than requested — warn but proceed
                # (user may have clicked the overlay while focused on another app)
                pass  # We'll extract from whatever is in the foreground

            # Step 3: Extract text
            extracted = extract_context(app_ctx)

            # Step 4: Validate content
            if not extracted.has_content() and extracted.error:
                on_error(extracted.error)
                return

            on_success(extracted)

        except Exception as e:
            on_error(f"Context capture failed: {str(e)}")

    def capture_sync(self, requested_app: str) -> ExtractedContext:
        """
        Synchronous version of capture — blocks until extraction is complete.
        Useful for testing and debugging.
        """
        app_ctx = detect_foreground_app()

        if app_ctx.app_type == APP_UNKNOWN:
            from .app_detector import AppContext
            app_ctx = AppContext(
                app_type=requested_app,
                hwnd=app_ctx.hwnd,
                window_title=app_ctx.window_title,
                process_name=app_ctx.process_name,
            )

        return extract_context(app_ctx)
