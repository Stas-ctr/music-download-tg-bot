import os
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from services.redis_services import music_redis
from handlers import routers

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

Bot_Token = os.getenv("BotToken")

if not Bot_Token:
    raise ValueError("BotToken не найден в переменных окружения!")

bot = Bot(token=Bot_Token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


async def main():
    """Основная функция запуска бота"""
    await music_redis.init_redis()

    storage = MemoryStorage()

    dp.include_router(search_router)
    dp.include_router(callbacks_router)
    
    logger.info("✨ Запуск бота...")
    logger.info("✅ Бот запущен. Используйте команду /search в Telegram.")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())