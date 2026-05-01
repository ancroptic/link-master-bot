"""Server-side LKSFY/intermediate-host bypass using curl_cffi (Chrome TLS fingerprint)."""
from __future__ import annotations
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

LKSFY_HOSTS = {"lksfy.com", "www.lksfy.com"}
INTERMEDIATE_HOSTS = {"sharclub.in", "sportswordz.com", "wblaxmibhandar.com"}
SHORTENER_HOSTS = LKSFY_HOSTS | INTERMEDIATE_HOSTS | {
    "gplinks.com", "www.gplinks.com", "linkshortify.com", "www.linkshortify.com",
}

_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

_LOC_PATTERN = r'(?:window\.location(?:\.href)?|location\.replace|location\.href)\s*[=(]\s*[\'"]([^\'"]+)[\'"]'
_META_REFRESH = r'<meta[^>]+http-equiv=[\'"]?refresh[\'"]?[^>]+url=([^\'";> ]+)'
_URL_PATTERN = r'https?://[^\s\'"<>)]+'
_LOCATION_RE = re.compile(_LOC_PATTERN, re.IGNORECASE)
_META_RE = re.compile(_META_REFRESH, re.IGNORECASE)
_ANY_URL_RE = re.compile(_URL_PATTERN)

_NOISE_HOST_FRAGMENTS = (
    "cloudflare", "cloudflareinsights", "jsdelivr", "googletagmanager",
    "google-analytics", "gstatic", "googleapis", "fonts.google",
    "facebook", "doubleclick", "adservice", "cdn-cgi", "challenges.cloudflare",
    "schema.org", "w3.org",
)

_CHALLENGE_HOST_FRAGMENTS = (
    "challenges.cloudflare.com", "challenge-platform", "cdn-cgi/challenge",
)

_CHALLENGE_BODY_MARKERS = (
    "Just a moment", "cf-challenge", "challenge-platform", "cf_chl_opt",
    "_cf_chl_opt", "Checking your browser", "challenges.cloudflare.com",
    "Enable JavaScript and cookies to continue",
)


def _is_challenge(final_url: str, body: str) -> bool:
    fl = (final_url or "").lower()
    if any(seg in fl for seg in _CHALLENGE_HOST_FRAGMENTS):
        return True
    b = body or ""
    return any(m in b for m in _CHALLENGE_BODY_MARKERS)

_IMPERSONATES = ("chrome124", "chrome120", "chrome110", "safari17_0")


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_lksfy(host: str) -> bool:
    host = (host or "").lower()
    return any(host == h or host.endswith("." + h) for h in LKSFY_HOSTS)


def _is_shortener(host: str) -> bool:
    host = (host or "").lower()
    return any(host == h or host.endswith("." + h) for h in SHORTENER_HOSTS)


def _normalize_to_lksfy(short_url: str) -> str:
    parsed = urlparse(short_url)
    host = (parsed.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in INTERMEDIATE_HOSTS):
        qs = parse_qs(parsed.query)
        ids = qs.get("id")
        if ids:
            return f"https://lksfy.com/{ids[0]}"
    return short_url


def _extract_destination(html: str, current_host: str) -> Optional[str]:
    for rx in (_LOCATION_RE, _META_RE):
        for m in rx.finditer(html or ""):
            cand = m.group(1).strip()
            h = _host(cand)
            if h and h != current_host and not _is_shortener(h) and not any(seg in h for seg in _NOISE_HOST_FRAGMENTS):
                return cand
    for m2 in _ANY_URL_RE.finditer(html or ""):
        cand = m2.group(0).rstrip('";,)\'')
        h = _host(cand)
        if not h or h == current_host or _is_shortener(h):
            continue
        if any(seg in h for seg in _NOISE_HOST_FRAGMENTS):
            continue
        return cand
    return None


def _sync_fetch(target: str):
    try:
        from curl_cffi import requests as cffi_requests
    except Exception as e:
        logger.warning("curl_cffi unavailable: %s", e)
        return None, None, None
    last_exc = None
    for prof in _IMPERSONATES:
        try:
            with cffi_requests.Session() as s:
                r = s.get(
                    target,
                    headers=_HEADERS,
                    cookies={"ab": "1"},
                    impersonate=prof,
                    allow_redirects=True,
                    timeout=25,
                )
                return str(r.url), r.status_code, (r.text or "")
        except Exception as e:
            last_exc = e
            continue
    if last_exc:
        logger.warning("curl_cffi all profiles failed for %s: %s", target, last_exc)
    return None, None, None


def _sync_resolve(short_url: str, max_hops: int = 5) -> Optional[str]:
    current = _normalize_to_lksfy(short_url)
    seen = set()
    for _ in range(max_hops):
        if not current or current in seen:
            break
        seen.add(current)
        final_url, status, body = _sync_fetch(current)
        if not final_url:
            return None
        fh = _host(final_url)
        if _is_challenge(final_url, body):
            logger.warning("Cloudflare challenge encountered for %s -> %s", current, final_url)
            return None
        if fh and not _is_shortener(fh) and not any(seg in fh for seg in _NOISE_HOST_FRAGMENTS):
            return final_url
        nxt = _extract_destination(body, fh)
        if not nxt:
            return None
        if not _is_shortener(_host(nxt)):
            return nxt
        current = _normalize_to_lksfy(nxt)
    return None


async def bypass_lksfy(short_url: str) -> Optional[str]:
    return await asyncio.to_thread(_sync_resolve, short_url)


async def bypass_provider(short_url: str) -> Optional[str]:
    """Returns destination URL on success, None on failure (caller handles fallback)."""
    host = _host(short_url)
    if _is_shortener(host):
        try:
            return await bypass_lksfy(short_url)
        except Exception as e:
            last_exc = e
            return None
    return short_url
