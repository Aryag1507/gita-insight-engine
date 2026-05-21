"""Shared HTTP client with rate-limiting and retry logic."""
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; gita-research-bot/1.0)"}
RATE_LIMIT_SECONDS = 1.5  # polite delay between requests


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=HEADERS,
        timeout=20.0,
        follow_redirects=True,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch(client: httpx.AsyncClient, url: str) -> httpx.Response:
    resp = await client.get(url)
    resp.raise_for_status()
    await asyncio.sleep(RATE_LIMIT_SECONDS)
    return resp
