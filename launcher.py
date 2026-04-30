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
    application = build_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot started in polling mode.")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


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
