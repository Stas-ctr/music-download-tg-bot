import time
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from core.logger import logger


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user_id = data.get("event_from_user")
        user_id = user_id.id if user_id else "unknown"

        if isinstance(event, Message) and event.text:
            logger.info("incoming", user_id=user_id, text=event.text[:100])
        elif isinstance(event, CallbackQuery):
            logger.info("callback", user_id=user_id, data=event.data[:100])

        start = time.perf_counter()
        result = await handler(event, data)
        elapsed = round((time.perf_counter() - start) * 1000, 1)

        logger.info("handled", user_id=user_id, ms=elapsed)
        return result
