from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from core.redis import get_history
import html

router = Router()

CYBER_LINE = "═" * 24


@router.message(Command("history"))
async def history_handler(message: Message):
    user_id = message.from_user.id
    history = await get_history(user_id)

    if not history:
        await message.answer(
            f"<code>{CYBER_LINE}</code>\n"
            f"  ◆ ИСТОРИЯ ПУСТА\n"
            f"<code>{CYBER_LINE}</code>",
            parse_mode="HTML",
        )
        return

    lines = [f"  ▸ {html.escape(q)}" for q in history]
    text = (
        f"<code>{CYBER_LINE}</code>\n"
        f"  ◆ ИСТОРИЯ ЗАПРОСОВ\n"
        f"<code>{CYBER_LINE}</code>\n"
        + "\n".join(lines) + "\n"
        f"<code>{CYBER_LINE}</code>"
    )
    await message.answer(text, parse_mode="HTML")
