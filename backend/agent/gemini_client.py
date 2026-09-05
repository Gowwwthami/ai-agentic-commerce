import json
import logging
import re

from config import GEMINI_MODEL, LLM_API_KEY

logger = logging.getLogger(__name__)


def gemini_available() -> bool:
    return bool(LLM_API_KEY)


def generate_json(prompt: str) -> dict | None:
    text = generate_text(prompt, json_mode=True)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def generate_text(prompt: str, json_mode: bool = False) -> str | None:
    if not LLM_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=LLM_API_KEY)
        config_kwargs = {"temperature": 0.2}
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return (response.text or "").strip()
    except Exception:
        logger.exception("Gemini request failed")
        return None
