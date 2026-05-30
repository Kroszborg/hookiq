# Backward-compat shim — all calls now go through app.services.llm
# which supports both Groq (default) and Gemini based on LLM_PROVIDER env var.
from app.services.llm import generate_json, stream_text, get_langchain_llm

__all__ = ["generate_json", "stream_text", "get_langchain_llm"]
