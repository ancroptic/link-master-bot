"""GPLinks / LinkShortify API wrappers."""
from __future__ import annotations
import logging
from typing import Dict
import httpx

logger = logging.getLogger(__name__)


async def shorten_link(original_url: str, api_data: Dict[str, str]) -> str:
    api_key = (api_data or {}).get("api_key") or ""
    api_type = ((api_data or {}).get("type") or "gplinks").lower()
    if not api_key:
        return original_url
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            if api_type == "gplinks":
                r = await client.get("https://gplinks.com/api", params={"api": api_key, "url": original_url})
            else:
                r = await client.get("https://lksfy.com/api", params={"api": api_key, "url": original_url})
            data = r.json()
            if data.get("status") == "success" and data.get("shortenedUrl"):
                return data["shortenedUrl"]
            logger.warning("Shortener response unexpected: %s", data)
    except Exception as e:
        logger.exception("Shortener failed: %s", e)
    return original_url
