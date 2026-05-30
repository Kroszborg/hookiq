"""
Unified LLM service — supports Groq (default) and Gemini.
Switch via LLM_PROVIDER env var: "groq" (default) or "gemini"

Groq free tier: 30 RPM, 14,400 requests/day — ideal for demos.
Gemini free tier: ~15 RPM, 1,500 requests/day — hits limits with parallel calls.
"""
import json
import logging
import re
from functools import lru_cache
from typing import Any, AsyncGenerator

from app.config import get_settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Groq implementation
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_groq_client():
    from groq import Groq
    settings = get_settings()
    return Groq(api_key=settings.GROQ_API_KEY)


async def _groq_generate_json(prompt: str) -> dict[str, Any]:
    settings = get_settings()
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a JSON API. Always respond with valid JSON only. No markdown, no code fences."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=2048,
    )
    return json.loads(response.choices[0].message.content)


async def _groq_stream_text(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    client = _get_groq_client()

    msg_list = [{"role": "system", "content": system_prompt}]
    for m in messages:
        role = "user" if m["role"] == "user" else "assistant"
        msg_list.append({"role": role, "content": m["content"]})

    stream = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=msg_list,
        stream=True,
        temperature=0.7,
        max_tokens=2048,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ─────────────────────────────────────────────
# Gemini implementation (fallback)
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_gemini_client():
    from google import genai
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def _gemini_generate_json(prompt: str) -> dict[str, Any]:
    from google.genai import types
    settings = get_settings()
    client = _get_gemini_client()
    full_prompt = prompt + "\n\nRespond with valid JSON only. No markdown, no code blocks."
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    text = response.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


async def _gemini_stream_text(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    from google.genai import types
    settings = get_settings()
    client = _get_gemini_client()

    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]
    config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.7)
    for chunk in client.models.generate_content_stream(
        model=settings.GEMINI_MODEL,
        contents=contents,
        config=config,
    ):
        if chunk.text:
            yield chunk.text


# ─────────────────────────────────────────────
# Public API — dispatch based on LLM_PROVIDER
# ─────────────────────────────────────────────

def _is_groq() -> bool:
    return get_settings().LLM_PROVIDER.lower() == "groq"


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()


async def generate_json(prompt: str, schema_hint: str = "") -> dict[str, Any]:
    full_prompt = prompt
    if schema_hint:
        full_prompt += f"\n\nExpected JSON schema:\n{schema_hint}"

    if _is_groq():
        return await _groq_generate_json(full_prompt)
    else:
        return await _gemini_generate_json(full_prompt)


async def stream_text(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    if _is_groq():
        async for chunk in _groq_stream_text(system_prompt, messages):
            yield chunk
    else:
        async for chunk in _gemini_stream_text(system_prompt, messages):
            yield chunk


def get_langchain_llm():
    """Return a LangChain-compatible LLM for use in LangGraph agent."""
    settings = get_settings()
    if _is_groq():
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.GROQ_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            streaming=True,
            temperature=0.7,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            streaming=True,
            temperature=0.7,
        )
