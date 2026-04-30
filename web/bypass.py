"""Server-side LKSFY bypass.

Mirrors the userscript at
https://greasyfork.org/en/scripts/571604-lksfy-instant-redirect:

1. Intermediate domains (sharclub.in, sportswordz.com, wblaxmibhandar.com)
   carry the LKSFY id in `?id=` and resolve to https://lksfy.com/{id}.
2. On lksfy.com, setting cookie `ab=1` short-circuits the wait/ad gate
   and the page redirects directly to the destination.

We replay this server-side using httpx, capturing the final 30x Location.
For GPLinks we follow redirects with the same trick attempt.
"""
from __future__ import annotations
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs
import httpx

logger = logging.getLogger(__name__)

LKSFY_HOSTS = {"lksfy.com", "www.lksfy.com"}
INTERMEDIATE_HOSTS = {"sharclub.in", "sportswordz.com", "wblaxmibhandar.com"}


def _normalize_to_lksfy(short_url: str) -> str:
    """If URL is one of the intermediate hosts with ?id=, rewrite to lksfy.com/{id}."""
    parsed = urlparse(short_url)
    host = (parsed.hostname or "").lower()
    if any(host.endswith(h) for h in INTERMEDIATE_HOSTS):
        qs = parse_qs(parsed.query)
        ids = qs.get("id")
        if ids:
            return f"https://lksfy.com/{ids[0]}"
    return short_url


async def bypass_lksfy(short_url: str) -> Optional[str]:
    """Resolve a lksfy.com short URL to its final destination using ab=1 cookie."""
    target = _normalize_to_lksfy(short_url)
    cookies = {"ab": "1"}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            cookies=cookies,
            headers=headers,
        ) as client:
            r = await client.get(target)
            final = str(r.url)
            final_host = (urlparse(final).hostname or "").lower()
            if final_host and not any(final_host.endswith(h) for h in LKSFY_HOSTS):
                return final
            for line in r.text.splitlines():
                low = line.lower()
                if "window.location" in low or "location.replace" in low or "location.href" in low:
                    import re
                    m = re.search(r"https?://[^\"'\s<>]+", line)
                    if m:
                        candidate = m.group(0)
                        ch = (urlparse(candidate).hostname or "").lower()
                        if ch and not any(ch.endswith(h) for h in LKSFY_HOSTS):
                            return candidate
    except Exception as e:
        logger.exception("LKSFY bypass failed: %s", e)
    return None


async def bypass_provider(short_url: str) -> str:
    """Dispatch to the right bypass strategy. Returns short_url on failure."""
    host = (urlparse(short_url).hostname or "").lower()
    if any(host.endswith(h) for h in LKSFY_HOSTS | INTERMEDIATE_HOSTS):
        result = await bypass_lksfy(short_url)
        return result or short_url
    return short_url
