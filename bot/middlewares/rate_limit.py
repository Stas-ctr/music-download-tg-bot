from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from core.redis import check_rate_limit
from core.logger import logger


class RateLimitMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user_id = data.get("event_from_user")
        if user_id is None:
            return await handler(event, data)
        user_id = user_id.id

        if isinstance(event, CallbackQuery):
            return await handler(event, data)

        allowed = await check_rate_limit(user_id)
        if not allowed:
            if isinstance(event, Message):
                await event.answer("⚠️ Слишком много запросов. Подожди немного.")
            logger.warning("rate_limited", user_id=user_id)
            return None

        return await handler(event, data)
