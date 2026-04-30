"""User-facing Telegram handlers."""
from __future__ import annotations
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import config
from bot.database import db

logger = logging.getLogger(__name__)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🛠️ Setup APIs", callback_data="setup_api"),
         InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium")],
        [InlineKeyboardButton("📖 How to Use", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await db.upsert_user(user.id, user.username, user.first_name)
    text = (
        f"<b>Welcome to LinkMaster, {user.first_name}!</b> 🚀\n\n"
        "<i>The world's most advanced link management system.</i>\n\n"
        "✨ <b>Direct Bypass:</b> Enabled\n"
        "⚡ <b>Engine:</b> Ultra-Fast\n"
        "🔒 <b>Security:</b> Military Grade\n\n"
        "Send me any link to begin."
    )
    await update.message.reply_html(text=text, reply_markup=main_menu_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>📖 How to Use</b>\n\n"
        "1. Tap <b>🛠️ Setup APIs</b> and send <code>/setapi gplinks YOUR_API_KEY</code> "
        "or <code>/setapi linkshortify YOUR_API_KEY</code>.\n"
        "2. Send any URL — I generate a bridge link.\n"
        "3. The bridge handles bypass + IP-aware monetization automatically.\n\n"
        "Admin only: /admin"
    )
    if update.message:
        await update.message.reply_html(text)
    elif update.callback_query:
        await update.callback_query.message.reply_html(text)


async def setapi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text("Usage: /setapi <gplinks|linkshortify> <API_KEY>")
        return
    stype = args[0].lower()
    if stype not in ("gplinks", "linkshortify"):
        await update.message.reply_text("Type must be gplinks or linkshortify.")
        return
    await db.set_user_api(update.effective_user.id, args[1], stype)
    await update.message.reply_html(f"✅ <b>API saved.</b> Type: <code>{stype}</code>")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await db.get_user(update.effective_user.id)
    total = (user or {}).get("total_shortened", 0)
    text = (
        "<b>📊 Your Stats</b>\n\n"
        f"🔗 Links shortened: <b>{total}</b>\n"
        f"👤 Type: {(user or {}).get('shortener_type', 'gplinks')}\n"
    )
    if update.message:
        await update.message.reply_html(text)
    else:
        await update.callback_query.message.reply_html(text)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if data == "setup_api":
        await q.message.reply_html("🛠️ Send: <code>/setapi gplinks YOUR_KEY</code>\nor <code>/setapi linkshortify YOUR_KEY</code>")
    elif data == "stats":
        await stats(update, context)
    elif data == "help":
        await help_cmd(update, context)
    elif data == "premium":
        await q.message.reply_html("💎 Premium unlocks unlimited monetization splits. Contact the admin to upgrade.")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = (update.message.text or "").strip()
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ Send a valid URL starting with http:// or https://")
        return
    user_id = update.effective_user.id
    bridge_code = uuid.uuid4().hex[:8]
    await db.create_link(user_id, url, bridge_code)
    await db.increment_user_count(user_id)
    bridge_url = f"{config.BASE_WEB_URL.rstrip('/')}/v/{bridge_code}"
    text = (
        "✅ <b>Link Processed Successfully!</b>\n\n"
        f"🔗 <b>Original:</b> {url}\n"
        f"🚀 <b>Shortened:</b> <code>{bridge_url}</code>\n\n"
        "<i>Automatic bypass + IP-intelligent routing active.</i>"
    )
    await update.message.reply_html(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={bridge_url}")]]))
