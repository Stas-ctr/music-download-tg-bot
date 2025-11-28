import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass

from parsers.hitmotop import HitmotopParser

logger = logging.getLogger(__name__)



@dataclass
class TrackInfo:
    """Информация о треке"""
    source: str
    id: str
    title: str
    artist: str
    duration: int
    url: str
    thumbnail: Optional[str] = None
    album: Optional[str] = None
    relevance: float = 0.0


class MusicDownloader:
    def __init__(self):
        self.parsers = {
            'hitmotop': HitmotopParser()
        }
        self.active_parsers = ['hitmotop']  # Используем только Hitmotop для начала

    async def search_tracks(self, query: str, limit: int = 5) -> List[TrackInfo]:
        """Поиск треков по всем активным парсерам"""
        tasks = []

        for parser_name in self.active_parsers:
            parser = self.parsers[parser_name]
            tasks.append(self._safe_parser_search(parser, query, limit))

        # Запускаем все парсеры параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Собираем все успешные результаты
        all_tracks = []
        for result in results:
            if isinstance(result, list):
                all_tracks.extend(result)

        # Сортируем по релевантности и убираем дубликаты
        unique_tracks = self._remove_duplicates(all_tracks)
        sorted_tracks = sorted(unique_tracks, key=lambda x: x.relevance, reverse=True)

        return sorted_tracks[:limit]

    async def _safe_parser_search(self, parser, query: str, limit: int):
        """Безопасный поиск через парсер с обработкой ошибок"""
        try:
            results = await parser.search(query, limit)
            # Конвертируем словари в объекты TrackInfo, фильтруя None
            track_objects = []
            for track_dict in results:
                if track_dict is None:
                    logger.warning("Парсер вернул None для одного из треков, пропускаю")
                    continue
                if isinstance(track_dict, dict):
                    # Проверяем, что есть обязательные поля
                    if not track_dict.get('url') or not track_dict.get('title'):
                        logger.warning(f"Трек с неполными данными пропущен: {track_dict}")
                        continue
                    track_objects.append(TrackInfo(**track_dict))
                elif isinstance(track_dict, TrackInfo):
                    # Проверяем, что есть обязательные поля
                    if not track_dict.url or not track_dict.title:
                        logger.warning(f"TrackInfo с неполными данными пропущен: {track_dict.title}")
                        continue
                    track_objects.append(track_dict)
            return track_objects
        except Exception as e:
            logger.error(f"Ошибка в парсере {parser.__class__.__name__}: {e}")
            return []

    def _remove_duplicates(self, tracks: List[TrackInfo]) -> List[TrackInfo]:
        """Удаление дубликатов по названию и исполнителю"""
        seen = set()
        unique_tracks = []

        for track in tracks:
            key = (track.title.lower().strip(), track.artist.lower().strip())
            if key not in seen:
                seen.add(key)
                unique_tracks.append(track)

        return unique_tracks