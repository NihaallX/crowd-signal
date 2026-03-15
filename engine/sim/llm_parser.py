"""LLM-powered catalyst bias parser using Groq via the OpenAI-compatible SDK."""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_SYSTEM_PROMPT = (
    "You are a financial sentiment analyzer for intraday stock trading. "
    "Given a market catalyst, return ONLY a single float between -1.0 and 1.0 "
    "representing crowd sentiment bias.\n"
    "-1.0 = extremely bearish crowd reaction\n"
    "-0.5 = moderately bearish\n"
    " 0.0 = neutral\n"
    "+0.5 = moderately bullish\n"
    "+1.0 = extremely bullish\n"
    "Consider: earnings, CEO actions, macro events, product launches, "
    "legal issues, analyst ratings.\n"
    "Return ONLY the float. No explanation. No text."
)

_MODEL = "llama-3.1-8b-instant"  # llama3-8b-8192 is decommissioned
_TIMEOUT = 8.0  # seconds — allows for Groq cold starts

# Keyword fallback lists (mirrors runner.py — kept here to avoid circular import)
_POSITIVE_KW = ["beat", "surge", "growth", "bullish", "upgrade", "record"]
_NEGATIVE_KW = ["miss", "crash", "layoffs", "bearish", "downgrade", "loss"]


def _clamp(value: float) -> float:
    """Clamp *value* to [-1.0, 1.0]."""
    return max(-1.0, min(1.0, value))


def _keyword_fallback(catalyst: str) -> float:
    """Simple keyword-based bias scorer used when the LLM is unavailable."""
    text = catalyst.lower()
    pos = sum(len(re.findall(rf"\b{re.escape(kw)}\b", text)) for kw in _POSITIVE_KW)
    neg = sum(len(re.findall(rf"\b{re.escape(kw)}\b", text)) for kw in _NEGATIVE_KW)
    if pos == 0 and neg == 0:
        return 0.0
    raw = 0.30 * (pos - neg)
    pct_matches = [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)]
    multiplier = 1.0
    if pct_matches:
        multiplier += min(max(pct_matches), 50.0) / 100.0
    return _clamp(raw * multiplier)


def parse_catalyst_bias_llm(catalyst: str) -> float:
    """Parse a market catalyst into a sentiment bias using the Groq LLM.

    Uses the Groq API (OpenAI-compatible) with ``llama3-8b-8192``.
    Falls back to keyword scoring if the API call fails for any reason
    (network error, bad key, timeout, unparseable response, etc.).

    Args:
        catalyst: Free-text description of the market event.

    Returns:
        Float in [-1.0, 1.0] representing crowd sentiment bias.
    """
    try:
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            timeout=_TIMEOUT,
        )

        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": catalyst},
            ],
            max_tokens=10,
            temperature=0.0,  # deterministic — we want a consistent float
        )

        raw = response.choices[0].message.content or ""
        return _clamp(float(raw.strip()))

    except Exception:
        # Any failure → keyword fallback
        return _keyword_fallback(catalyst)
