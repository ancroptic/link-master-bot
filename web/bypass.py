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

_LOC_PATTERN = r'(?:window\.location(?\\.href)?|location\.replace|location\.href)\\s*[]=](\\s*[\'"]([^\'"]+)[\'"]'
