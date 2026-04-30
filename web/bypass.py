"""Server-side LKSFY bypass using curl_cffi (Chrome TLS fingerprint)."""
from __future__ import annotations
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

LKSFY_HOSTS = {"lksfy.com", "www.lksfy.com"}
INTERMEDIATE_HOSTS = {"sharclub.in", "sportswordz.com", "wblaxmibhandar.com"}

_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

_LOC_PATTERN = '(?:window\\.location(?:\\.href)?|location\\.replace|location\\.href)\\s*[=(]\\s*[\'"]([^\'"]+)[\'"]'
_URL_PATTERN = 'https?://[^\\s\'"<>)]+'
_LOCATION_RE = re.compile(_LOC_PATTERN, re.IGNORECASE)
_ANY_URL_RE = re.compile(_URL_PATTERN)

_NOISE_HOST_FRAGMENTS = (
    "cloudflare", "cloudflareinsights", "jsdelivr", "googletagmanager",
    "google-analytics", "gstatic", "googleapis", "fonts.google",
    "facebook", "doubleclick", "adservice", "cdn-cgi",
)

def _normalize_to_lksfy(short_url: str) -> str:
    parsed = urlparse(short_url)
    host = (parsed.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in INTERMEDIATE_HOSTS):
        qs = parse_qs(parsed.query)
        ids = qs.get("id")
        if ids:
            return f"https://lksfy.com/{ids[0]}"
    return short_url

def _is_lksfy(host: str) -> bool:
    host = (host or "").lower()
    return any(host == h or host.endswith("." + h) for h in LKSFY_HOSTS)

def _extract_destination(html: str) -> Optional[str]:
    m = _LOCATION_RE.search(html)
    if m:
        cand = m.group(1)
        h = (urlparse(cand).hostname or "").lower()
        if h and not _is_lksfy(h):
            return cand
    for m2 in _ANY_URL_RE.finditer(html):
        cand = m2.group(0).rstrip('";,)')
        h = (urlparse(cand).hostname or "").lower()
        if not h or _is_lksfy(h):
            continue
        if any(seg in h for seg in _NOISE_HOST_FRAGMENTS):
            continue
        return cand
    return None

def _sync_bypass_lksfy(target: str) -> Optional[str]:
    try:
        from curl_cffi import requests as cffi_requests
    except Exception as e:
        logger.warning("curl_cffi unavailable: %s", e)
        return None
    try:
        with cffi_requests.Session() as s:
            r = s.get(
                target,
                headers=_HEADERS,
                cookies={"ab": "1"},
                impersonate="chrome124",
                allow_redirects=True,
                timeout=20,
            )
            final = str(r.url)
            fh = (urlparse(final).hostname or "").lower()
            if fh and not _is_lksfy(fh):
                return final
            return _extract_destination(r.text or "")
    except Exception as e:
        logger.warning("curl_cffi lksfy bypass failed for %s: %s", target, e)
        return None

async def bypass_lksfy(short_url: str) -> Optional[str]:
    target = _normalize_to_lksfy(short_url)
    return await asyncio.to_thread(_sync_bypass_lksfy, target)

async def bypass_provider(short_url: str) -> str:
    """Returns destination URL on success, else original short_url (fallback)."""
    host = (urlparse(short_url).hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in LKSFY_HOSTS | INTERMEDIATE_HOSTS):
        try:
            result = await bypass_lksfy(short_url)
        except Exception as e:
            logger.exception("bypass_provider error: %s", e)
            result = None
        return result or short_url
    return short_url
