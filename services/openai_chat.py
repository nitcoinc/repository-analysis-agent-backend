"""
Central OpenAI chat completions: always use ``OPENAI_MODEL`` / ``settings.openai_model`` first.

Optional ``OPENAI_MODEL_FALLBACKS`` is only used if the primary model request fails (quota,
unknown model name, etc.). Set fallbacks in ``.env`` explicitly; the default is no fallbacks so
runs do not silently switch to another model.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from openai import OpenAI

from core.config import get_settings

logger = logging.getLogger(__name__)


def chat_model_candidates() -> List[str]:
    """Primary model first, then comma-separated fallbacks (deduplicated)."""
    s = get_settings()
    primary = (s.openai_model or "").strip()
    out: List[str] = []
    if primary:
        out.append(primary)
    for fb in str(s.openai_model_fallbacks or "").split(","):
        fb = fb.strip()
        if fb and fb not in out:
            out.append(fb)
    return out


def chat_completions_create(
    client: OpenAI,
    *,
    model_override: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """
    Call ``client.chat.completions.create`` with ``settings.openai_model`` first.

    Pass *model_override* to use a specific model (e.g. documentation_model) instead
    of the global OPENAI_MODEL.  Do not pass ``model`` in kwargs.
    """
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    if kwargs.pop("model", None) is not None:
        logger.warning("openai_chat: ignored model= in kwargs; use model_override param or OPENAI_MODEL in environment")

    if model_override and model_override.strip():
        candidates = [model_override.strip()]
        for fb in chat_model_candidates():
            if fb not in candidates:
                candidates.append(fb)
    else:
        candidates = chat_model_candidates()

    if not candidates:
        raise RuntimeError("OPENAI_MODEL is not configured (set in .env or environment).")

    last_exc: Optional[Exception] = None
    primary = candidates[0]
    for candidate in candidates:
        try:
            if candidate != primary:
                logger.info("OpenAI chat: retrying with fallback model %s (primary was %s)", candidate, primary)
            resp = client.chat.completions.create(model=candidate, **kwargs)
            logger.debug("OpenAI chat completion ok: model=%s", candidate)
            return resp
        except Exception as exc:
            last_exc = exc
            logger.warning("OpenAI chat failed for model %s: %s", candidate, exc)
            continue

    attempted = ", ".join(candidates)
    raise RuntimeError(
        f"Chat completion failed for all configured models ({attempted}). "
        "Check OPENAI_MODEL, OPENAI_MODEL_FALLBACKS, and API access."
    ) from last_exc
