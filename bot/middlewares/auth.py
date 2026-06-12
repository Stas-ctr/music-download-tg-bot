from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from core.redis import is_banned
from core.logger import logger


class AuthMiddleware(BaseMiddleware):
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

        if await is_banned(user_id):
            if isinstance(event, Message):
                await event.answer("🚫 Доступ запрещён.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Доступ запрещён.", show_alert=True)
            logger.warning("blocked_user", user_id=user_id)
            return None

        return await handler(event, data)
