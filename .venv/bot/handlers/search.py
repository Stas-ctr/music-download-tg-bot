import html
import os
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import FSInputFile

from services.downloader import MusicDownloader
from services.audio_processor import AudioProcessor
from services.redis_services import music_redis

from utils.keyboards import create_tracks_keyboard

logger = logging.getLogger(__name__)

router = Router()


class SearchStates(StatesGroup):
    waiting_query = State()


@router.message(Command("search"))
async def cmd_search(message: types.Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_query)
    await message.answer(
        "🎵 <b>Введите название трека</b>"
    )


@router.message(Command("cancel"))
async def cancel_search(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Поиск отменен")


@router.message(SearchStates.waiting_query, F.text)
async def handle_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("❌ Слишком короткий запрос")
        return

    await state.clear()
    await process_search(message, query)


async def process_search(message: types.Message, query: str):
    """Основной процесс поиска и отправки треков"""
    try:
        status_msg = await message.answer(f"🔍 Ищу треки для: <b>{html.escape(query)}</b>...")
        logger.info(f"Начинаю поиск треков для: {query}")

        # Используем загрузчик для поиска
        downloader = MusicDownloader()
        tracks = await downloader.search_tracks(query, limit=20)

        await music_redis.save_search_results(user_id, query, tracks)

        total_pages = await music_redis.get_total_pages(user_id, query)
        current_tracks = await music_redis.get_tracks_page(user_id, query, 0)

        keyboard = create_tracks_keyboard(current_tracks, user_id, query, 0,total_pages)

        await message.answer(
            f"🔍 Найдено {len(tracks)} треков по запросу: <b>{query}</b>\n"
            f"📄 Страница 1/{total_pages}",
            reply_markup=keyboard
        )
        # # Обработка каждого трека
        # success_count = 0
        # for i, track in enumerate(tracks, 1):
        #     try:
        #         await send_track_to_user(message, track, i)
        #         success_count += 1
        #         logger.info(f"Успешно отправлен трек {i}: {track.title} - {track.artist}")
        #
        #     except FileNotFoundError as e:
        #         # Файл не найден (404) - пропускаем без сообщения пользователю
        #         logger.warning(f"Трек недоступен (404): {track.title} - {track.artist}. Пропускаю.")
        #         continue
        #     except Exception as e:
        #         error_msg = (
        #             f"⚠️ Ошибка с треком <b>{html.escape(track.title)}</b>:\n"
        #             f"{html.escape(str(e))}"
        #         )
        #         await message.answer(error_msg)
        #         logger.error(f"Ошибка обработки трека {track.title}: {e}")
        #
        # if success_count > 0:
        #     await message.answer(f"✅ Успешно отправлено {success_count} трек(ов)")
        # else:
        #     await message.answer("❌ Не удалось отправить ни одного трека")

    except Exception as e:
        error_msg = f"❌ Ошибка поиска: {html.escape(str(e))}"
        await message.answer(error_msg)
        logger.error(f"Критическая ошибка в process_search: {e}")


