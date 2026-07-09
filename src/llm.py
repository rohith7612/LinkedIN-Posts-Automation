"""Thin shared wrapper around the OpenAI client so verify.py and describe.py don't duplicate it."""
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

_client = None


def get_client() -> OpenAI:
    global _client
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def ask(prompt: str, system: str = "", reasoning_effort: str = "low") -> str:
    """One-shot text completion using GPT-5 nano via the Responses API."""
    client = get_client()
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=system or None,
        input=prompt,
        reasoning={"effort": reasoning_effort},
    )
    return response.output_text.strip()
