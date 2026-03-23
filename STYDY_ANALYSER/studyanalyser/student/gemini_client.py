from __future__ import annotations

import os
import time
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    import google.generativeai as genai
except Exception as e:  # pragma: no cover
    genai = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


_MODELS_CACHE: dict[str, Any] = {"models": None, "ts": 0.0}
_CACHE_TTL_SECONDS = 60 * 60  # 1 hour


def _ensure_configured() -> None:
    if load_dotenv is not None:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your environment or .env file.")

    if genai is None:  # pragma: no cover
        raise RuntimeError(
            "google-generativeai is not installed or failed to import. "
            "Install it with: pip install google-generativeai. "
            f"Original error: {_IMPORT_ERROR}"
        )

    genai.configure(api_key=api_key)


def _list_generate_content_models() -> list[str]:
    now = time.time()
    cached_models = _MODELS_CACHE.get("models")
    cached_ts = float(_MODELS_CACHE.get("ts") or 0.0)
    if cached_models and (now - cached_ts) < _CACHE_TTL_SECONDS:
        return list(cached_models)

    models = []
    for m in genai.list_models():
        if "generateContent" in getattr(m, "supported_generation_methods", []):
            models.append(m.name.replace("models/", ""))

    _MODELS_CACHE["models"] = models
    _MODELS_CACHE["ts"] = now
    return models


def get_response(
    prompt: str,
    history: list[dict[str, Any]] | None = None,
    *,
    system_prompt: str | None = None,
) -> str:
    _ensure_configured()

    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("Prompt is empty.")

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    contents: list[dict[str, Any]] = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt.strip()}]})
    contents.extend(list(history or []))
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    last_error: Exception | None = None
    for candidate in [model_name, *_list_generate_content_models()]:
        try:
            model = genai.GenerativeModel(candidate)
            response = model.generate_content(contents)
            text = getattr(response, "text", None)
            if not text:
                raise RuntimeError("Empty response from Gemini.")
            return str(text)
        except Exception as e:  # pragma: no cover
            last_error = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")
