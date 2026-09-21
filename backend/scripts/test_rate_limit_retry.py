#!/usr/bin/env python3
"""
Smoke tests for free-tier Gemini rate-limit handling — NO live network calls.

Covers:

1. `is_rate_limit_error` (core.exceptions) must see THROUGH the generic
   wrapper message ("AI generation failed for all configured providers") to
   the real 429/RESOURCE_EXHAUSTED text carried on the exception's __cause__
   chain — that's the bug that made Stage 3 rate-limit retry never engage.

2. The concise notes pipeline's `_call_with_rate_limit_retry` must retry on a
   mocked 429 and succeed once the mock "recovers", then give up after a
   bounded number of attempts. `asyncio.sleep` is patched out so this runs in
   well under a second instead of waiting the real backoff.

Run from the backend/ directory:
    python scripts/test_rate_limit_retry.py
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from app.core.exceptions import ExternalServiceError, describe_exception_chain, is_rate_limit_error
from app.services.notes_engine.pipeline import _call_with_rate_limit_retry


def test_chain_aware_detection() -> None:
    real_gemini_error = RuntimeError(
        "All Gemini models failed: Gemini REST 429: RESOURCE_EXHAUSTED. Please retry in 32.5s."
    )

    # Mirrors llm_service._generate_json: the outer message embeds the real
    # cause via describe_exception_chain.
    wrapped = ExternalServiceError(
        f"AI generation failed for all configured providers: {describe_exception_chain(real_gemini_error)}"
    )
    wrapped.__cause__ = real_gemini_error
    assert "429" in wrapped.message, "fix regressed: real error text missing from wrapper message"
    assert is_rate_limit_error(wrapped)

    # Belt-and-suspenders: even if a caller wraps WITHOUT embedding the cause
    # in the message, walking __cause__/__context__ must still catch it.
    bare_wrapped = ExternalServiceError("AI generation failed for all configured providers")
    bare_wrapped.__cause__ = real_gemini_error
    assert "429" not in bare_wrapped.message  # proves this only works via chain-walking
    assert is_rate_limit_error(bare_wrapped)

    # __context__ fallback (raised inside an except block without `from`).
    context_only = ExternalServiceError("Gemini notes generation failed")
    try:
        try:
            raise real_gemini_error
        except RuntimeError:
            raise context_only
    except ExternalServiceError as caught:
        assert is_rate_limit_error(caught)

    unrelated = ExternalServiceError("Gemini returned empty notes content")
    assert not is_rate_limit_error(unrelated)

    print("PASS: chain-aware rate-limit detection (wrapped, bare-wrapped, __context__, unrelated)")


async def test_retry_engages_and_recovers() -> None:
    real_gemini_error = RuntimeError("Gemini REST 429: RESOURCE_EXHAUSTED. Please retry in 1.0s.")
    attempts: list[int] = []

    async def fake_generate_notes_json(system_prompt, user_prompt, schema, max_tokens, temperature):
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise ExternalServiceError(
                f"AI generation failed for all configured providers: {describe_exception_chain(real_gemini_error)}"
            ) from real_gemini_error
        return {"ok": True}, {"provider": "gemini", "model": "gemini-2.5-flash"}

    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    with patch("asyncio.sleep", side_effect=fake_sleep):
        result, meta = await _call_with_rate_limit_retry(
            fake_generate_notes_json,
            "system prompt",
            "user prompt",
            topic="Binary Search Trees",
            stage="generate",
        )

    assert attempts == [1, 2, 3], f"expected 3 attempts, got {attempts}"
    assert result == {"ok": True}
    assert meta["model"] == "gemini-2.5-flash"
    assert len(sleeps) == 2, f"expected 2 backoff waits before the 3rd (successful) attempt, got {sleeps}"
    print(f"PASS: rate-limit retry engaged, backed off {sleeps}s, and recovered on attempt {len(attempts)}")


async def test_gives_up_after_max_attempts() -> None:
    real_gemini_error = RuntimeError("Gemini REST 429: RESOURCE_EXHAUSTED.")
    attempts: list[int] = []

    async def always_rate_limited(system_prompt, user_prompt, schema, max_tokens, temperature):
        attempts.append(len(attempts) + 1)
        raise ExternalServiceError(
            f"AI generation failed for all configured providers: {describe_exception_chain(real_gemini_error)}"
        ) from real_gemini_error

    async def fake_sleep(seconds: float) -> None:
        return None

    with patch("asyncio.sleep", side_effect=fake_sleep):
        try:
            await _call_with_rate_limit_retry(
                always_rate_limited,
                "system prompt",
                "user prompt",
                topic="Binary Search Trees",
                stage="generate",
            )
        except ExternalServiceError:
            pass
        else:
            raise AssertionError("expected the persistent 429 to eventually raise")

    assert len(attempts) == 3, f"expected exactly 3 attempts (few retries), got {len(attempts)}"
    print(f"PASS: gives up after {len(attempts)} attempts instead of retrying forever")


def main() -> int:
    test_chain_aware_detection()
    asyncio.run(test_retry_engages_and_recovers())
    asyncio.run(test_gives_up_after_max_attempts())
    print("\nAll rate-limit smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
