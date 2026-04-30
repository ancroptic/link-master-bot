"""Admin-only commands and rich admin panel."""
from __future__ import annotations
import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import config
from bot.database import db

logger = logging.getLogger(__name__)


def is_admin(uid: int) -> bool:
    return uid == config.ADMIN_TELEGRAM_ID


def kb(rows):
    return InlineKeyboardMarkup(rows)


def admin_home_kb(s: dict) -> InlineKeyboardMarkup:
    def t(name: str, key: str) -> str:
        return f"{name}: {'🟢 ON' if s.get(key) else '🔴 OFF'}"
    rows = [
        [InlineKeyboardButton(t("🛡️ Bypass", "bypass_enabled"), callback_data="adm:tog:bypass_enabled")],
        [InlineKeyboardButton(t("🌐 Global Redirect", "global_redirect_enabled"), callback_data="adm:tog:global_redirect_enabled")],
        [InlineKeyboardButton(t("📍 IP Logging", "ip_logging_enabled"), callback_data="adm:tog:ip_logging_enabled")],
        [InlineKeyboardButton(t("🔧 Maintenance", "maintenance_mode"), callback_data="adm:tog:maintenance_mode")],
        [InlineKeyboardButton("📊 Global Stats", callback_data="adm:stats"),
         InlineKeyboardButton("🔑 Admin API", callback_data="adm:api")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="adm:bcast"),
         InlineKeyboardButton("👥 Users", callback_data="adm:users")],
        [InlineKeyboardButton("🚫 Ban", callback_data="adm:ban"),
         InlineKeyboardButton("✅ Unban", callback_data="adm:unban")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="adm:home"),
         InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:home")],
    ]
    return InlineKeyboardMarkup(rows)


def back_admin_kb() -> InlineKeyboardMarkup:
    return kb([[InlineKeyboardButton("⬅️ Back to Admin", callback_data="adm:home")]])


async def _edit(update: Update, text: str, markup: InlineKeyboardMarkup):
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text=text, reply_markup=markup, parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return
        except Exception as e:
            if "not modified" in str(e).lower():
                return
    await update.effective_message.reply_html(text, reply_markup=markup, disable_web_page_preview=True)


def render_home(s: dict) -> str:
    return (
        "<b>🛡️ Admin Panel</b>\n\n"
        f"🛡️ Bypass: <b>{'ON' if s.get('bypass_enabled') else 'OFF'}</b>\n"
        f"🌐 Global Redirect: <b>{'ON' if s.get('global_redirect_enabled') else 'OFF'}</b>\n"
        f"📍 IP Logging: <b>{'ON' if s.get('ip_logging_enabled') else 'OFF'}</b>\n"
        f"🔧 Maintenance: <b>{'ON' if s.get('maintenance_mode') else 'OFF'}</b>\n\n"
        f"⚙️ Admin shortener: <code>{s.get('admin_shortener_type') or 'gplinks'}</code>\n"
        "<i>Tap a row to toggle.</i>"
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Not authorized.")
        return
    s = await db.get_settings()
    await _edit(update, render_home(s), admin_home_kb(s))


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Not authorized", show_alert=True)
        return
    await q.answer()
    parts = (q.data or "").split(":")
    if len(parts) < 2:
        return
    section = parts[1]

    if section == "home":
        s = await db.get_settings()
        await _edit(update, render_home(s), admin_home_kb(s))
        return

    if section == "tog" and len(parts) >= 3:
        key = parts[2]
        s = await db.get_settings()
        s = await db.update_setting(key, not bool(s.get(key)))
        await _edit(update, render_home(s), admin_home_kb(s))
        return

    if section == "stats":
        st = await db.stats()
        text = (
            "<b>📊 Global Stats</b>\n\n"
            f"👥 Users: <b>{st['users']}</b>\n"
            f"🔗 Links: <b>{st['links']}</b>\n"
            f"👁 Total clicks: <b>{st['clicks']}</b>"
        )
        await _edit(update, text, back_admin_kb())
        return

    if section == "users":
        rows = await db.list_users(limit=15)
        lines = ["<b>👥 Recent Users</b>\n"]
        for r in rows:
            uname = html.escape(r.get("username") or "")
            ban = "🚫" if r.get("is_banned") else "✅"
            lines.append(f"{ban} <code>{r['telegram_id']}</code> @{uname} — links: {r.get('total_shortened', 0)}")
        await _edit(update, "\n".join(lines) or "No users.", back_admin_kb())
        return

    if section == "api":
        text = (
            "<b>🔑 Admin Shortener API</b>\n\n"
            "Choose provider, then send the API key as a message."
        )
        await _edit(update, text, kb([
            [InlineKeyboardButton("GPLinks", callback_data="adm:apiset:gplinks"),
             InlineKeyboardButton("LinkShortify", callback_data="adm:apiset:linkshortify")],
            [InlineKeyboardButton("⬅️ Back to Admin", callback_data="adm:home")],
        ]))
        return

    if section == "apiset" and len(parts) >= 3:
        context.user_data["await_admin_api"] = parts[2]
        await _edit(update,
            f"<b>🔑 Send the {parts[2]} API key now.</b>\n/cancel to abort.",
            back_admin_kb())
        return

    if section == "bcast":
        context.user_data["await_broadcast"] = True
        await _edit(update,
            "<b>📣 Broadcast</b>\n\nSend the message to broadcast to all users.\nHTML supported. /cancel to abort.",
            back_admin_kb())
        return

    if section == "ban":
        context.user_data["await_ban"] = True
        await _edit(update,
            "<b>🚫 Ban User</b>\n\nSend the Telegram user id to ban.",
            back_admin_kb())
        return

    if section == "unban":
        context.user_data["await_unban"] = True
        await _edit(update,
            "<b>✅ Unban User</b>\n\nSend the Telegram user id to unban.",
            back_admin_kb())
        return


async def setadminapi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text("Usage: /setadminapi <gplinks|linkshortify> <KEY>")
        return
    await db.update_setting("admin_shortener_type", args[0].lower())
    await db.update_setting("admin_api_key", args[1])
    await update.message.reply_text("✅ Admin API updated.")
