"""
Shared utilities for cron jobs.

Import in your job handlers like:
    from shared.utils import fetch_url, call_llm
"""

import json
import urllib.request
from typing import Optional


def fetch_url(url: str, timeout: int = 30) -> str:
    """
    Fetch content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response body as string
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CronBot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def call_llm(
    prompt: str,
    api_key: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 1000,
) -> Optional[str]:
    """
    Call OpenAI-compatible LLM API.

    Args:
        prompt: The prompt to send
        api_key: API key for authentication
        model: Model identifier
        max_tokens: Maximum response tokens

    Returns:
        LLM response text, or None on failure
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM API error: {e}")
        return None
