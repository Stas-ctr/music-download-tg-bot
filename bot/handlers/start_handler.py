from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repo import UserRepository
from core.logger import logger
import html

router = Router()

CYBER_LINE = "═" * 24

HELP_TEXT = f"""<code>{CYBER_LINE}</code>
  ◆ МУЗЫКАЛЬНЫЙ БОТ v2.0
<code>{CYBER_LINE}</code>

  ▸ Просто напиши название песни
    или имя исполнителя

  ▸ Нажми на трек в списке

  ▸ Получи MP3 файл

  ▸ /history — последние запросы
  ▸ /help — эта справка

<code>{CYBER_LINE}</code>
  ▸ powered by ▓▓▓ MUS_OS ▓▓▓
<code>{CYBER_LINE}</code>"""


@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    repo = UserRepository(session)
    user = await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    safe_name = html.escape(message.from_user.first_name or "")
    text = f"""<code>{CYBER_LINE}</code>
  ◆ СИСТЕМА ГОТОВА К РАБОТЕ
<code>{CYBER_LINE}</code>

  Привет, <b>{safe_name}</b>

  Напиши название песни или
  имя исполнителя — я найду
  и скачаю музыку для тебя.

<code>{CYBER_LINE}</code>
  ▸ /help — справка
<code>{CYBER_LINE}</code>"""

    await message.answer(text, parse_mode="HTML")


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")
