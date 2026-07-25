"""
UTF-8 text cleaning for PDF extraction and topic names.

Removes OCR/encoding garbage so corrupted strings never reach Gemini.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from urllib.parse import unquote

logger = logging.getLogger("exambuddy.text_sanitizer")

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200d\ufeff]")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_NL = re.compile(r"\n{3,}")
# Lines that are mostly punctuation / symbols (PDF stream garbage).
_GARBAGE_LINE = re.compile(r"^[\W\d_%]{8,}$")
# High ratio of non-letter characters → corrupted topic / OCR noise.
_URL_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")
_LETTER = re.compile(r"[A-Za-z]")


def ensure_utf8_text(value: str | bytes | None) -> str:
    """Normalize any inbound text to a clean Unicode string."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16", "latin-1", "cp1252"):
            try:
                text = value.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)

    # Fix mojibake where UTF-8 was decoded as latin-1.
    if "Ã" in text or "Â" in text:
        try:
            repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            if repaired and _LETTER.search(repaired):
                text = repaired
        except Exception:
            pass

    text = unicodedata.normalize("NFKC", text)
    # Decode URL-encoded fragments (%20, %23, …) repeatedly (max 2 passes).
    for _ in range(2):
        if "%" not in text:
            break
        decoded = unquote(text, encoding="utf-8", errors="replace")
        if decoded == text:
            break
        text = decoded
    return text


def clean_extracted_text(raw: str | bytes | None) -> str:
    """Clean PDF/OCR extracted text for analysis (never used as notes body)."""
    text = ensure_utf8_text(raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _MULTI_SPACE.sub(" ", raw_line.strip())
        if not line:
            lines.append("")
            continue
        if _GARBAGE_LINE.match(line):
            continue
        # Drop lines with almost no letters (binary / stream junk).
        letters = len(_LETTER.findall(line))
        if len(line) >= 10 and letters / max(len(line), 1) < 0.25:
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = _MULTI_NL.sub("\n\n", cleaned).strip()
    logger.debug(
        "clean_extracted_text chars_in=%d chars_out=%d",
        len(ensure_utf8_text(raw)),
        len(cleaned),
    )
    return cleaned


def looks_like_corrupted_topic(topic: str | None) -> bool:
    """True when a topic name is encoding/OCR garbage and must not go to Gemini."""
    name = ensure_utf8_text(topic).strip()
    if not name:
        return True
    if name.upper() == "UNKNOWN_TOPIC":
        return True
    if len(name) < 2:
        return True
    if _URL_ESCAPE.search(name):
        return True
    letters = len(_LETTER.findall(name))
    if letters < 2:
        return True
    # Mostly symbols / digits / punctuation
    if letters / max(len(name), 1) < 0.4:
        return True
    # Too many non-word clusters
    weird = sum(1 for ch in name if not (ch.isalnum() or ch.isspace() or ch in "-_/&().,:+"))
    if weird / max(len(name), 1) > 0.35:
        return True
    return False


def sanitize_topic_name(topic: str | None) -> str:
    """Clean a topic name; returns empty string if corrupted."""
    name = ensure_utf8_text(topic).strip()
    name = _CONTROL.sub("", name)
    name = _MULTI_SPACE.sub(" ", name)
    if looks_like_corrupted_topic(name):
        logger.warning("Rejected corrupted topic name=%r", name[:80])
        return ""
    return name
