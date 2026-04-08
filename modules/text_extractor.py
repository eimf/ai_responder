"""
text_extractor.py
-----------------
Extracts visible text content from Microsoft Teams, Outlook, and Cisco Jabber.

Strategy (in order of preference):
  1. UIAutomation tree traversal (comtypes direct, then uiautomation lib)
  2. Tesseract OCR (pytesseract + mss screenshot)

Each extractor returns an ExtractedContext object with the raw text,
source app, and extraction method used.
"""

import re
import sys
import logging
from dataclasses import dataclass, field
from typing import Optional

from .app_detector import AppContext, APP_TEAMS, APP_OUTLOOK, APP_JABBER

log = logging.getLogger("TextExtractor")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ExtractedContext:
    """Holds the text extracted from the active application window."""
    app_type: str = ""
    subject: str = ""           # Email subject (Outlook only)
    sender: str = ""            # Sender name/email
    body: str = ""              # Main content body / last message
    thread: str = ""            # Thread / conversation history
    extraction_method: str = "" # "uiautomation", "tesseract", "none"
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
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = text.strip()
    if len(text) > max_chars:
        text = "...[truncated]\n" + text[-max_chars:]
    return text


# ---------------------------------------------------------------------------
# UI chrome filter
# ---------------------------------------------------------------------------

_CHROME_EXACT = {
    # Outlook ribbon / nav
    "File", "Home", "Send / Receive", "Folder", "View", "Help",
    "New Email", "New Items", "Delete", "Archive", "Reply",
    "Reply All", "Forward", "Move", "Rules", "Tags",
    "Inbox", "Sent Items", "Drafts", "Junk Email", "Deleted Items",
    "Calendar", "Contacts", "Tasks", "Notes",
    "Tell me what you want to do", "Search",
    "Minimize", "Maximize", "Close", "Restore",
    # Teams nav
    "Chat", "Teams", "Activity", "Files", "Apps",
    "Type a message", "New conversation",
    # Jabber nav
    "Contacts", "Chats", "Calls", "Meetings", "Voicemail",
    "Search or Call", "Send a message",
}


def _is_ui_chrome(text: str) -> bool:
    """Return True if the text looks like UI chrome rather than content."""
    stripped = text.strip()
    if stripped in _CHROME_EXACT:
        return True
    if len(stripped) <= 2:
        return True
    # Short title-case single words are likely menu items
    if re.match(r'^[\w\s]{1,15}$', stripped) and stripped.istitle() and len(stripped) < 8:
        return True
    return False


# ---------------------------------------------------------------------------
# Win32 helpers
# ---------------------------------------------------------------------------

def _ensure_window_foreground(hwnd: int) -> bool:
    """Bring the target window to the foreground and ensure it's not minimized."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        import time
        time.sleep(0.15)
        return True
    except Exception as e:
        log.debug(f"Could not bring window to foreground: {e}")
        return False


# ===========================================================================
# Method 1: UIAutomation — comtypes IUIAutomation (primary)
# ===========================================================================

def _extract_via_uiautomation(ctx: AppContext) -> Optional[ExtractedContext]:
    """
    Use comtypes IUIAutomation COM interface to walk the accessibility tree.
    Falls back to the uiautomation Python library if comtypes types are
    not generated yet.
    """
    result = ExtractedContext(
        app_type=ctx.app_type,
        extraction_method="uiautomation"
    )

    try:
        import comtypes
        import comtypes.client

        try:
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        except OSError:
            pass

        uia = comtypes.CoCreateInstance(
            comtypes.GUID("{FF48DBA4-60EF-4201-AA87-54103EEF594E}"),
            interface=comtypes.gen._944DE083_8FB8_45CF_BCB7_C477ACB2F897_0_1_0.IUIAutomation,
        )
    except Exception:
        log.debug("comtypes UIA not available, trying uiautomation library")
        return _extract_via_uiautomation_lib(ctx)

    try:
        root = uia.ElementFromHandle(ctx.hwnd)
        if not root:
            return None

        if ctx.is_teams():
            return _extract_teams_comtypes(uia, root, result)
        elif ctx.is_jabber():
            return _extract_jabber_comtypes(uia, root, result)
        elif ctx.is_outlook():
            return _extract_outlook_comtypes(uia, root, result)

    except Exception as e:
        log.error(f"comtypes UIA extraction failed: {e}", exc_info=True)
        result.error = str(e)
        fallback = _extract_via_uiautomation_lib(ctx)
        if fallback and fallback.has_content():
            return fallback
        return result

    return None


# ---------------------------------------------------------------------------
# comtypes helpers
# ---------------------------------------------------------------------------

def _get_element_name(element) -> str:
    try:
        name = element.CurrentName
        return name if name else ""
    except Exception:
        return ""


def _get_element_value(uia, element) -> str:
    try:
        UIA_ValuePatternId = 10002
        pattern = element.GetCurrentPattern(UIA_ValuePatternId)
        if pattern:
            from comtypes import cast
            val_iface = cast(
                pattern,
                comtypes.gen._944DE083_8FB8_45CF_BCB7_C477ACB2F897_0_1_0.IUIAutomationValuePattern,
            )
            return val_iface.CurrentValue or ""
    except Exception:
        pass
    return ""


def _get_element_text_range(uia, element) -> str:
    try:
        UIA_TextPatternId = 10014
        pattern = element.GetCurrentPattern(UIA_TextPatternId)
        if pattern:
            from comtypes import cast
            text_iface = cast(
                pattern,
                comtypes.gen._944DE083_8FB8_45CF_BCB7_C477ACB2F897_0_1_0.IUIAutomationTextPattern,
            )
            doc_range = text_iface.DocumentRange
            if doc_range:
                return doc_range.GetText(8000) or ""
    except Exception:
        pass
    return ""


def _get_element_control_type(element) -> int:
    """Return the UIA ControlTypeId for the element (0 on failure)."""
    try:
        return element.CurrentControlType
    except Exception:
        return 0


def _walk_tree_comtypes(uia, element, max_items=300, max_depth=15):
    """Walk the UIA tree and collect text from Name, Value, and TextPattern."""
    texts = []
    seen = set()
    tree_walker = uia.RawViewWalker

    def _collect(el, depth):
        if len(texts) >= max_items or depth > max_depth:
            return

        name = _get_element_name(el)
        if name and len(name) > 1 and name not in seen:
            seen.add(name)
            texts.append(name)

        value = _get_element_value(uia, el)
        if value and len(value) > 1 and value not in seen:
            seen.add(value)
            texts.append(value)

        text_content = _get_element_text_range(uia, el)
        if text_content and len(text_content) > 1 and text_content not in seen:
            seen.add(text_content)
            texts.append(text_content)

        try:
            child = tree_walker.GetFirstChildElement(el)
            while child:
                _collect(child, depth + 1)
                try:
                    child = tree_walker.GetNextSiblingElement(child)
                except Exception:
                    break
        except Exception:
            pass

    _collect(element, 0)
    return texts


def _walk_tree_comtypes_typed(uia, element, max_items=400, max_depth=18):
    """
    Walk the UIA tree and return a list of (control_type_id, text) tuples.
    Useful for chat apps where we want to distinguish message list items
    from other controls.
    """
    items = []
    seen = set()
    tree_walker = uia.RawViewWalker

    def _collect(el, depth):
        if len(items) >= max_items or depth > max_depth:
            return

        ct = _get_element_control_type(el)

        for getter in (_get_element_name, lambda e: _get_element_value(uia, e),
                       lambda e: _get_element_text_range(uia, e)):
            text = getter(el)
            if text and len(text) > 1 and text not in seen:
                seen.add(text)
                items.append((ct, text))

        try:
            child = tree_walker.GetFirstChildElement(el)
            while child:
                _collect(child, depth + 1)
                try:
                    child = tree_walker.GetNextSiblingElement(child)
                except Exception:
                    break
        except Exception:
            pass

    _collect(element, 0)
    return items


# ---------------------------------------------------------------------------
# Teams extraction (comtypes) — highest priority
# ---------------------------------------------------------------------------

# UIA ControlType IDs we care about for chat messages
_UIA_CT_LIST_ITEM = 50007
_UIA_CT_TEXT = 50020
_UIA_CT_EDIT = 50004
_UIA_CT_GROUP = 50026
_UIA_CT_LIST = 50008
_UIA_CT_DOCUMENT = 50030


def _extract_teams_comtypes(uia, root, result: ExtractedContext) -> ExtractedContext:
    """
    Extract chat messages from Microsoft Teams.

    We collect all text from the UIA tree and filter out UI chrome.
    No control-type gating — Teams uses varying control types across
    versions (classic vs new) so we accept anything that looks like content.
    """
    log.debug("Teams extraction via comtypes UIA")

    typed_items = _walk_tree_comtypes_typed(uia, root, max_items=500, max_depth=20)
    log.debug(f"Teams walk collected {len(typed_items)} typed fragments")

    if not typed_items:
        return result

    # Accept all non-chrome text longer than 3 chars regardless of control type
    message_texts = []
    for _ct, text in typed_items:
        if len(text) > 3 and not _is_ui_chrome(text):
            message_texts.append(text)

    if message_texts:
        # Keep the last 40 messages for context
        thread_texts = message_texts[-40:]
        result.thread = _clean_text("\n".join(thread_texts))
        result.body = thread_texts[-1] if thread_texts else ""
        log.debug(f"Teams: extracted {len(thread_texts)} messages, "
                  f"thread_len={len(result.thread)}")
    else:
        # Absolute fallback: dump everything
        all_text = [t for _, t in typed_items if len(t) > 3]
        result.raw_text = _clean_text("\n".join(all_text))
        log.debug(f"Teams: fallback raw_text len={len(result.raw_text)}")

    return result


# ---------------------------------------------------------------------------
# Jabber extraction (comtypes)
# ---------------------------------------------------------------------------

def _extract_jabber_comtypes(uia, root, result: ExtractedContext) -> ExtractedContext:
    """
    Extract chat messages from Cisco Jabber.
    Same approach as Teams — accept all non-chrome text, no control-type gating.
    """
    log.debug("Jabber extraction via comtypes UIA")

    typed_items = _walk_tree_comtypes_typed(uia, root, max_items=500, max_depth=20)
    log.debug(f"Jabber walk collected {len(typed_items)} typed fragments")

    if not typed_items:
        return result

    message_texts = []
    for _ct, text in typed_items:
        if len(text) > 3 and not _is_ui_chrome(text):
            message_texts.append(text)

    if message_texts:
        thread_texts = message_texts[-40:]
        result.thread = _clean_text("\n".join(thread_texts))
        result.body = thread_texts[-1] if thread_texts else ""
        log.debug(f"Jabber: extracted {len(thread_texts)} messages")
    else:
        all_text = [t for _, t in typed_items if len(t) > 3]
        result.raw_text = _clean_text("\n".join(all_text))
        log.debug(f"Jabber: fallback raw_text len={len(result.raw_text)}")

    return result


# ---------------------------------------------------------------------------
# Outlook extraction (comtypes)
# ---------------------------------------------------------------------------

def _extract_outlook_comtypes(uia, root, result: ExtractedContext) -> ExtractedContext:
    """
    Extract email content from Outlook using comtypes IUIAutomation.
    """
    log.debug("Outlook extraction via comtypes UIA")

    all_texts = _walk_tree_comtypes(uia, root, max_items=400, max_depth=18)
    log.debug(f"Outlook comtypes walk collected {len(all_texts)} text fragments")

    if not all_texts:
        return result

    body_candidates = []
    subject_found = False

    for text in all_texts:
        text_lower = text.lower().strip()

        if not subject_found:
            if any(text_lower.startswith(p) for p in ["re:", "fw:", "fwd:"]):
                result.subject = text.strip()
                subject_found = True
                continue

        if not result.sender and "@" in text and "." in text:
            email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', text)
            if email_match:
                result.sender = text.strip()
                continue

        if len(text) > 3 and not _is_ui_chrome(text):
            body_candidates.append(text)

    if body_candidates:
        body_candidates.sort(key=len, reverse=True)
        result.body = _clean_text(body_candidates[0])
        if len(body_candidates) > 1:
            result.raw_text = _clean_text("\n".join(body_candidates[:30]))

    if not result.body and all_texts:
        result.raw_text = _clean_text("\n".join(all_texts))

    return result


# ===========================================================================
# Fallback: uiautomation Python library
# ===========================================================================

def _extract_via_uiautomation_lib(ctx: AppContext) -> Optional[ExtractedContext]:
    """Fallback using the uiautomation Python library."""
    try:
        import uiautomation as auto
    except ImportError:
        return None

    result = ExtractedContext(
        app_type=ctx.app_type,
        extraction_method="uiautomation"
    )

    try:
        root = auto.ControlFromHandle(ctx.hwnd)
        if not root:
            return None

        if ctx.is_teams():
            return _extract_teams_uia_lib(root, result)
        elif ctx.is_jabber():
            return _extract_jabber_uia_lib(root, result)
        elif ctx.is_outlook():
            return _extract_outlook_uia_lib(root, result)

    except Exception as e:
        log.error(f"uiautomation lib extraction failed: {e}", exc_info=True)
        result.error = str(e)
        return result

    return None


def _collect_all_text_deep(root, max_items: int = 300) -> list:
    """Walk the UIAutomation tree deeply and collect text from Name,
    ValuePattern, and TextPattern on every element."""
    texts = []
    seen = set()
    count = [0]

    def walk(ctrl, depth=0):
        if count[0] >= max_items or depth > 16:
            return

        name = ctrl.Name or ""
        if name and len(name) > 1 and name not in seen:
            seen.add(name)
            texts.append(name)
            count[0] += 1

        try:
            vp = ctrl.GetValuePattern()
            if vp:
                val = vp.Value or ""
                if val and len(val) > 1 and val not in seen:
                    seen.add(val)
                    texts.append(val)
                    count[0] += 1
        except Exception:
            pass

        try:
            tp = ctrl.GetTextPattern()
            if tp:
                text = tp.DocumentRange.GetText(-1) or ""
                if text and len(text) > 1 and text not in seen:
                    seen.add(text)
                    texts.append(text)
                    count[0] += 1
        except Exception:
            pass

        for child in ctrl.GetChildren():
            walk(child, depth + 1)

    walk(root)
    return texts


# --- Teams (uiautomation lib) ---

def _extract_teams_uia_lib(root, result: ExtractedContext) -> ExtractedContext:
    """Extract chat content from Teams using uiautomation library."""
    import uiautomation as auto

    message_texts = []

    # Try ListControl at increasing depths
    for search_depth in [8, 12, 16]:
        list_ctrl = root.ListControl(searchDepth=search_depth)
        if list_ctrl.Exists(0, 0):
            items = list_ctrl.GetChildren()
            for item in items[-30:]:
                text = item.Name or ""
                if text and len(text) > 3 and not _is_ui_chrome(text):
                    message_texts.append(text)
            if message_texts:
                break

    # Try GroupControl
    if not message_texts:
        group = root.GroupControl(searchDepth=12)
        if group.Exists(0, 0):
            for child in group.GetChildren():
                text = child.Name or ""
                if text and len(text) > 3 and not _is_ui_chrome(text):
                    message_texts.append(text)

    # Deep walk fallback — collect all text and treat as messages
    if not message_texts:
        all_text = _collect_all_text_deep(root)
        message_texts = [t for t in all_text if len(t) > 5 and not _is_ui_chrome(t)]

    if message_texts:
        thread_texts = message_texts[-40:]
        result.thread = _clean_text("\n".join(thread_texts))
        result.body = thread_texts[-1]

    return result


# --- Jabber (uiautomation lib) ---

def _extract_jabber_uia_lib(root, result: ExtractedContext) -> ExtractedContext:
    """Extract chat content from Cisco Jabber using uiautomation library."""
    import uiautomation as auto

    message_texts = []

    # Jabber chat messages are typically in a List or a rich-text area
    for search_depth in [8, 12, 16]:
        list_ctrl = root.ListControl(searchDepth=search_depth)
        if list_ctrl.Exists(0, 0):
            items = list_ctrl.GetChildren()
            for item in items[-30:]:
                text = item.Name or ""
                if text and len(text) > 3 and not _is_ui_chrome(text):
                    message_texts.append(text)
            if message_texts:
                break

    # Try Document control (Jabber sometimes uses a rich-text pane)
    if not message_texts:
        doc = root.DocumentControl(searchDepth=12)
        if doc.Exists(0, 0):
            try:
                tp = doc.GetTextPattern()
                if tp:
                    text = tp.DocumentRange.GetText(-1) or ""
                    if text and len(text) > 3:
                        message_texts.append(text)
            except Exception:
                pass
            if not message_texts:
                name = doc.Name or ""
                if name and len(name) > 3:
                    message_texts.append(name)

    # Deep walk fallback — collect all text and treat as messages
    if not message_texts:
        all_text = _collect_all_text_deep(root)
        message_texts = [t for t in all_text if len(t) > 5 and not _is_ui_chrome(t)]

    if message_texts:
        thread_texts = message_texts[-40:]
        result.thread = _clean_text("\n".join(thread_texts))
        result.body = thread_texts[-1]

    return result


# --- Outlook (uiautomation lib) ---

def _extract_outlook_uia_lib(root, result: ExtractedContext) -> ExtractedContext:
    """Extract email content from Outlook using uiautomation library."""
    import uiautomation as auto

    body_text = ""
    doc = root.DocumentControl(searchDepth=12)
    if doc.Exists(0, 0):
        try:
            pattern = doc.GetTextPattern()
            if pattern:
                body_text = pattern.DocumentRange.GetText(-1) or ""
        except Exception:
            pass

        if not body_text:
            try:
                pattern = doc.GetValuePattern()
                if pattern:
                    body_text = pattern.Value or ""
            except Exception:
                pass

        if not body_text:
            body_text = doc.Name or ""
        if not body_text:
            child_texts = []
            for c in doc.GetChildren():
                n = c.Name or ""
                if n and len(n) > 2:
                    child_texts.append(n)
            body_text = " ".join(child_texts)

    if body_text:
        result.body = _clean_text(body_text)

    for ctrl in root.GetChildren():
        name = ctrl.Name or ""
        name_lower = name.lower()
        if any(p in name_lower for p in ["re:", "fw:", "fwd:"]):
            result.subject = name
            break

    if not result.body:
        all_text = _collect_all_text_deep(root)
        if all_text:
            result.raw_text = _clean_text("\n".join(all_text))

    return result


# ===========================================================================
# Method 2: Tesseract OCR (fallback)
# ===========================================================================

def _extract_via_tesseract(ctx: AppContext) -> Optional[ExtractedContext]:
    """Capture a screenshot and run Tesseract OCR on it."""
    try:
        import pytesseract
        from PIL import Image
        import io

        result = ExtractedContext(
            app_type=ctx.app_type,
            extraction_method="tesseract"
        )

        _ensure_window_foreground(ctx.hwnd)

        screenshot_bytes = _capture_window_screenshot(ctx.hwnd)
        if not screenshot_bytes:
            log.debug("Tesseract: screenshot capture returned None")
            return None

        img = Image.open(io.BytesIO(screenshot_bytes))
        log.debug(f"Tesseract: captured image size={img.size}")

        img = img.convert("L")  # grayscale for better OCR
        text = pytesseract.image_to_string(img, lang="eng")
        log.debug(f"Tesseract: extracted {len(text)} chars")
        result.raw_text = _clean_text(text)
        return result

    except Exception as e:
        log.error(f"Tesseract extraction failed: {e}", exc_info=True)
        return None


# ===========================================================================
# Screenshot helper
# ===========================================================================

def _capture_window_screenshot(hwnd: int) -> Optional[bytes]:
    """Capture a screenshot of the window identified by hwnd.
    Uses DPI-aware window rect and validates dimensions."""
    try:
        import ctypes
        import ctypes.wintypes
        import mss
        from PIL import Image
        import io

        user32 = ctypes.windll.user32

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

        if not user32.IsWindowVisible(hwnd):
            log.debug("Screenshot: window is not visible")
            return None
        if user32.IsIconic(hwnd):
            log.debug("Screenshot: window is minimized")
            return None

        rect = ctypes.wintypes.RECT()
        try:
            DWMWA_EXTENDED_FRAME_BOUNDS = 9
            ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect), ctypes.sizeof(rect)
            )
        except Exception:
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

        left, top = rect.left, rect.top
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        log.debug(f"Screenshot: rect=({left},{top},{width}x{height})")

        if width <= 50 or height <= 50:
            log.debug("Screenshot: window too small")
            return None

        with mss.mss() as sct:
            monitor = {"top": top, "left": left, "width": width, "height": height}
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            log.debug(f"Screenshot: captured {img.size[0]}x{img.size[1]} image")
            return buf.getvalue()

    except Exception as e:
        log.error(f"Screenshot capture failed: {e}", exc_info=True)
        return None


# ===========================================================================
# Main entry point
# ===========================================================================

def extract_context(ctx: AppContext) -> ExtractedContext:
    """
    Tries each extraction method in order and returns the first success.

    Order:
      1. UIAutomation (comtypes direct → uiautomation lib fallback)
      2. Tesseract OCR
    """
    if not ctx.is_known():
        return ExtractedContext(
            app_type=ctx.app_type,
            error="No supported application detected in foreground.",
            extraction_method="none"
        )

    log.info(f"Starting extraction for {ctx.app_type} "
             f"window={ctx.window_title!r} process={ctx.process_name!r}")

    # Method 1: UIAutomation
    try:
        result = _extract_via_uiautomation(ctx)
        if result and result.has_content():
            log.info(f"UIAutomation succeeded: body_len={len(result.body)} "
                     f"thread_len={len(result.thread)} raw_len={len(result.raw_text)}")
            return result
        log.debug("UIAutomation returned no content, trying Tesseract")
    except Exception as e:
        log.error(f"UIAutomation failed: {e}", exc_info=True)

    # Method 2: Tesseract
    try:
        result = _extract_via_tesseract(ctx)
        if result and result.has_content():
            log.info(f"Tesseract succeeded: raw_len={len(result.raw_text)}")
            return result
        log.debug("Tesseract returned no content")
    except Exception as e:
        log.error(f"Tesseract failed: {e}", exc_info=True)

    return ExtractedContext(
        app_type=ctx.app_type,
        error="Could not extract text. Ensure the application window is visible "
              "and an email or chat is selected/open.",
        extraction_method="none"
    )
