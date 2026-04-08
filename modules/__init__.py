# AI Responder — modules package
#
# Phase 1 modules:
#   overlay           — Floating always-on-top overlay window (Teams, Outlook, Jabber)
#   response_panel    — Suggestion popup with Copy / Regenerate
#   settings_manager  — Persistent settings (API key, model, position)
#   settings_dialog   — Settings UI dialog
#   tray_icon         — System tray icon with right-click menu
#   app_controller    — Main orchestrator wiring all modules together
#
# Phase 2 modules:
#   app_detector      — Detects foreground app (Teams / Outlook / Jabber) via Win32
#   text_extractor    — Extracts text via UIAutomation or Tesseract OCR
#   context_manager   — Orchestrates detection + extraction pipeline
