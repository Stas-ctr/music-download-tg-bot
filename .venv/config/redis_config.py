import redis.asyncio as redis
from config.settings import settings


class RedisManager:
    def __init__(self):
        self.redis = None

    async def init_redis(self):
        """Инициализация подключения к Redis"""
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            encoding='utf-8'
        )

        await self.redis.ping()
        print("✅ Redis подключен")
        return self.redis

    async def close(self):
        """Закрытие подключения"""
        if self.redis:
            await self.redis.close()


# Глобальный экземпляр
redis_manager = RedisManager()