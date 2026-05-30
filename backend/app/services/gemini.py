import json
import logging
from functools import lru_cache
from typing import Any, AsyncGenerator

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

MODEL = "gemini-2.0-flash"


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def generate_json(prompt: str, schema_hint: str = "") -> dict[str, Any]:
    client = get_client()
    full_prompt = prompt
    if schema_hint:
        full_prompt += f"\n\nExpected JSON schema:\n{schema_hint}"
    full_prompt += "\n\nRespond with valid JSON only. No markdown, no code blocks."

    response = client.models.generate_content(
        model=MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    text = response.text.strip()
    # Strip markdown fences if model still wraps in them
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


async def stream_text(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    client = get_client()

    # Build contents list for the new SDK
    contents: list[types.Content] = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])],
            )
        )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.7,
    )

    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=contents,
        config=config,
    ):
        if chunk.text:
            yield chunk.text
