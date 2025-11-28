import os
import logging
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC

logger = logging.getLogger(__name__)


class MetadataService:
    def __init__(self):
        self.supported_formats = ['.mp3']

    async def add_metadata(self, audio_path: str, track_info, cover_path: str = None) -> str:
        """Добавление метаданных к аудио файлу"""
        if not audio_path.endswith('.mp3'):
            return audio_path

        try:
            audio = MP3(audio_path, ID3=ID3)

            # Создаем теги если их нет
            try:
                audio.add_tags()
            except Exception:
                pass  # Теги уже существуют

            # 🔧 ИСПРАВЛЕНИЕ: Проверяем тип track_info
            if isinstance(track_info, dict):
                # Если передан словарь
                title = track_info.get('title', 'Unknown Title')
                artist = track_info.get('artist', 'Unknown Artist')
                album = track_info.get('album')
            else:
                # Если передан объект с атрибутами
                title = getattr(track_info, 'title', 'Unknown Title')
                artist = getattr(track_info, 'artist', 'Unknown Artist')
                album = getattr(track_info, 'album', None)

            # Основные теги
            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TPE1(encoding=3, text=artist))

            if album:
                audio.tags.add(TALB(encoding=3, text=album))

            # Добавление обложки
            if cover_path and os.path.exists(cover_path):
                await self._add_cover(audio, cover_path)

            audio.save()
            logger.info(f"Метаданные успешно добавлены к файлу: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Ошибка добавления метаданных: {e}")
            return audio_path

    async def _add_cover(self, audio, cover_path: str):
        """Добавление обложки к аудио файлу"""
        try:
            with open(cover_path, 'rb') as cover_file:
                cover_data = cover_file.read()

            audio.tags.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,  # Обложка альбома
                desc='Cover',
                data=cover_data
            ))
            logger.info(f"Обложка успешно добавлена к файлу")
        except Exception as e:
            logger.error(f"Ошибка добавления обложки: {e}")