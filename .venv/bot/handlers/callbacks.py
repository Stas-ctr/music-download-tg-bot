from re import search

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from services.redis_service import music_redis
from utils.keyboards import create_tracks_keyboard, create_download_keyboard

router = Router()

@router.callback_query(F.data.startswith("page"))
async def handle_page_change(callback: types.CallbackQuery):
    try:
        _, user_id, query, page_num = callback.data.split(";")
        user_id = int(user_id)
        page_num = int(page_num)

        tracks = await music_redis.get_tracks_pages(user_id, query, page_num)
        total_pages = await music_redis.get_total_pages(user_id, query)

        if not tracks:
            await callback("Нет данных для этой страницы")
            return
        new_keyboard = create_tracks_keyboard(tracks, user_id, query, page_num, total_pages)
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        await callback.answer()

    except Exception as e:
        await callback.answer("Ошибка при переключении страницы")

@router.callback_query(F.data.startswith("select:"))
async def handle_track_select(callback: types.CallbackQuery):
    try:
        _, user_id, query, page_num, track_index = callback.data.split(":")
        user_id = int(user_id)
        page_num = int(page_num)
        track_index = int(track_index)

        search_data = await music_redis.get_search_results(user_id, query)
        if not search_data:
            await callback.answer("❌Данные устарели")
            return

        # Вычисляем реальный индекс трека
        real_index = (page_num * 5) + track_index
        if real_index >= len(search_data['tracks']):
            await callback.answer("❌Трек не найден")
            return
        track = search_data['tracks'][real_index]

        await callback.message.edit_text(
            f"🎵 <b>Выбран трек:</b>\n"
            f"<b>Название:</b> {track['title']}\n"
            f"<b>Исполнитель:</b> {track['artist']}\n"
            f"⏳ Скачиваю...",
            reply_markup=create_download_keyboard(track['url'], track['title'])
        )

        await send_track_to_user(message, track)


        await callback.answer()

    except Exception as e:
        await callback.answer("❌ Ошибка при выборе трека")

async def send_track_to_user(message: types.Message, track, track_number: int):
    """Отправка трека пользователю"""
    processor = AudioProcessor()

    try:
        # Скачиваем и обрабатываем трек
        processed_track = await processor.download_and_process(track)

        if not processed_track:
            raise Exception("Не удалось обработать трек")

        # Отправляем аудио
        if processed_track.cover_path and os.path.exists(processed_track.cover_path):
            await message.answer_audio(
                audio=FSInputFile(processed_track.audio_path),
                thumb=FSInputFile(processed_track.cover_path),
                title=processed_track.track_info.title[:64],
                performer=processed_track.track_info.artist[:64]
            )
        else:
            await message.answer_audio(
                audio=FSInputFile(processed_track.audio_path),
                title=processed_track.track_info.title[:64],
                performer=processed_track.track_info.artist[:64]
            )

        # Очистка временных файлов
        await processed_track.cleanup()

    except Exception as e:
        # Убедимся, что файлы очищены даже при ошибке
        if 'processed_track' in locals():
            try:
                await processed_track.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Ошибка при очистке файлов: {cleanup_error}")
        logger.error(f"Ошибка отправки трека: {e}")
        raise
@router.callback_query(F.data.startswith("cancel:"))
async def handle_cancel(callback: types.CallbackQuery):
    """Обработчик отмены"""
    await callback.message.edit_text("❌ Поиск отменен")
    await callback.answer()


@router.callback_query(F.data == "new_search")
async def handle_new_search(callback: types.CallbackQuery):
    """Обработчик нового поиска"""
    await callback.message.edit_text("🎵 <b>Введите название песни:</b>")
    await callback.answer()