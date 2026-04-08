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
