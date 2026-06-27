import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Bound the model output so responses stay fast and never run away.
GEMINI_MAX_OUTPUT_TOKENS = 8192

# Study notes are long, structured documents. Give them a much larger ceiling so
# the JSON payload is never truncated mid-document (truncation corrupts the
# markdown and forces the placeholder fallback). Only the Gemini 2.5 family
# supports outputs this large; older models are clamped to their 8192 limit.
GEMINI_MAX_NOTES_TOKENS = 24576

# Shared, connection-pooled HTTP client. Re-creating a client per request
# (the old behaviour) added TLS/handshake latency to every AI call.
_shared_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=90.0, write=30.0, pool=15.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _shared_client


async def close_http_client() -> None:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None


class GeminiAPIError(RuntimeError):
    """Carries the HTTP status so callers can decide whether to retry."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Gemini REST {status_code}: {detail}")

    @property
    def is_fatal(self) -> bool:
        # Quota and auth errors will fail identically on every model, so there
        # is no point burning seconds retrying — fail fast to the local fallback.
        return self.status_code in (401, 403, 429)


class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        pass

    @abstractmethod
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        pass


class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=max_output_tokens,
        )
        content = response.choices[0].message.content or "{}"
        metadata = {
            "provider": "openai",
            "model": self.model,
            "tokens_used": response.usage.total_tokens if response.usage else None,
        }
        return json.loads(content), metadata

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=max_output_tokens,
        )
        content = response.choices[0].message.content or ""
        metadata = {
            "provider": "openai",
            "model": self.model,
            "tokens_used": response.usage.total_tokens if response.usage else None,
        }
        return content, metadata


class GeminiProvider(BaseAIProvider):
    """Gemini via REST API (supports AIza and AQ. auth keys)."""

    FALLBACK_MODELS = (
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
    )

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _models_to_try(self) -> list[str]:
        models = [self.model, *self.FALLBACK_MODELS]
        seen: set[str] = set()
        ordered: list[str] = []
        for m in models:
            if m and m not in seen:
                seen.add(m)
                ordered.append(m)
        return ordered

    @staticmethod
    def _supports_thinking(model_name: str) -> bool:
        # Only the Gemini 2.5 family accepts thinkingConfig; sending it to 2.0
        # models returns a 400. 2.5 Flash thinks by default, which is the main
        # source of latency — turning it off makes notes generate far faster.
        return model_name.startswith("gemini-2.5")

    @staticmethod
    def _salvage_notes_json(text: str) -> dict[str, Any] | None:
        """
        Recover the "notes" (and "summary") fields from a JSON blob that failed
        to parse — usually because the model hit the output-token cap and the
        string was cut off before the closing brace. Without this, truncated
        responses surface to the user as raw `{"notes": "...` fragments.
        """
        match = re.search(r'"notes"\s*:\s*"', text)
        if not match:
            return None

        escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}
        chars: list[str] = []
        i = match.end()
        while i < len(text):
            ch = text[i]
            if ch == "\\" and i + 1 < len(text):
                chars.append(escapes.get(text[i + 1], text[i + 1]))
                i += 2
                continue
            if ch == '"':
                break
            chars.append(ch)
            i += 1

        notes = "".join(chars).strip()
        if not notes:
            return None

        result: dict[str, Any] = {"notes": notes}
        summary_match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if summary_match:
            try:
                result["summary"] = json.loads('"' + summary_match.group(1) + '"')
            except json.JSONDecodeError:
                pass
        return result

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        text = (content or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            inner = fence.group(1).strip()
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                salvaged = GeminiProvider._salvage_notes_json(inner)
                if salvaged:
                    return salvaged
        salvaged = GeminiProvider._salvage_notes_json(text)
        if salvaged:
            return salvaged
        return {"notes": text}

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            return ""
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))

    @staticmethod
    def _effective_max_tokens(model_name: str, max_output_tokens: int | None) -> int:
        tokens = max_output_tokens or GEMINI_MAX_OUTPUT_TOKENS
        # Only the 2.5 family supports very large outputs; older flash models
        # cap at 8192 and reject larger requests.
        if not model_name.startswith("gemini-2.5"):
            tokens = min(tokens, GEMINI_MAX_OUTPUT_TOKENS)
        return tokens

    async def _rest_generate(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        *,
        json_mode: bool,
        max_output_tokens: int | None = None,
    ) -> str:
        url = f"{GEMINI_API_BASE}/models/{model_name}:generateContent"
        generation_config: dict[str, Any] = {
            "temperature": 0.3 if json_mode else 0.4,
            "maxOutputTokens": self._effective_max_tokens(model_name, max_output_tokens),
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        if self._supports_thinking(model_name):
            generation_config["thinkingConfig"] = {"thinkingBudget": 0}

        body: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        client = _get_http_client()
        response = await client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            raise GeminiAPIError(response.status_code, response.text[:500])
        data = response.json()
        text = self._extract_text(data)
        if not text:
            raise RuntimeError("Gemini REST returned empty content")
        return text

    async def _sdk_generate(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        *,
        json_mode: bool,
        max_output_tokens: int | None = None,
    ) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        generation_config: dict[str, Any] = {
            "temperature": 0.3 if json_mode else 0.4,
            "max_output_tokens": self._effective_max_tokens(model_name, max_output_tokens),
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
        if self._supports_thinking(model_name):
            generation_config["thinking_config"] = {"thinking_budget": 0}

        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
                generation_config=generation_config,
            )
        except (TypeError, ValueError):
            # Older SDK builds may not accept thinking_config — drop it and retry.
            generation_config.pop("thinking_config", None)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
                generation_config=generation_config,
            )
        response = await model.generate_content_async(user_prompt)
        return response.text or ""

    async def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        json_mode: bool,
        max_output_tokens: int | None = None,
    ) -> tuple[str, str]:
        last_exc: Exception | None = None

        # Pass 1: REST for each model. Fail fast on quota/auth (retrying other
        # models would hit the same wall and waste many seconds).
        for model_name in self._models_to_try():
            try:
                content = await self._rest_generate(
                    model_name,
                    system_prompt,
                    user_prompt,
                    json_mode=json_mode,
                    max_output_tokens=max_output_tokens,
                )
                if content.strip():
                    logger.info("Gemini rest generation succeeded model=%s", model_name)
                    return content, model_name
            except GeminiAPIError as exc:
                last_exc = exc
                if exc.is_fatal:
                    logger.warning("Gemini fatal error (%s) — skipping retries", exc.status_code)
                    raise
                logger.warning("Gemini rest model %s failed: %s", model_name, exc)
            except Exception as exc:
                logger.warning("Gemini rest model %s failed: %s", model_name, exc)
                last_exc = exc

        # Pass 2: single SDK attempt with the primary model as a last resort
        # (covers edge auth-key formats the REST path may reject).
        try:
            content = await self._sdk_generate(
                self.model,
                system_prompt,
                user_prompt,
                json_mode=json_mode,
                max_output_tokens=max_output_tokens,
            )
            if content.strip():
                logger.info("Gemini sdk generation succeeded model=%s", self.model)
                return content, self.model
        except Exception as exc:
            logger.warning("Gemini sdk fallback failed: %s", exc)
            last_exc = exc

        raise RuntimeError(f"All Gemini models failed: {last_exc}") from last_exc

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        content, model_name = await self._generate(
            system_prompt, user_prompt, json_mode=True, max_output_tokens=max_output_tokens
        )
        parsed = self._parse_json_content(content)
        metadata = {
            "provider": "gemini",
            "model": model_name,
            "tokens_used": None,
        }
        return parsed, metadata

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        content, model_name = await self._generate(
            system_prompt, user_prompt, json_mode=False, max_output_tokens=max_output_tokens
        )
        metadata = {
            "provider": "gemini",
            "model": model_name,
            "tokens_used": None,
        }
        return content, metadata


def chunk_text(text: str, chunk_size: int = 12000, overlap: int = 500) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
