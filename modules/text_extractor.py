"""
text_extractor.py
-----------------
Extracts visible text content from Microsoft Outlook and Teams windows.

Strategy (in order of preference):
  1. UIAutomation tree traversal (uiautomation library)
  2. Windows OCR via WinRT (winrt library)
  3. Tesseract OCR (pytesseract + mss screenshot)

Each extractor returns an ExtractedContext object with the raw text,
source app, and extraction method used.
"""

import re
import sys
from dataclasses import dataclass, field
from typing import Optional

from .app_detector import AppContext, APP_TEAMS, APP_OUTLOOK


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ExtractedContext:
    """Holds the text extracted from the active application window."""
    app_type: str = ""
    subject: str = ""           # Email subject (Outlook only)
    sender: str = ""            # Sender name/email (Outlook only)
    body: str = ""              # Main content body
    thread: str = ""            # Thread / conversation history
    extraction_method: str = "" # "uiautomation", "winrt_ocr", "tesseract", "none"
    raw_text: str = ""          # Unprocessed full text (for debugging)
    error: str = ""             # Error message if extraction failed

    def has_content(self) -> bool:
        return bool(self.body or self.thread or self.raw_text)

    def to_prompt_context(self) -> str:
        """Format the extracted content into a clean string for the AI prompt."""
        parts = []
        if self.subject:
            parts.append(f"Subject: {self.subject}")
        if self.sender:
            parts.append(f"From: {self.sender}")
        if self.thread:
            parts.append(f"Conversation:\n{self.thread}")
        if self.body and self.body != self.thread:
            parts.append(f"Current message:\n{self.body}")
        if not parts and self.raw_text:
            parts.append(self.raw_text)
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Text cleaning utilities
# ---------------------------------------------------------------------------

def _clean_text(text: str, max_chars: int = 4000) -> str:
    """Remove noise and truncate text to stay within token limits."""
    if not text:
        return ""
    # Collapse excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = text.strip()
    # Truncate to max_chars from the end (most recent content is most relevant)
    if len(text) > max_chars:
        text = "...[truncated]\n" + text[-max_chars:]
    return text


# ---------------------------------------------------------------------------
# Method 1: UIAutomation (primary)
# ---------------------------------------------------------------------------

def _extract_via_uiautomation(ctx: AppContext) -> Optional[ExtractedContext]:
    """
    Use the uiautomation library to walk the accessibility tree of the
    target window and extract relevant text elements.
    """
    try:
        import uiautomation as auto
    except ImportError:
        return None

    result = ExtractedContext(
        app_type=ctx.app_type,
        extraction_method="uiautomation"
    )

    try:
        # Get the root control for the foreground window
        root = auto.ControlFromHandle(ctx.hwnd)
        if not root:
            return None

        if ctx.is_outlook():
            return _extract_outlook_uia(root, result)
        elif ctx.is_teams():
            return _extract_teams_uia(root, result)

    except Exception as e:
        result.error = str(e)
        return result

    return None


def _extract_outlook_uia(root, result: ExtractedContext) -> ExtractedContext:
    """Extract email content from Classic Outlook using UIAutomation."""
    import uiautomation as auto

    collected_texts = []

    # Try to find the reading pane / email body
    # Classic Outlook uses a Document control for the email body
    body_control = root.DocumentControl(searchDepth=10)
    if body_control.Exists(0):
        result.body = _clean_text(body_control.GetValueOrDefault(""))
        if not result.body:
            # Try getting all text from the document
            result.body = _clean_text(
                " ".join(c.Name for c in body_control.GetChildren() if c.Name)
            )

    # Try to find subject line — typically a text/edit control near the top
    subject_patterns = ["subject", "re:", "fw:", "fwd:"]
    for ctrl in root.GetChildren():
        name_lower = (ctrl.Name or "").lower()
        if any(p in name_lower for p in subject_patterns):
            result.subject = ctrl.Name
            break

    # Fallback: collect all visible text from the window
    if not result.body:
        all_text = _collect_all_text_uia(root)
        result.raw_text = _clean_text("\n".join(all_text))

    return result


def _extract_teams_uia(root, result: ExtractedContext) -> ExtractedContext:
    """Extract chat content from Microsoft Teams using UIAutomation."""
    import uiautomation as auto

    # Teams renders messages in a list/group control
    # Try to find the message list area
    message_texts = []

    # Look for list items (chat messages)
    list_ctrl = root.ListControl(searchDepth=8)
    if list_ctrl.Exists(0):
        items = list_ctrl.GetChildren()
        for item in items[-20:]:  # Last 20 messages
            text = item.Name or ""
            if text and len(text) > 2:
                message_texts.append(text)

    if message_texts:
        result.thread = _clean_text("\n".join(message_texts))
        result.body = message_texts[-1] if message_texts else ""
    else:
        # Fallback: collect all visible text
        all_text = _collect_all_text_uia(root)
        result.raw_text = _clean_text("\n".join(all_text))

    return result


def _collect_all_text_uia(root, max_items: int = 200) -> list:
    """Walk the UIAutomation tree and collect all non-empty text values."""
    import uiautomation as auto
    texts = []
    count = [0]

    def walk(ctrl, depth=0):
        if count[0] >= max_items or depth > 12:
            return
        name = ctrl.Name or ""
        if name and len(name) > 2 and name not in texts:
            texts.append(name)
            count[0] += 1
        for child in ctrl.GetChildren():
            walk(child, depth + 1)

    walk(root)
    return texts


# ---------------------------------------------------------------------------
# Method 2: Windows OCR via WinRT (secondary fallback)
# ---------------------------------------------------------------------------

def _extract_via_winrt_ocr(ctx: AppContext) -> Optional[ExtractedContext]:
    """
    Capture a screenshot of the target window and run Windows OCR
    (WinRT OcrEngine) on it. Requires Windows 10+ and the winrt package.
    """
    try:
        import asyncio
        import mss
        import mss.tools
        from PIL import Image
        import io

        # Try to import WinRT OCR
        try:
            import winrt.windows.media.ocr as winrt_ocr
            import winrt.windows.globalization as globalization
            import winrt.windows.graphics.imaging as imaging
        except ImportError:
            return None

        result = ExtractedContext(
            app_type=ctx.app_type,
            extraction_method="winrt_ocr"
        )

        # Capture screenshot of the foreground window
        screenshot_bytes = _capture_window_screenshot(ctx.hwnd)
        if not screenshot_bytes:
            return None

        # Run OCR synchronously via asyncio
        async def run_ocr():
            language = globalization.Language("en-US")
            engine = winrt_ocr.OcrEngine.try_create_from_language(language)
            if not engine:
                engine = winrt_ocr.OcrEngine.try_create_from_user_profile_languages()
            if not engine:
                return ""

            img = Image.open(io.BytesIO(screenshot_bytes))
            # Convert PIL image to WinRT SoftwareBitmap
            img_bytes = img.tobytes()
            bitmap = imaging.SoftwareBitmap(
                imaging.BitmapPixelFormat.RGBA8,
                img.width,
                img.height,
                imaging.BitmapAlphaMode.PREMULTIPLIED
            )
            ocr_result = await engine.recognize_async(bitmap)
            return ocr_result.text if ocr_result else ""

        loop = asyncio.new_event_loop()
        text = loop.run_until_complete(run_ocr())
        loop.close()

        result.raw_text = _clean_text(text)
        return result

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Method 3: Tesseract OCR (last resort fallback)
# ---------------------------------------------------------------------------

def _extract_via_tesseract(ctx: AppContext) -> Optional[ExtractedContext]:
    """
    Capture a screenshot and run Tesseract OCR on it.
    Requires pytesseract and mss to be installed.
    """
    try:
        import pytesseract
        from PIL import Image
        import mss
        import io

        result = ExtractedContext(
            app_type=ctx.app_type,
            extraction_method="tesseract"
        )

        screenshot_bytes = _capture_window_screenshot(ctx.hwnd)
        if not screenshot_bytes:
            return None

        img = Image.open(io.BytesIO(screenshot_bytes))
        text = pytesseract.image_to_string(img, lang="eng")
        result.raw_text = _clean_text(text)
        return result

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Screenshot helper
# ---------------------------------------------------------------------------

def _capture_window_screenshot(hwnd: int) -> Optional[bytes]:
    """
    Capture a screenshot of the window identified by hwnd.
    Returns PNG bytes or None on failure.
    """
    try:
        import ctypes
        import ctypes.wintypes
        import mss
        import io

        user32 = ctypes.windll.user32

        # Get window rect
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))

        left = rect.left
        top = rect.top
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width <= 0 or height <= 0:
            return None

        with mss.mss() as sct:
            monitor = {"top": top, "left": left, "width": width, "height": height}
            screenshot = sct.grab(monitor)
            from PIL import Image
            import io
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_context(ctx: AppContext) -> ExtractedContext:
    """
    Main entry point. Tries each extraction method in order and returns
    the first successful result. Falls back gracefully at each step.

    Order:
      1. UIAutomation (best quality, structured)
      2. WinRT OCR (good quality, no dependencies on app internals)
      3. Tesseract OCR (last resort, requires Tesseract installed)
    """
    if not ctx.is_known():
        return ExtractedContext(
            app_type=ctx.app_type,
            error="No supported application detected in foreground.",
            extraction_method="none"
        )

    # Method 1: UIAutomation
    result = _extract_via_uiautomation(ctx)
    if result and result.has_content():
        return result

    # Method 2: WinRT OCR
    result = _extract_via_winrt_ocr(ctx)
    if result and result.has_content():
        return result

    # Method 3: Tesseract
    result = _extract_via_tesseract(ctx)
    if result and result.has_content():
        return result

    # Nothing worked
    return ExtractedContext(
        app_type=ctx.app_type,
        error="Could not extract text. Ensure the application window is visible and not minimized.",
        extraction_method="none"
    )
