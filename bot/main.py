"""Application factory for the Telegram bot."""
from __future__ import annotations
import logging
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from bot.config import config
from bot.handlers import (
    start, help_cmd, setapi, stats_view, handle_message, callback_router, cancel,
)
from bot.admin import admin_panel, admin_callback, setadminapi

logger = logging.getLogger(__name__)


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("setapi", setapi))
    app.add_handler(CommandHandler("stats", stats_view))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("setadminapi", setadminapi))

    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^adm:"))
    app.add_handler(CallbackQueryHandler(callback_router, pattern=r"^(menu|setup):"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
