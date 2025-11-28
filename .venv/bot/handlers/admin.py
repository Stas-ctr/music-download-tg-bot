import logging
from aiogram import Router, types
from aiogram.filters import Command

logger = logging.getLogger(__name__)

# Временная заглушка для settings и database функций
# TODO: Реализовать настройки и базу данных
ADMIN_IDS = ["@NoWayWarrior"]  # Добавьте ID администраторов здесь

async def get_user_stats():
    """Заглушка для получения статистики пользователей"""
    return {
        'total_users': 0,
        'total_downloads': 0,
        'total_queries': 0
    }

async def get_popular_queries(limit: int = 10):
    """Заглушка для получения популярных запросов"""
    return []

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Команда для получения статистики бота (только для администраторов)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        logger.warning(f"Попытка доступа к статистике от пользователя {message.from_user.id}")
        return

    try:
        stats = await get_user_stats()
        popular_queries = await get_popular_queries(limit=10)

        stats_text = "📊 <b>Статистика бота</b>\n\n"
        stats_text += f"👥 Всего пользователей: {stats['total_users']}\n"
        stats_text += f"🎵 Всего скачиваний: {stats['total_downloads']}\n"
        stats_text += f"🔍 Всего запросов: {stats['total_queries']}\n\n"

        if popular_queries:
            stats_text += "🔝 Популярные запросы:\n"
            for i, (query, count) in enumerate(popular_queries, 1):
                stats_text += f"{i}. {query} - {count}\n"
        else:
            stats_text += "🔝 Популярные запросы пока отсутствуют"

        await message.answer(stats_text)
        logger.info(f"Статистика отправлена администратору {message.from_user.id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {str(e)}")
        logger.error(f"Ошибка получения статистики: {e}")