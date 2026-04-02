# AI Responder — modules package
#
# Phase 1 modules:
#   overlay           — Floating always-on-top overlay window
#   response_panel    — Suggestion popup with Copy / Regenerate
#   settings_manager  — Persistent settings (API key, model, position)
#   settings_dialog   — Settings UI dialog
#   tray_icon         — System tray icon with right-click menu
#   app_controller    — Main orchestrator wiring all modules together
#
# Phase 2 modules:
#   app_detector      — Detects foreground app (Teams / Outlook) via Win32
#   text_extractor    — Extracts text via UIAutomation, WinRT OCR, or Tesseract
#   context_manager   — Orchestrates detection + extraction pipeline
