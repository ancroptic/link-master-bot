"""Async wrapper around Supabase REST for all DB ops."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from bot.config import config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning("Supabase credentials missing; DB calls will fail.")
            self.client: Optional[Client] = None
        else:
            self.client = create_client(
                config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY
            )

    def _c(self) -> Client:
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        return self.client

    async def upsert_user(self, telegram_id: int, username: Optional[str], first_name: Optional[str] = None) -> Dict[str, Any]:
        is_admin = telegram_id == config.ADMIN_TELEGRAM_ID
        payload = {"telegram_id": telegram_id, "username": username or first_name or "", "is_admin": is_admin}
        res = self._c().table("users").upsert(payload, on_conflict="telegram_id").execute()
        return res.data[0] if res.data else payload

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        res = self._c().table("users").select("*").eq("telegram_id", telegram_id).limit(1).execute()
        return res.data[0] if res.data else None

    async def set_user_api(self, telegram_id: int, api_key: str, shortener_type: str) -> None:
        self._c().table("users").update({"shortener_api_key": api_key, "shortener_type": shortener_type}).eq("telegram_id", telegram_id).execute()

    async def increment_user_count(self, telegram_id: int) -> None:
        user = await self.get_user(telegram_id)
        if not user:
            return
        self._c().table("users").update({"total_shortened": (user.get("total_shortened") or 0) + 1}).eq("telegram_id", telegram_id).execute()

    async def create_link(self, creator_id: int, original_url: str, bridge_code: str) -> Dict[str, Any]:
        payload = {"creator_id": creator_id, "original_url": original_url, "bridge_code": bridge_code}
        res = self._c().table("generated_links").insert(payload).execute()
        return res.data[0]

    async def get_link_by_code(self, bridge_code: str) -> Optional[Dict[str, Any]]:
        res = self._c().table("generated_links").select("*").eq("bridge_code", bridge_code).limit(1).execute()
        return res.data[0] if res.data else None

    async def get_or_create_click(self, link_id: str, visitor_ip: str) -> Dict[str, Any]:
        existing = self._c().table("link_clicks").select("*").eq("link_id", link_id).eq("visitor_ip", visitor_ip).limit(1).execute()
        if existing.data:
            row = existing.data[0]
            new_count = (row.get("click_count") or 1) + 1
            self._c().table("link_clicks").update({"click_count": new_count, "last_click": "now()"}).eq("id", row["id"]).execute()
            row["click_count"] = new_count
            return row
        payload = {"link_id": link_id, "visitor_ip": visitor_ip, "click_count": 1}
        res = self._c().table("link_clicks").insert(payload).execute()
        return res.data[0]

    async def get_user_api(self, telegram_id: int) -> Dict[str, Any]:
        user = await self.get_user(telegram_id)
        if not user or not user.get("shortener_api_key"):
            return await self.get_admin_api()
        return {"api_key": user["shortener_api_key"], "type": user.get("shortener_type") or "gplinks"}

    async def get_admin_api(self) -> Dict[str, Any]:
        s = await self.get_settings()
        return {"api_key": s.get("admin_api_key") or config.ADMIN_API_KEY, "type": s.get("admin_shortener_type") or config.ADMIN_SHORTENER_TYPE}

    async def get_settings(self) -> Dict[str, Any]:
        res = self._c().table("bot_settings").select("*").eq("id", 1).limit(1).execute()
        if res.data:
            return res.data[0]
        default = {"id": 1, "bypass_enabled": True, "global_redirect_enabled": True, "ip_logging_enabled": True, "admin_api_key": config.ADMIN_API_KEY, "admin_shortener_type": config.ADMIN_SHORTENER_TYPE, "maintenance_mode": False}
        self._c().table("bot_settings").insert(default).execute()
        return default

    async def update_setting(self, key: str, value: Any) -> Dict[str, Any]:
        self._c().table("bot_settings").update({key: value}).eq("id", 1).execute()
        return await self.get_settings()

    async def is_bypass_enabled(self) -> bool:
        s = await self.get_settings()
        return bool(s.get("bypass_enabled", True))

    async def stats(self) -> Dict[str, Any]:
        users = self._c().table("users").select("telegram_id", count="exact").execute()
        links = self._c().table("generated_links").select("id", count="exact").execute()
        clicks = self._c().table("link_clicks").select("id", count="exact").execute()
        return {"users": users.count or 0, "links": links.count or 0, "clicks": clicks.count or 0}


db = Database()
