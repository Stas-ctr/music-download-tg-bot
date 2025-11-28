import json
import asyncio
from typing import List, Dict, Optional
import redis.asyncio as redis

class MusicRedis:
    def __init__(self):
        self.redis = None
        self.serch_ttl = 3600

    async def init_redis(self):
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        await self.redis.ping()
        print("Redis подключен")
        return self.redis

    async def save_search_results(self, user_id: int, query: str, tracks: List[Dict]):
        """Сохраняет результаты поиска"""
        key = f"search:{user_id}:{query}"
        data = {
            'query': query,
            'tracks': tracks,
            'timestamp': asyncio.get_event_loop().time()
        }
        await self.redis.setex(key, self.search_ttl, json.dumps(data))
        return key

    async def get_search_results(self, user_id: int,query: str, tracks: List[Dict]):
        key = f"search:{user_id}:{query}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def get_tracks_page(self, user_id: int,query: str, page: int, page_size: int = 5)->List[Dict]:
        search_data = await self.get_search_results(user_id, query)
        if not search_data:
            return []

        tracks = search_data['tracks']
        start_idx = page*page_size
        end_idx = start_idx+page_size
        return tracks[start_idx:end_idx]
    async def get_total_pages(self, user_id: int, query: str, page_size: int=5)->int:
        search_data = await self.get_search_results(user_id,query)
        if not search_data:
            return 0

        total_tracks = len(search_data['tracks'])
        return (total_tracks + page_size - 1)//page_size
    async def close(self):
        if self.redis:
            await self.redis.close()

music_redis = MusicRedis()
