"""LLM client for general peptide Q&A via OpenRouter."""

import httpx
from bot.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

SYSTEM_PROMPT = """You are a helpful peptide research assistant for peptide-compare.com.
You answer questions about peptides, their research applications, dosing protocols, and general information.
You do NOT provide medical advice. Always note that peptides are for research purposes only.
Keep responses concise (under 200 words) for Telegram readability.
If someone asks about pricing or where to buy, tell them to type a peptide name (like "BPC-157" or "semaglutide") to get current prices from 50+ vendors.
Do not use markdown formatting — Telegram will handle it."""


async def chat(message: str) -> str:
    """Send a message to the LLM and return the response."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "max_tokens": 500,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
