"""User-facing Telegram handlers — professional UI with back buttons & inline editing."""
from __future__ import annotations
import logging
import uuid
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import config
from bot.database import db

logger = logging.getLogger(__name__)


def kb(rows):
    return InlineKeyboardMarkup(rows)


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🛠️ Setup APIs", callback_data="menu:setup"),
            InlineKeyboardButton("📊 My Stats", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("🔗 My Links", callback_data="menu:links"),
            InlineKeyboardButton("💎 Premium", callback_data="menu:premium"),
        ],
        [InlineKeyboardButton("📖 How to Use", callback_data="menu:help")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("🛡️ Admin Panel", callback_data="adm:home")])
    return InlineKeyboardMarkup(rows)


def back_kb(target: str = "menu:home") -> InlineKeyboardMarkup:
    return kb([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def setup_kb() -> InlineKeyboardMarkup:
    return kb([
        [InlineKeyboardButton("🔗 GPLinks", callback_data="setup:gplinks"),
         InlineKeyboardButton("⚡ LinkShortify", callback_data="setup:linkshortify")],
        [InlineKeyboardButton("🗑️ Clear API", callback_data="setup:clear")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:home")],
    ])


WELCOME_TEXT = (
    "<b>💎 Welcome to LinkMaster Prime, {name}!</b>\n\n"
    "<i>The world's most advanced link management system.</i>\n\n"
    "✨ <b>Direct Bypass:</b> Enabled\n"
    "⚡ <b>Engine:</b> Ultra-Fast\n"
    "🔒 <b>Security:</b> Military Grade\n\n"
    "📨 <i>Send me any URL to generate a premium bridge link.</i>"
)


def is_admin(uid: int) -> bool:
    return uid == config.ADMIN_TELEGRAM_ID


async def _send_or_edit(update: Update, text: str, markup: InlineKeyboardMarkup):
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await db.upsert_user(user.id, user.username, user.first_name)
    text = WELCOME_TEXT.format(name=html.escape(user.first_name or "friend"))
    await _send_or_edit(update, text, main_menu_kb(is_admin(user.id)))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>📖 How to Use</b>\n\n"
        "<b>Step 1.</b> Tap <b>🛠️ Setup APIs</b> and choose your shortener.\n"
        "<b>Step 2.</b> Send your API key when prompted.\n"
        "<b>Step 3.</b> Drop any URL — I'll generate a bridge link with bypass + IP-aware monetization.\n\n"
        "<b>Commands</b>\n"
        "• /start — main menu\n"
        "• /stats — your stats\n"
        "• /setapi &lt;gplinks|linkshortify&gt; &lt;KEY&gt;\n"
        "• /cancel — cancel current action\n\n"
        "<i>Premium features unlock unlimited monetization splits.</i>"
    )
    await _send_or_edit(update, text, back_kb())


async def stats_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await db.get_user(update.effective_user.id) or {}
    api_set = "✅ Configured" if user.get("shortener_api_key") else "❌ Not set"
    text = (
        "<b>📊 Your Stats</b>\n\n"
        f"👤 <b>User:</b> <code>{update.effective_user.id}</code>\n"
        f"🔗 <b>Links shortened:</b> <b>{user.get('total_shortened', 0)}</b>\n"
        f"⚙️ <b>Shortener:</b> <code>{user.get('shortener_type') or 'gplinks'}</code>\n"
        f"🔑 <b>API:</b> {api_set}\n"
    )
    await _send_or_edit(update, text, back_kb())


async def my_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    rows = await db.list_user_links(uid, limit=10)
    if not rows:
        text = "<b>🔗 My Links</b>\n\n<i>You haven't created any links yet. Send a URL to get started.</i>"
    else:
        lines = ["<b>🔗 My Recent Links</b>\n"]
        base = config.BASE_WEB_URL.rstrip("/")
        for r in rows:
            bridge = f"{base}/v/{r['bridge_code']}"
            orig = html.escape((r.get("original_url") or "")[:60])
            lines.append(f"• <a href=\"{bridge}\">{r['bridge_code']}</a> → <i>{orig}</i>")
        text = "\n".join(lines)
    await _send_or_edit(update, text, back_kb())


async def premium_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>💎 Premium Membership</b>\n\n"
        "Unlock the full power of LinkMaster Prime:\n\n"
        "✨ Unlimited links per day\n"
        "🚀 Priority redirect engine\n"
        "🛡️ Advanced bypass strategies\n"
        "📊 Detailed click analytics\n"
        "🎯 Custom bridge codes\n\n"
        f"💬 Contact admin: <a href=\"tg://user?id={config.ADMIN_TELEGRAM_ID}\">Open chat</a>"
    )
    await _send_or_edit(update, text, back_kb())


async def setup_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await db.get_user(update.effective_user.id) or {}
    cur_type = user.get("shortener_type") or "—"
    cur_key = user.get("shortener_api_key")
    masked = (cur_key[:4] + "•" * 6 + cur_key[-3:]) if cur_key else "❌ none"
    text = (
        "<b>🛠️ API Setup</b>\n\n"
        f"Current shortener: <code>{cur_type}</code>\n"
        f"Current key: <code>{html.escape(masked)}</code>\n\n"
        "Choose a provider to set or update your API key:"
    )
    await _send_or_edit(update, text, setup_kb())


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
    await update.message.reply_html(
        f"✅ <b>API saved.</b>\n⚙️ Type: <code>{stype}</code>",
        reply_markup=main_menu_kb(is_admin(update.effective_user.id)),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("await_api", None)
    context.user_data.pop("await_broadcast", None)
    context.user_data.pop("await_admin_api", None)
    context.user_data.pop("await_ban", None)
    context.user_data.pop("await_unban", None)
    await update.message.reply_html("✅ Cancelled.", reply_markup=main_menu_kb(is_admin(update.effective_user.id)))


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    if data == "menu:home":
        user = update.effective_user
        text = WELCOME_TEXT.format(name=html.escape(user.first_name or "friend"))
        await _send_or_edit(update, text, main_menu_kb(is_admin(user.id)))
    elif data == "menu:setup":
        await setup_view(update, context)
    elif data == "menu:stats":
        await stats_view(update, context)
    elif data == "menu:links":
        await my_links(update, context)
    elif data == "menu:premium":
        await premium_view(update, context)
    elif data == "menu:help":
        await help_cmd(update, context)
    elif data.startswith("setup:"):
        action = data.split(":", 1)[1]
        if action == "clear":
            await db.set_user_api(q.from_user.id, None, "gplinks")
            await q.answer("API cleared", show_alert=False)
            await setup_view(update, context)
        else:
            context.user_data["await_api"] = action
            text = (
                f"<b>🔑 Send your {action} API key</b>\n\n"
                "Just paste the key as a message. /cancel to abort."
            )
            await _send_or_edit(update, text, back_kb("menu:setup"))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    uid = update.effective_user.id

    if context.user_data.get("await_api"):
        stype = context.user_data.pop("await_api")
        await db.set_user_api(uid, text, stype)
        await update.message.reply_html(
            f"✅ <b>{stype} API saved.</b>",
            reply_markup=main_menu_kb(is_admin(uid)),
        )
        return

    if context.user_data.get("await_broadcast") and is_admin(uid):
        context.user_data.pop("await_broadcast")
        users = await db.all_user_ids()
        sent = 0
        failed = 0
        for u in users:
            try:
                await context.bot.send_message(u, text, parse_mode="HTML", disable_web_page_preview=True)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_html(f"📣 Broadcast complete.\n✅ Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>")
        return

    if context.user_data.get("await_admin_api") and is_admin(uid):
        stype = context.user_data.pop("await_admin_api")
        await db.update_setting("admin_shortener_type", stype)
        await db.update_setting("admin_api_key", text)
        await update.message.reply_html(f"✅ Admin <code>{stype}</code> API updated.")
        return

    if context.user_data.get("await_ban") and is_admin(uid):
        context.user_data.pop("await_ban")
        try:
            target = int(text)
            await db.set_banned(target, True)
            await update.message.reply_html(f"🚫 User <code>{target}</code> banned.")
        except ValueError:
            await update.message.reply_text("Invalid user id.")
        return

    if context.user_data.get("await_unban") and is_admin(uid):
        context.user_data.pop("await_unban")
        try:
            target = int(text)
            await db.set_banned(target, False)
            await update.message.reply_html(f"✅ User <code>{target}</code> unbanned.")
        except ValueError:
            await update.message.reply_text("Invalid user id.")
        return

    if text.startswith(("http://", "https://")):
        await handle_link(update, context, text)
        return

    await update.message.reply_html(
        "❓ <i>I didn't understand that. Send a URL or use the menu.</i>",
        reply_markup=main_menu_kb(is_admin(uid)),
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    uid = update.effective_user.id
    user = await db.get_user(uid) or {}
    if user.get("is_banned"):
        await update.message.reply_text("⛔ You are banned from using this bot.")
        return
    settings = await db.get_settings()
    if settings.get("maintenance_mode") and not is_admin(uid):
        await update.message.reply_html("🛠️ <b>Bot is under maintenance.</b> Try again shortly.")
        return

    bridge_code = uuid.uuid4().hex[:8]
    await db.create_link(uid, url, bridge_code)
    await db.increment_user_count(uid)
    bridge_url = f"{config.BASE_WEB_URL.rstrip('/')}/v/{bridge_code}"
    text = (
        "✅ <b>Link Processed Successfully!</b>\n\n"
        f"🔗 <b>Original:</b>\n<code>{html.escape(url)}</code>\n\n"
        f"🚀 <b>Your Bridge:</b>\n<code>{bridge_url}</code>\n\n"
        "<i>Automatic bypass + IP-intelligent monetization active.</i>"
    )
    await update.message.reply_html(
        text=text,
        disable_web_page_preview=True,
        reply_markup=kb([
            [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={bridge_url}"),
             InlineKeyboardButton("🔗 Open", url=bridge_url)],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:home")],
        ]),
    )
