from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from core.config import settings
from core.redis import redis_client, is_banned, get_history
from core.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repo import UserRepository
from repositories.track_repo import TrackRepository
from repositories.download_repo import DownloadRepository
from sqlalchemy import select, func
from pathlib import Path
import html
import os
import sys
import signal

router = Router()

ENV_PATH = Path(__file__).parent.parent / ".env"


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def _update_env_token(new_token: str) -> bool:
    try:
        lines = ENV_PATH.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("BOT_TOKEN="):
                lines[i] = f"BOT_TOKEN={new_token}"
                break
        else:
            lines.append(f"BOT_TOKEN={new_token}")
        ENV_PATH.write_text("\n".join(lines) + "\n")
        return True
    except Exception as e:
        logger.error("env_update_failed", error=str(e))
        return False


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        "◆ <b>АДМИН-ПАНЕЛЬ</b>\n"
        "═══════════════\n\n"
        "▸ /stats — статистика\n"
        "▸ /ban &lt;id&gt; — забанить\n"
        "▸ /unban &lt;id&gt; — разбанить\n"
        "▸ /users — список пользователей\n"
        "▸ /token — сменить токен бота",
        parse_mode="HTML",
    )


@router.message(Command("stats"))
async def stats_handler(message: Message, session: AsyncSession):
    if not _is_admin(message.from_user.id):
        return

    from models.models import User, Track, Download
    user_count = await session.scalar(select(func.count(User.telegram_id)))
    track_count = await session.scalar(select(func.count(Track.id)))
    download_count = await session.scalar(select(func.count(Download.id)))

    await message.answer(
        f"◆ <b>СТАТИСТИКА</b>\n"
        f"═══════════════\n\n"
        f"▸ Пользователей: <b>{user_count or 0}</b>\n"
        f"▸ Треков в базе: <b>{track_count or 0}</b>\n"
        f"▸ Скачиваний: <b>{download_count or 0}</b>",
        parse_mode="HTML",
    )


@router.message(Command("token"))
async def token_handler(message: Message):
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or ":" not in parts[1]:
        await message.answer(
            "◆ <b>СМЕНА ТОКЕНА</b>\n"
            "═══════════════\n\n"
            "Использование:\n"
            "/token 123456789:ABCdefGHI...",
            parse_mode="HTML",
        )
        return

    new_token = parts[1].strip()
    if not _update_env_token(new_token):
        await message.answer("❌ Ошибка записи .env")
        return

    await message.answer("✅ Токен обновлён. Перезапуск...")
    logger.info("token_updated", admin=message.from_user.id)

    os.kill(os.getpid(), signal.SIGTERM)


@router.message(Command("ban"))
async def ban_handler(message: Message):
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /ban <user_id>")
        return

    target_id = int(parts[1])
    if target_id in settings.admin_ids:
        await message.answer("Нельзя забанить админа")
        return

    if redis_client:
        await redis_client.set(f"banned:{target_id}", "1")
    await message.answer(f"🚫 Пользователь {target_id} забанен")
    logger.warning("user_banned", admin=message.from_user.id, target=target_id)


@router.message(Command("unban"))
async def unban_handler(message: Message):
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /unban <user_id>")
        return

    target_id = int(parts[1])
    if redis_client:
        await redis_client.delete(f"banned:{target_id}")
    await message.answer(f"✅ Пользователь {target_id} разбанен")
    logger.info("user_unbanned", admin=message.from_user.id, target=target_id)


@router.message(Command("users"))
async def users_handler(message: Message, session: AsyncSession):
    if not _is_admin(message.from_user.id):
        return

    from models.models import User
    result = await session.execute(select(User).limit(20))
    users = result.scalars().all()

    if not users:
        await message.answer("Нет пользователей")
        return

    lines = []
    for u in users:
        status = "🚫" if await is_banned(u.telegram_id) else "✅"
        safe_name = html.escape(u.username or "нет")
        lines.append(f"  {status} {u.telegram_id} | @{safe_name}")

    text = (
        "◆ <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        "═══════════════\n"
        + "\n".join(lines) + "\n"
        "═══════════════"
    )
    await message.answer(text, parse_mode="HTML")
