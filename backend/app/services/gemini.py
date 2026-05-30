import json
import logging
from typing import Any, AsyncGenerator

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)

_configured = False


def _configure() -> None:
    global _configured
    if not _configured:
        settings = get_settings()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True


def get_model(model_name: str = "gemini-2.0-flash") -> genai.GenerativeModel:
    _configure()
    return genai.GenerativeModel(model_name)


async def generate_json(prompt: str, schema_hint: str = "") -> dict[str, Any]:
    _configure()
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    full_prompt = f"{prompt}\n\nRespond with valid JSON only."
    if schema_hint:
        full_prompt += f"\n\nExpected JSON schema:\n{schema_hint}"

    response = model.generate_content(full_prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


async def stream_text(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    _configure()
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(temperature=0.7),
    )

    history = []
    for msg in messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=history)
    last_message = messages[-1]["content"] if messages else ""

    response = chat.send_message(last_message, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text
