import asyncio
import socket
import aiohttp

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.session.aiohttp import AiohttpSession
from typing import Callable, Awaitable, Any
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.logger import setup_logging, logger
from core.database import engine, Base, async_session
from core.redis import init_redis, close_redis
from models.models import User, Track, Download
from handlers import start_handler, search_handler, download_handler, history_handler, admin_handler
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.auth import AuthMiddleware
from middlewares.logging import LoggingMiddleware


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)


class HitmotopSessionMiddleware(BaseMiddleware):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__()
        self.session = session

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        data["hitmotop_session"] = self.session
        return await handler(event, data)


async def main():
    setup_logging()
    logger.info("bot_starting")

    await init_redis()
    logger.info("redis_connected")

    hitmotop_headers = {
        "User-Agent": settings.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://rus.hitmotop.com/",
        "Connection": "keep-alive",
    }
    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300, enable_cleanup_closed=True, family=socket.AF_INET)
    hitmotop_session = aiohttp.ClientSession(
        headers=hitmotop_headers, connector=connector,
        proxy=settings.PROXY_URL,
    )
    try:
        async with hitmotop_session.get(
            "https://rus.hitmotop.com/",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            logger.info("hitmotop_cookies", status=resp.status, proxy=settings.PROXY_URL or "none")
    except Exception as e:
        logger.error("hitmotop_init_failed", error=str(e))

    from aiogram.client.telegram import TelegramAPIServer
    if settings.TELEGRAM_API_URL and settings.TELEGRAM_API_URL != "https://api.telegram.org":
        custom_api = TelegramAPIServer.from_base(settings.TELEGRAM_API_URL)
        bot_session = AiohttpSession(api=custom_api, timeout=300)
    else:
        bot_session = AiohttpSession(timeout=300)
    bot_session._connector_init["family"] = socket.AF_INET

    bot = Bot(token=settings.BOT_TOKEN, session=bot_session)
    dp = Dispatcher()

    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(AuthMiddleware())
    dp.update.middleware(RateLimitMiddleware())
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(HitmotopSessionMiddleware(hitmotop_session))

    dp.include_router(start_handler.router)
    dp.include_router(search_handler.router)
    dp.include_router(download_handler.router)
    dp.include_router(history_handler.router)
    dp.include_router(admin_handler.router)

    try:
        while True:
            try:
                await dp.start_polling(bot, timeout=5)
            except Exception as e:
                logger.error("polling_crashed", error=str(e))
                await asyncio.sleep(5)
                continue
            break
    finally:
        await hitmotop_session.close()
        await close_redis()
        await engine.dispose()
        logger.info("bot_stopped")


asyncio.run(main())
