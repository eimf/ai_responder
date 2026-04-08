# AI Responder

> **Platform:** Windows 10/11 64-bit  
> **Python:** 3.11+  
> **Framework:** PyQt6  
> **AI Backend:** LM Studio / OpenAI / Azure OpenAI  

---

## What It Does

AI Responder is a floating desktop overlay that reads the active conversation or email from Microsoft Teams, Cisco Jabber, or Microsoft Outlook, and generates a suggested reply using a local or cloud AI model.

- Click the **T** (Teams), **J** (Jabber), or **O** (Outlook) button on the overlay
- The app detects the foreground window, extracts the conversation/email text via UIAutomation
- Sends the context to your configured AI model
- Displays a suggested reply you can edit, copy, or regenerate

---

## Prerequisites

| Requirement | Details |
| :--- | :--- |
| **Python 3.11+** | [python.org](https://www.python.org/downloads/) — check "Add Python to PATH" during install |
| **LM Studio** (recommended) | [lmstudio.ai](https://lmstudio.ai) — local AI model server, no API key needed |
| **Windows 10/11 64-bit** | Required for UIAutomation text extraction |

---

## Installation

### Step 1 — Download the project

Place the `ai_responder` folder anywhere on your machine.

### Step 2 — Run setup

Double-click `setup.bat`. This creates a virtual environment and installs all dependencies.

### Step 3 — Configure AI model

See [AI Model Setup](#ai-model-setup) below.

### Step 4 — Launch

Double-click `run.bat`.

---

## AI Model Setup

### Option A: LM Studio (recommended — local, free, no internet needed)

1. Download and install [LM Studio](https://lmstudio.ai)
2. Download a model — recommended: `phi-3-mini-4k-instruct`
3. Go to the Developer tab (left sidebar) and click **Start Server**
4. Note the URL (typically `http://127.0.0.1:1234`)
5. In AI Responder: right-click tray icon → **Settings** → **OpenAI / Custom** tab:
   - **Base URL:** `http://127.0.0.1:1234/v1`
   - **API Key:** `lm-studio`
   - **Model:** the model name shown in LM Studio (e.g. `phi-3-mini-4k-instruct`)
6. Set **Active Provider** to `openai`
7. Click **Save**

### Option B: Azure OpenAI

1. Get your endpoint, API key, and deployment name from Azure Portal
2. In AI Responder: right-click tray icon → **Settings** → **Azure OpenAI** tab:
   - **Endpoint:** `https://YOUR_RESOURCE.openai.azure.com/`
   - **API Key:** your key
   - **Deployment:** your model deployment name (e.g. `gpt-4o`)
   - **API Version:** `2024-02-01`
3. Set **Active Provider** to `azure`
4. Click **Save**

### Option C: OpenAI API

1. Get an API key from [platform.openai.com](https://platform.openai.com)
2. In AI Responder: right-click tray icon → **Settings** → **OpenAI / Custom** tab:
   - **Base URL:** leave blank
   - **API Key:** your `sk-...` key
   - **Model:** `gpt-4o-mini`
3. Set **Active Provider** to `openai`
4. Click **Save**

---

## How to Use

| Action | Result |
| :--- | :--- |
| **Click "T"** | Reads the active Teams chat and generates a reply |
| **Click "J"** | Reads the active Jabber chat and generates a reply |
| **Click "O"** | Reads the active Outlook email and generates a reply |
| **Drag the overlay** | Click and drag the dark pill background |
| **Copy** | Copies the suggested reply to clipboard |
| **Regenerate** | Generates a new suggestion from the same context |
| **Right-click tray icon** | Show/Hide overlay, Settings, Quit |

### Tips for best results

- Have the target app (Teams/Jabber/Outlook) visible and in the foreground
- For Teams/Jabber: have the chat conversation open and scrolled to the latest messages
- For Outlook: have an email open or selected in the reading pane
- The window must not be minimized

---

## Project Structure

```
ai_responder/
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
├── setup.bat                   # First-time install script
├── run.bat                     # Daily launch script
├── README.md                   # This file
└── modules/
    ├── __init__.py
    ├── app_controller.py       # Main orchestrator
    ├── app_detector.py         # Foreground app detection (Teams/Jabber/Outlook)
    ├── text_extractor.py       # Text extraction via UIAutomation + OCR fallback
    ├── context_manager.py      # Detection + extraction pipeline
    ├── ai_engine.py            # AI integration (OpenAI/Azure/LM Studio)
    ├── overlay.py              # Floating overlay window (T/J/O buttons)
    ├── response_panel.py       # AI suggestion panel
    ├── settings_manager.py     # JSON-backed settings store
    ├── settings_dialog.py      # Settings UI dialog
    └── tray_icon.py            # System tray icon + context menu
```

---

## Architecture

### Text Extraction Pipeline

1. **App Detection** — Win32 API identifies the foreground window (process name + title)
2. **UIAutomation** (primary) — Walks the accessibility tree via comtypes IUIAutomation COM interface, extracting text from Name, ValuePattern, and TextPattern on each element
3. **UIAutomation lib** (fallback) — Uses the `uiautomation` Python library if comtypes types aren't generated
4. **Tesseract OCR** (last resort) — Screenshots the window and runs OCR

### AI Generation

- Uses the OpenAI SDK (`openai` package) which supports OpenAI, Azure OpenAI, and any OpenAI-compatible API (LM Studio, Ollama, etc.)
- Different system prompts per mode: casual for Teams/Jabber, professional for Outlook
- Handles reasoning models that put output in `reasoning_content` instead of `content`

### Settings

Stored at `%APPDATA%\AIResponder\settings.json`. Configurable via the Settings dialog (tray icon → Settings).

---

## Troubleshooting

**The overlay doesn't appear**  
Check the system tray — right-click the AI icon → Show Overlay.

**"No supported application detected"**  
Make sure Teams/Jabber/Outlook is the foreground window before clicking the overlay button.

**"Could not extract text"**  
The window must be visible (not minimized). Try clicking on the message body first.

**AI returns empty or weird responses**  
Check Settings — make sure the provider, API key, and model are configured correctly. For LM Studio, ensure the server is running.

**"The 'openai' package is not installed"**  
Run `setup.bat` again, or manually: `venv\Scripts\pip install openai`

---

## Development Phases

| Phase | Status | Description |
| :--- | :--- | :--- |
| **Phase 1** | ✅ Complete | Overlay UI, response panel, settings, tray icon |
| **Phase 2** | ✅ Complete | Context capture: UIAutomation for Teams, Jabber, Outlook + OCR fallback |
| **Phase 3** | ✅ Complete | AI integration: LM Studio / OpenAI / Azure OpenAI |
| **Phase 4** | 🔜 Planned | Polish: keyboard shortcuts, PyInstaller `.exe` packaging |
