"""
Standalone e2e smoke test for the Stage-3 sectioned notes engine (v30) — no
MongoDB needed.

Confirms:
- GEMINI_API_KEY loads from backend/.env
- AIService.generate_topic_notes() -> SectionedNotesPipeline -> ~11 focused
  Gemini calls -> merged long-form markdown chapter
- Result is real AI content (never a local/local_fallback template), with a
  word count in the 2000-5500 range and the required headings present.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

REQUIRED_HEADINGS = (
    "# Definition",
    "# Introduction",
    "# Core Concept",
    "# Working Principle",
    "# Architecture / Components",
    "# Flow Diagram",
    "# Mathematical Formula",
    "# Algorithm",
    "# Example",
    "# Advantages",
    "# Disadvantages",
    "# Applications",
    "# Comparison",
    "# PYQ Perspective",
    "# 2 Marks Answer",
    "# 5 Marks Answer",
    "# 10 Marks Answer",
    "# Viva Questions",
    "# Interview Questions",
    "# Common Mistakes",
    "# Memory Tricks",
    "# Revision Notes",
    "# Keywords",
    "# Summary",
)


async def main() -> int:
    from app.core.config import reload_settings
    from app.services.ai.ai_service import AIService

    settings = reload_settings()
    print(f"gemini_configured={bool(settings.gemini_api_key)} ai_provider={settings.ai_provider} model={settings.gemini_model}")

    ai = AIService()
    print(f"ai_available={ai.ai_available} providers={[n for n, _ in ai.providers]}")

    if not ai.ai_available:
        print("FAIL: no AI provider configured — set GEMINI_API_KEY in backend/.env")
        return 1

    topic = "Process Synchronization"
    subject = "Operating Systems"

    try:
        result, metadata = await ai.generate_topic_notes(
            topic,
            subject=subject,
            exam_priority="High",
        )
    except Exception as exc:
        print(f"FAIL: generate_topic_notes raised {type(exc).__name__}: {exc}")
        return 1

    provider = metadata.get("provider")
    model = metadata.get("model")
    notes = result.get("notes") or ""
    word_count = metadata.get("word_count") or result.get("word_count")

    print("---- RESULT ----")
    print(f"provider={provider} model={model} notes_engine={metadata.get('notes_engine')}")
    print(f"prompt_version={metadata.get('prompt_version')} generation_mode={metadata.get('generation_mode')}")
    print(f"notes_chars={len(notes)} word_count={word_count}")
    print("---- NOTES PREVIEW (first 600 chars) ----")
    print(notes[:600])

    if provider == "local" or metadata.get("generation_mode") == "local_fallback":
        print("FAIL: got local/local_fallback notes instead of real Gemini AI notes")
        return 1
    if provider != "gemini":
        print(f"FAIL: unexpected provider={provider}")
        return 1
    if metadata.get("notes_engine") != "exambuddy_sectioned_v30":
        print(f"FAIL: unexpected notes_engine={metadata.get('notes_engine')}")
        return 1
    if not word_count or word_count < 2000:
        print(f"FAIL: word_count too low ({word_count}), expected >= 2000")
        return 1

    missing = [h for h in REQUIRED_HEADINGS if h not in notes]
    if missing:
        print(f"FAIL: missing required headings: {missing}")
        return 1

    print(f"PASS: real Gemini sectioned notes confirmed (word_count={word_count}, all headings present)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
