"""Markdown renderer for ExamBuddy concise exam notes (v40).

Renders the seven-section structured payload into short revision markdown:

    # <Topic>
    ## Definition        (2-3 sentences)
    ## Working           (numbered steps)
    ## Advantages        (bullets)
    ## Disadvantages     (bullets)
    ## Applications      (bullets, **name** — detail)
    ## Example           (one worked/practical example)
    ## Quick Revision    (bullets)

Every heading is always emitted — the validator guarantees real content
behind each one, so there is no "Not Applicable" placeholder path.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.ai.notes_sanitizer import sanitize_note_text
from app.services.notes_engine.schema import (
    FIELD_ALIASES,
    LIST_FIELDS,
    MAX_LIST_ITEM_CHARS,
    MAX_TEXT_FIELD_CHARS,
    SECTION_ITEM_LIMITS,
    SECTION_ORDER,
    TEXT_FIELDS,
)

_LEADING_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def _first_key(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def _resolve(data: dict[str, Any], canonical: str) -> Any:
    return _first_key(data, *FIELD_ALIASES.get(canonical, (canonical,)))


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(p for p in (_as_text(item) for item in value) if p)
    if isinstance(value, dict):
        for key in ("text", "detail", "description", "content", "value"):
            if value.get(key):
                return str(value[key]).strip()
        return ""
    return str(value).strip()


def _as_bullets(value: Any) -> list[str]:
    """Flatten a model value into clean bullet strings (markers stripped)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [
            _LEADING_MARKER.sub("", line).strip()
            for line in value.splitlines()
            if line.strip()
        ]
    if isinstance(value, list):
        bullets: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                bullets.append(_LEADING_MARKER.sub("", item).strip())
            elif isinstance(item, dict):
                name = _as_text(item.get("name") or item.get("title") or item.get("point"))
                detail = _as_text(
                    item.get("detail")
                    or item.get("description")
                    or item.get("explanation")
                    or item.get("text")
                )
                if name and detail:
                    bullets.append(f"**{name}** — {detail}")
                elif name or detail:
                    bullets.append(name or detail)
        return bullets
    text = _as_text(value)
    return [text] if text else []


def _cap_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(".,;:— ") + "…"


def _dedupe(bullets: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for bullet in bullets:
        key = re.sub(r"[^a-z0-9]+", " ", bullet.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(bullet)
    return out


def normalize_concise_payload(data: dict[str, Any], *, topic: str = "") -> dict[str, Any]:
    """Map aliases onto canonical fields, dedupe, and cap lengths/counts.

    Over-long or over-numerous items are trimmed here rather than bounced back
    to the model — the spec's upper bounds are style, not correctness.
    """
    result: dict[str, Any] = {}

    resolved_topic = _as_text(_resolve(data, "topic")) or topic.strip()
    if resolved_topic:
        result["topic"] = _cap_text(resolved_topic, 120)

    for field in TEXT_FIELDS:
        if field == "topic":
            continue
        text = _as_text(_resolve(data, field))
        if text:
            result[field] = _cap_text(text, MAX_TEXT_FIELD_CHARS)

    for field in LIST_FIELDS:
        bullets = _dedupe(
            [_cap_text(b, MAX_LIST_ITEM_CHARS) for b in _as_bullets(_resolve(data, field)) if b]
        )
        _, max_items = SECTION_ITEM_LIMITS.get(field, (0, 8))
        if bullets:
            result[field] = bullets[:max_items]

    for passthrough in ("subject", "status"):
        if data.get(passthrough):
            result[passthrough] = data[passthrough]

    return result


def _append_paragraph(lines: list[str], heading: str, value: Any) -> None:
    lines.append(f"## {heading}")
    lines.append(_as_text(value))
    lines.append("")


def _append_numbered(lines: list[str], heading: str, value: Any) -> None:
    lines.append(f"## {heading}")
    for idx, step in enumerate(_as_bullets(value), start=1):
        lines.append(f"{idx}. {step}")
    lines.append("")


def _append_bullets(lines: list[str], heading: str, value: Any) -> None:
    lines.append(f"## {heading}")
    for bullet in _as_bullets(value):
        lines.append(f"- {bullet}")
    lines.append("")


def render_concise_markdown(data: dict[str, Any]) -> str:
    """Render the normalized seven-section payload into revision markdown."""
    topic = _as_text(data.get("topic")) or "Study Topic"
    lines: list[str] = [f"# {topic}", ""]

    renderers = {
        "definition": _append_paragraph,
        "working": _append_numbered,
        "advantages": _append_bullets,
        "disadvantages": _append_bullets,
        "applications": _append_bullets,
        "example": _append_paragraph,
        "quick_revision": _append_bullets,
    }
    for field, heading in SECTION_ORDER:
        renderers[field](lines, heading, data.get(field))

    return sanitize_note_text("\n".join(lines).strip())


def extract_concise_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Structured fields kept alongside the markdown for storage/API."""
    payload: dict[str, Any] = {}
    if data.get("topic"):
        payload["topic"] = data["topic"]
    for field, _ in SECTION_ORDER:
        if data.get(field) is not None:
            payload[field] = data[field]
    return payload


def build_summary(data: dict[str, Any]) -> str:
    """One-line summary stored next to the note (list previews use it)."""
    definition = _as_text(data.get("definition"))
    if not definition:
        return ""
    first_sentence = re.split(r"(?<=[.!?])\s+", definition)[0].strip()
    return _cap_text(first_sentence or definition, 240)
