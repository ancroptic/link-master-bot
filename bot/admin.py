"""Admin-only commands and toggles."""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import config
from bot.database import db

logger = logging.getLogger(__name__)


def is_admin(uid: int) -> bool:
    return uid == config.ADMIN_TELEGRAM_ID


def admin_keyboard(s: dict) -> InlineKeyboardMarkup:
    def lab(name: str, key: str) -> str:
        return f"{name}: {'🟢 ON' if s.get(key) else '🔴 OFF'}"

    rows = [
        [InlineKeyboardButton(lab("Bypass", "bypass_enabled"), callback_data="adm:bypass_enabled")],
        [InlineKeyboardButton(lab("Global Redirect", "global_redirect_enabled"), callback_data="adm:global_redirect_enabled")],
        [InlineKeyboardButton(lab("IP Logging", "ip_logging_enabled"), callback_data="adm:ip_logging_enabled")],
        [InlineKeyboardButton(lab("Maintenance", "maintenance_mode"), callback_data="adm:maintenance_mode")],
        [InlineKeyboardButton("📊 Stats", callback_data="adm:stats")],
    ]
    return InlineKeyboardMarkup(rows)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Not authorized.")
        return
    s = await db.get_settings()
    text = (
        "<b>🛡️ Admin Panel</b>\n\n"
        "Toggle features and view stats."
    )
    await update.message.reply_html(text, reply_markup=admin_keyboard(s))


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Not authorized", show_alert=True)
        return
    await q.answer()
    data = (q.data or "").split(":", 1)[1]
    if data == "stats":
        st = await db.stats()
        await q.message.reply_html(
            f"<b>📊 Global Stats</b>\n\n"
            f"👥 Users: <b>{st['users']}</b>\n"
            f"🔗 Links: <b>{st['links']}</b>\n"
            f"👁 Clicks: <b>{st['clicks']}</b>"
        )
        return
    s = await db.get_settings()
    new_val = not bool(s.get(data))
    s = await db.update_setting(data, new_val)
    try:
        await q.edit_message_reply_markup(reply_markup=admin_keyboard(s))
    except Exception:
        pass


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
