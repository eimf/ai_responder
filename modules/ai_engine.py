"""
ai_engine.py
------------
AI integration module. Sends extracted context to OpenAI (or Azure OpenAI)
and returns a suggested reply.

Supports two providers:
  - "azure"  → Azure OpenAI Service
  - "openai" → Standard OpenAI API (also works with Ollama / LM Studio)
"""

import logging
from typing import Optional

log = logging.getLogger("AIEngine")

# ---------------------------------------------------------------------------
# System prompts per mode
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS = {
    "teams": (
        "You are a helpful assistant that drafts chat replies for Microsoft Teams. "
        "The user will provide a conversation thread from Teams. "
        "Write a concise, friendly, professional reply in English. "
        "Match the tone of the conversation — if it's casual, be casual; "
        "if it's formal, be formal. Keep it brief and to the point. "
        "Do NOT include greetings like 'Hi' unless the conversation style uses them. "
        "Output ONLY the reply text, nothing else."
    ),
    "jabber": (
        "You are a helpful assistant that drafts chat replies for Cisco Jabber. "
        "The user will provide a conversation thread from Jabber. "
        "Write a concise, friendly, professional reply in English. "
        "Match the tone of the conversation — if it's casual, be casual; "
        "if it's formal, be formal. Keep it brief and to the point. "
        "Do NOT include greetings like 'Hi' unless the conversation style uses them. "
        "Output ONLY the reply text, nothing else."
    ),
    "outlook": (
        "You are a helpful assistant that drafts email replies for Microsoft Outlook. "
        "The user will provide an email thread or a single email. "
        "Write a professional, well-structured email reply in English. "
        "Include an appropriate greeting and sign-off. "
        "Be clear, polite, and concise. "
        "Output ONLY the email reply text, nothing else."
    ),
}


# ---------------------------------------------------------------------------
# Client creation
# ---------------------------------------------------------------------------

def _create_client(settings):
    """
    Create an OpenAI client based on the configured provider.
    Returns (client, model_name) or raises an exception.
    """
    try:
        from openai import OpenAI, AzureOpenAI
    except ImportError:
        raise RuntimeError(
            "The 'openai' package is not installed.\n"
            "Run: pip install openai"
        )

    provider = settings.get("provider", "azure")

    if provider == "azure":
        endpoint = settings.get("azure_endpoint", "").strip()
        api_key = settings.get("azure_api_key", "").strip()
        deployment = settings.get("azure_deployment", "").strip()
        api_version = settings.get("azure_api_version", "2024-02-01").strip()

        if not endpoint or not api_key or not deployment:
            raise RuntimeError(
                "Azure OpenAI credentials not configured.\n"
                "Right-click the tray icon → Settings → Azure OpenAI tab."
            )

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        return client, deployment

    else:  # "openai" or custom
        api_key = settings.get("openai_api_key", "").strip()
        model = settings.get("openai_model", "gpt-4o-mini").strip()
        base_url = settings.get("openai_base_url", "").strip() or None

        if not api_key:
            raise RuntimeError(
                "OpenAI API key not configured.\n"
                "Right-click the tray icon → Settings → OpenAI / Custom tab."
            )

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        return client, model or "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate_suggestion(context_text: str, mode: str, settings) -> str:
    """
    Generate an AI-powered reply suggestion.

    Args:
        context_text: The extracted conversation/email context.
        mode: "teams", "jabber", or "outlook".
        settings: SettingsManager instance with API credentials.

    Returns:
        The suggested reply text, or an error message string.
    """
    if not context_text or not context_text.strip():
        return "No context available to generate a suggestion."

    system_prompt = _SYSTEM_PROMPTS.get(mode, _SYSTEM_PROMPTS["teams"])

    try:
        client, model = _create_client(settings)
        log.info(f"Calling AI: provider={settings.get('provider')} model={model} "
                 f"context_len={len(context_text)}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_text},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        reply = response.choices[0].message.content.strip()
        log.info(f"AI response received: {len(reply)} chars")
        return reply

    except RuntimeError as e:
        # Config errors — show to user as-is
        log.warning(f"AI config error: {e}")
        return str(e)

    except Exception as e:
        log.error(f"AI call failed: {e}", exc_info=True)
        error_str = str(e)
        # Provide user-friendly messages for common errors
        if "401" in error_str or "authentication" in error_str.lower():
            return "Authentication failed. Check your API key in Settings."
        if "404" in error_str:
            return "Model or deployment not found. Check your model/deployment name in Settings."
        if "429" in error_str or "rate" in error_str.lower():
            return "Rate limit exceeded. Wait a moment and try again."
        return f"AI call failed: {error_str}"
