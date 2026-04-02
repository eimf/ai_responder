"""
settings_manager.py
--------------------
Manages persistent application settings stored in a local JSON file.
Settings include Azure OpenAI credentials, model selection, and overlay position.
"""

import json
import os
from pathlib import Path


# Default location: %APPDATA%\AIResponder\settings.json  (Windows)
# Falls back to ~/.ai_responder/settings.json on other platforms
def _default_settings_path() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        base = Path(app_data) / "AIResponder"
    else:
        base = Path.home() / ".ai_responder"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


DEFAULTS = {
    # Azure OpenAI
    "azure_endpoint": "",           # e.g. https://YOUR_RESOURCE.openai.azure.com/
    "azure_api_key": "",
    "azure_deployment": "",         # e.g. gpt-4o
    "azure_api_version": "2024-02-01",

    # Fallback: standard OpenAI or Ollama
    "openai_base_url": "",          # leave blank for api.openai.com
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",

    # Which provider to use: "azure" | "openai"
    "provider": "azure",

    # UI
    "overlay_x": -1,                # -1 means auto-position (top-right)
    "overlay_y": -1,
    "theme": "dark",
}


class SettingsManager:
    """
    Simple JSON-backed settings store.

    Usage
    -----
    settings = SettingsManager()
    settings.get("azure_api_key")
    settings.set("azure_api_key", "sk-...")
    settings.save()
    """

    def __init__(self, path: Path = None):
        self._path = path or _default_settings_path()
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------ #
    #  Load / Save                                                          #
    # ------------------------------------------------------------------ #

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                # Merge with defaults so new keys are always present
                self._data = {**DEFAULTS, **stored}
            except (json.JSONDecodeError, OSError):
                self._data = dict(DEFAULTS)
        else:
            self._data = dict(DEFAULTS)

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            print(f"[SettingsManager] Could not save settings: {e}")

    # ------------------------------------------------------------------ #
    #  Get / Set                                                            #
    # ------------------------------------------------------------------ #

    def get(self, key: str, fallback=None):
        return self._data.get(key, fallback if fallback is not None else DEFAULTS.get(key))

    def set(self, key: str, value):
        self._data[key] = value

    def update(self, data: dict):
        self._data.update(data)

    def all(self) -> dict:
        return dict(self._data)

    # ------------------------------------------------------------------ #
    #  Convenience properties                                               #
    # ------------------------------------------------------------------ #

    @property
    def is_configured(self) -> bool:
        """Returns True if the user has entered enough credentials to make an AI call."""
        provider = self.get("provider")
        if provider == "azure":
            return bool(
                self.get("azure_endpoint")
                and self.get("azure_api_key")
                and self.get("azure_deployment")
            )
        else:
            return bool(self.get("openai_api_key"))
