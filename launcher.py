"""Launches FastAPI web gateway and Telegram bot together."""
import asyncio
import logging
import os
import uvicorn
from bot.config import config
from bot.main import build_application
from web.server import app as fastapi_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("launcher")


async def run_bot() -> None:
    while True:
        application = None
        try:
            application = build_application()
            await application.initialize()
            await application.start()
            await application.updater.start_polling(
                drop_pending_updates=True,
                timeout=30,
            )
            logger.info("Telegram bot started in polling mode.")
            while True:
                await asyncio.sleep(3600)
        except Exception as exc:
            logger.exception("Bot crashed: %s. Restarting in 15s...", exc)
            try:
                if application is not None:
                    if application.updater and application.updater.running:
                        await application.updater.stop()
                    if application.running:
                        await application.stop()
                    await application.shutdown()
            except Exception:
                pass
            await asyncio.sleep(15)


async def run_web() -> None:
    server_config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        log_level="info",
        loop="asyncio",
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def main() -> None:
    mode = (config.RUN_MODE or "both").lower()
    tasks = []
    if mode in ("both", "web"):
        tasks.append(asyncio.create_task(run_web()))
    if mode in ("both", "bot"):
        tasks.append(asyncio.create_task(run_bot()))
    if not tasks:
        raise SystemExit("RUN_MODE must be web/bot/both")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
