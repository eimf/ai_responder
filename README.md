# AI Responder — Phase 1: Overlay UI

> **Platform:** Windows 10/11 64-bit  
> **Python:** 3.11+  
> **Framework:** PyQt6  

---

## What is in Phase 1?

Phase 1 delivers the complete **floating overlay UI** and **response panel**, fully functional with stub (placeholder) data. No AI calls or screen reading happen yet — those are added in Phase 2 and 3. This phase lets you:

- See and interact with the floating Teams/Outlook overlay in the top-right corner of your screen.
- Click either icon to trigger the response panel with simulated context and a simulated AI suggestion.
- Drag both the overlay and the response panel anywhere on screen.
- Open the Settings dialog and enter your Azure OpenAI credentials (saved locally for Phase 3).
- Use the system tray icon to show/hide the overlay or quit the app.

---

## Prerequisites

| Requirement | Details |
| :--- | :--- |
| **Python 3.11+** | Download from [python.org](https://www.python.org/downloads/). During install, check **"Add Python to PATH"**. |
| **pip** | Included with Python. |
| **Windows 10 64-bit** | Required for Phase 2+ (UIAutomation). Phase 1 runs on any OS. |

---

## Installation

### Step 1 — Download / Extract the project

Place the `ai_responder` folder anywhere on your machine, for example:

```
C:\Users\YourName\ai_responder\
```

### Step 2 — Run the setup script

Double-click `setup.bat` (or run it in a terminal):

```bat
setup.bat
```

This will:
1. Create a Python virtual environment inside the project folder (`venv\`).
2. Install `PyQt6` and all other required packages.

### Step 3 — Launch the app

Double-click `run.bat`:

```bat
run.bat
```

The overlay will appear in the **top-right corner** of your screen. A tray icon will also appear in the system tray (bottom-right of the taskbar).

---

## How to Use (Phase 1)

| Action | Result |
| :--- | :--- |
| **Click the purple "T" icon** | Opens the Teams response panel with stub data |
| **Click the blue "O" icon** | Opens the Outlook response panel with stub data |
| **Drag the overlay** | Click and drag anywhere on the dark pill background |
| **Click "Copy"** | Copies the suggestion to your clipboard |
| **Click "Regenerate"** | Re-triggers the stub (simulates a new AI call) |
| **Right-click the tray icon** | Shows the context menu (Hide/Show, Settings, Quit) |
| **Click "⚙ Settings"** | Opens the settings dialog to enter Azure OpenAI credentials |

---

## Entering Your Azure OpenAI Credentials

1. Right-click the tray icon → **Settings**.
2. In the **Azure OpenAI** tab, enter:
   - **Endpoint:** `https://YOUR_RESOURCE_NAME.openai.azure.com/`
   - **API Key:** Your key from Azure Portal → Azure OpenAI → Keys and Endpoint.
   - **Deployment:** The name of your deployed model (e.g. `gpt-4o`).
   - **API Version:** `2024-02-01` (or the latest stable version).
3. Click **Save**.

Credentials are stored in `%APPDATA%\AIResponder\settings.json` on your machine. They are never transmitted anywhere until Phase 3 is implemented.

---

## Project Structure

```
ai_responder/
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
├── setup.bat                   # First-time install script
├── run.bat                     # Launch script
├── README.md                   # This file
└── modules/
    ├── __init__.py
    ├── app_controller.py       # Wires all components together
    ├── overlay.py              # Floating overlay window (Teams + Outlook icons)
    ├── response_panel.py       # AI suggestion panel (context preview + reply)
    ├── settings_manager.py     # JSON-backed settings store
    ├── settings_dialog.py      # Settings UI dialog
    └── tray_icon.py            # System tray icon + context menu
```

---

## Roadmap

| Phase | Status | Description |
| :--- | :--- | :--- |
| **Phase 1** | ✅ Complete | Overlay UI, response panel, settings, tray icon |
| **Phase 2** | 🔜 Next | Context capture: UIAutomation for Outlook & Teams + OCR fallback |
| **Phase 3** | 🔜 Planned | Azure OpenAI integration: real AI suggestions |
| **Phase 4** | 🔜 Planned | Polish: keyboard shortcuts, PyInstaller `.exe` packaging |

---

## Troubleshooting

**"Python is not installed or not on PATH"**  
Re-run the Python installer and check **"Add Python to PATH"** during setup.

**The overlay does not appear**  
Check the system tray — the app may be running but the overlay was hidden. Right-click the tray icon → **Show Overlay**.

**The window is behind other windows**  
This can happen with some fullscreen applications. Minimise the fullscreen app and the overlay will reappear.

**PyQt6 install fails**  
Ensure you are running `setup.bat` with a Python 3.11+ installation. Try running `pip install PyQt6` manually in the activated virtual environment.
