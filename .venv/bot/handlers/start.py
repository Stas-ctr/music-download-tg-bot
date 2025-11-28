import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    welcome_text = (
        "🎵 <b>Музыкальный бот</b>\n\n"
        "Отправь мне название трека или исполнителя для поиска.\n"
        "Например: <code>Lil NasX Old Town Road</code>\n\n"
        "Доступные команды:\n"
        "/search - поиск музыки\n"
        "/help - помощь"
    )
    await message.answer(welcome_text)
    logger.info(f"Пользователь {message.from_user.id} запустил бота")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "🤖 <b>Как пользоваться ботом:</b>\n\n"
        "1. <b>Команда /search</b> - активирует режим поиска\n"
        "   Затем вводи названия треков один за другим\n\n"
        "2. <b>Отмена</b> - /cancel для выхода из любого режима\n\n"
        "📝 <b>Что умеет бот:</b>\n"
        "• Искать музыку по названию и исполнителю\n"
        "• Скачивать треки в высоком качестве"
    )
    await message.answer(help_text)
    logger.info(f"Пользователь {message.from_user.id} запросил помощь")