"""Helpers for choosing which LLM provider to use."""

from __future__ import annotations

from typing import Any


def has_usable_api_key(value: str | None) -> bool:
    key = (value or "").strip()
    if len(key) < 20:
        return False
    lower = key.lower()
    if lower.startswith("your-") or "replace" in lower or "xxx" in lower:
        return False
    return True


def resolve_provider_order(settings: Any) -> list[str]:
    """
    Return providers that have usable keys, preferred first.

    If the preferred provider has no key, fall back to whichever key exists
    (e.g. AI_PROVIDER=openai but only GEMINI_API_KEY is set).
    """
    available: list[str] = []
    if has_usable_api_key(getattr(settings, "gemini_api_key", "")):
        available.append("gemini")
    if has_usable_api_key(getattr(settings, "openai_api_key", "")):
        available.append("openai")
    if not available:
        return []

    preferred = getattr(settings, "ai_provider", None) or "gemini"
    if preferred in available:
        return [preferred, *[name for name in available if name != preferred]]
    return available
