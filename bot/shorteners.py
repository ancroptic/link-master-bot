"""Shortener API wrappers — supports GPLinks, LinkShortify (lksfy.com)."""
from __future__ import annotations
import logging
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)

_ENDPOINTS = {
    "gplinks": "https://gplinks.com/api",
    "linkshortify": "https://lksfy.com/api",
    "lksfy": "https://lksfy.com/api",
}


def _pick_endpoint(api_type: str) -> str:
    return _ENDPOINTS.get((api_type or "gplinks").lower(), _ENDPOINTS["gplinks"])


def _extract_short(data) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    if str(data.get("status", "")).lower() != "success":
        return None
    for key in ("shortenedUrl", "shortened_url", "shortLink", "short_url", "url"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


async def shorten_link(original_url: str, api_data: Dict[str, str]) -> str:
    """Returns shortened URL via configured provider; falls back to original_url on failure."""
    api_key = (api_data or {}).get("api_key") or ""
    api_type = ((api_data or {}).get("type") or "gplinks").lower()
    if not api_key or not original_url:
        return original_url
    endpoint = _pick_endpoint(api_type)
    params = {"api": api_key, "url": original_url}
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (linkmasterbot)"},
        ) as client:
            r = await client.get(endpoint, params=params)
            try:
                data = r.json()
            except Exception:
                logger.warning("Shortener %s non-JSON response: %s", api_type, r.text[:200])
                return original_url
            short = _extract_short(data)
            if short:
                return short
            logger.warning("Shortener %s response unexpected: %s", api_type, data)
    except Exception as e:
        logger.exception("Shortener %s failed: %s", api_type, e)
    return original_url
