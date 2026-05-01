"""FastAPI redirect gateway."""
from __future__ import annotations
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from bot.database import db
from bot.shorteners import shorten_link
from web.bypass import bypass_provider

logger = logging.getLogger(__name__)
app = FastAPI(title="LinkMasterBot Gateway")


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "linkmasterbot-gateway"})


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True})


@app.get("/v/{bridge_code}")
async def redirect_engine(bridge_code: str, request: Request) -> RedirectResponse:
    visitor_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "0.0.0.0")
    )
    link_data = await db.get_link_by_code(bridge_code)
    if not link_data:
        raise HTTPException(status_code=404, detail="Link not found")
    original_url = link_data["original_url"]

    settings = await db.get_settings()
    if settings.get("maintenance_mode"):
        raise HTTPException(status_code=503, detail="Maintenance")

    if not settings.get("global_redirect_enabled", True):
        return RedirectResponse(url=original_url)

    visit = await db.get_or_create_click(link_data["id"], visitor_ip)
    if visit["click_count"] == 1:
        api = await db.get_user_api(link_data["creator_id"])
    else:
        api = await db.get_admin_api()

    short_url = await shorten_link(original_url, api)

    if settings.get("bypass_enabled", True):
        try:
            final = await bypass_provider(short_url)
        except Exception as e:
            logger.exception("bypass error for %s: %s", bridge_code, e)
            final = None
        return RedirectResponse(url=final or original_url)

    return RedirectResponse(url=short_url or original_url)
