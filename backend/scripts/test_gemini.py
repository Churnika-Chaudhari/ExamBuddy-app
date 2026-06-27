"""Verify Gemini REST connectivity without printing secrets."""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> int:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("FAIL: GEMINI_API_KEY not set")
        return 1

    from app.services.ai.base_provider import GeminiProvider

    provider = GeminiProvider(key, os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    try:
        text, meta = await provider.generate_text(
            "You are a helpful assistant.",
            "Reply with exactly: OK",
        )
        ok = "OK" in (text or "").upper()
        print(f"{'OK' if ok else 'FAIL'}: Gemini provider={meta.get('provider')} model={meta.get('model')}")
        return 0 if ok else 1
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
