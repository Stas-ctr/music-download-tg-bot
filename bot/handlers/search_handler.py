import uuid
import html
from aiogram import Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from services.parser import search_tracks
from core.config import settings
from core.redis import get_cache, set_cache, add_to_history, set_search_session
from core.logger import logger
import aiohttp

router = Router()

CYBER_LINE = "═" * 24
CYBER_ICON = "▓"
MAX_STORE = 30
TRACKS_PER_PAGE = 5


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "??:??"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


@router.message()
async def search_handler(message: Message, hitmotop_session: aiohttp.ClientSession):
    query = message.text
    if not query or len(query) > 200:
        await message.answer("❌ Некорректный запрос")
        return

    if not hitmotop_session:
        await message.answer("Ошибка соединения, попробуйте позже")
        return

    cached = await get_cache(query)
    if cached:
        tracks = cached
    else:
        try:
            tracks = await search_tracks(query, hitmotop_session)
        except Exception as e:
            await message.answer("Ошибка поиска, попробуй позже")
            logger.error("search_error", query=query, error=str(e))
            return

        if tracks:
            await set_cache(query, tracks)

    if not tracks:
        await message.answer("Ничего не найдено 😔")
        return

    logger.info("search", query=query, user_id=message.from_user.id, count=len(tracks))
    await add_to_history(message.from_user.id, query)

    search_id = uuid.uuid4().hex[:8]
    results = tracks[:MAX_STORE]
    await set_search_session(search_id, results)

    total_pages = max(1, -(-len(results) // TRACKS_PER_PAGE))
    page_tracks = results[:TRACKS_PER_PAGE]

    buttons = []
    for i, track in enumerate(page_tracks):
        dur = _format_duration(track.get("duration"))
        label = f"{CYBER_ICON} {track['artist']} — {track['title']} [{dur}]"
        if len(label) > 64:
            label = label[:61] + "..."
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"tr:{search_id}:{i + 1}")
        ])

    nav = []
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text="Вперед ▶", callback_data=f"pg:{search_id}:1"))
    buttons.append(nav)

    safe_query = html.escape(query)
    header = (
        f"<code>{CYBER_LINE}</code>\n"
        f"  ◆ ПОИСК: <b>{safe_query}</b>\n"
        f"  ◆ Найдено: <b>{len(results)}</b> треков\n"
        f"<code>{CYBER_LINE}</code>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
