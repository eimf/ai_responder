"""
app_detector.py
---------------
Detects which application is currently in the foreground (Teams, Outlook,
or Cisco Jabber) using the Win32 API.  Returns an AppContext object with
the app type and window handle for downstream text extraction.
"""

import ctypes
import ctypes.wintypes

# App type constants
APP_TEAMS = "teams"
APP_OUTLOOK = "outlook"
APP_JABBER = "jabber"
APP_UNKNOWN = "unknown"

# Known process / window-title signatures
TEAMS_SIGNATURES = [
    "microsoft teams",
    "teams",
]

OUTLOOK_SIGNATURES = [
    "microsoft outlook",
    "outlook",
]

JABBER_SIGNATURES = [
    "cisco jabber",
    "jabber",
]


class AppContext:
    """Holds information about the currently detected foreground application."""

    def __init__(self, app_type: str, hwnd: int, window_title: str, process_name: str):
        self.app_type = app_type
        self.hwnd = hwnd
        self.window_title = window_title
        self.process_name = process_name

    def is_teams(self) -> bool:
        return self.app_type == APP_TEAMS

    def is_outlook(self) -> bool:
        return self.app_type == APP_OUTLOOK

    def is_jabber(self) -> bool:
        return self.app_type == APP_JABBER

    def is_known(self) -> bool:
        return self.app_type != APP_UNKNOWN

    def __repr__(self):
        return (
            f"AppContext(app_type={self.app_type!r}, "
            f"window_title={self.window_title!r}, "
            f"process_name={self.process_name!r})"
        )


def _get_foreground_window_info() -> tuple[int, str, str]:
    """
    Returns (hwnd, window_title, process_name) for the current foreground window.
    Uses ctypes to call Win32 APIs directly — no external dependencies.
    """
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return 0, "", ""

        # Get window title
        length = user32.GetWindowTextLengthW(hwnd) + 1
        title_buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, title_buf, length)
        window_title = title_buf.value

        # Get process ID from window handle
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        # Open process to get executable name
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h_process = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
        )

        process_name = ""
        if h_process:
            buf = ctypes.create_unicode_buffer(1024)
            size = ctypes.wintypes.DWORD(1024)
            if psapi.GetModuleFileNameExW(h_process, None, buf, size):
                import os
                process_name = os.path.basename(buf.value).upper()
            kernel32.CloseHandle(h_process)

        return hwnd, window_title, process_name

    except Exception:
        return 0, "", ""


def _classify_app(window_title: str, process_name: str) -> str:
    """Classify the app type based on window title and process name."""
    title_lower = window_title.lower()
    proc_lower = process_name.lower()

    # Check Teams
    if "teams.exe" in proc_lower or "ms-teams.exe" in proc_lower:
        return APP_TEAMS
    for sig in TEAMS_SIGNATURES:
        if sig in title_lower:
            return APP_TEAMS

    # Check Outlook
    if "outlook.exe" in proc_lower:
        return APP_OUTLOOK
    for sig in OUTLOOK_SIGNATURES:
        if sig in title_lower:
            return APP_OUTLOOK

    # Check Jabber
    if "ciscojabber.exe" in proc_lower or "jabber.exe" in proc_lower:
        return APP_JABBER
    for sig in JABBER_SIGNATURES:
        if sig in title_lower:
            return APP_JABBER

    return APP_UNKNOWN


def detect_foreground_app() -> AppContext:
    """
    Main entry point. Detects the foreground application and returns
    an AppContext describing it.
    """
    hwnd, window_title, process_name = _get_foreground_window_info()
    app_type = _classify_app(window_title, process_name)
    return AppContext(
        app_type=app_type,
        hwnd=hwnd,
        window_title=window_title,
        process_name=process_name,
    )
