import os
import asyncio
import aiofiles
import aiohttp
from typing import Optional
from dataclasses import dataclass
import logging
import requests

logger = logging.getLogger(__name__)


@dataclass
class ProcessedTrack:
    """Обработанный трек с путями к файлам"""
    audio_path: str
    cover_path: Optional[str]
    track_info: object  # TrackInfo объект
    
    async def cleanup(self):
        """Очистка временных файлов"""
        files_to_remove = [self.audio_path]
        if self.cover_path and os.path.exists(self.cover_path):
            files_to_remove.append(self.cover_path)
            # Также удаляем thumb файл, если он был создан
            thumb_path = self.cover_path.replace('.jpg', '_thumb.jpg')
            if os.path.exists(thumb_path):
                files_to_remove.append(thumb_path)
        
        for file_path in files_to_remove:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Удален временный файл: {file_path}")
                except Exception as e:
                    logger.error(f"Ошибка удаления {file_path}: {e}")


class AudioProcessor:
    def __init__(self, storage_path: str = "storage"):
        self.storage_path = storage_path
        self.audio_path = os.path.join(storage_path, "audio")
        self.covers_path = os.path.join(storage_path, "covers")
        self.temp_path = os.path.join(storage_path, "temp")

        # Создание директорий
        os.makedirs(self.audio_path, exist_ok=True)
        os.makedirs(self.covers_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)

    async def download_and_process(self, track_info):
        """Полный процесс скачивания и обработки трека"""
        # Поддержка как словарей, так и объектов TrackInfo
        if isinstance(track_info, dict):
            title = track_info.get('title', 'Unknown')
            artist = track_info.get('artist', 'Unknown')
        else:
            title = getattr(track_info, 'title', 'Unknown')
            artist = getattr(track_info, 'artist', 'Unknown')
        
        logger.info(f"Начинаю обработку трека: {title} - {artist}")

        try:
            # Скачивание аудио
            audio_path = await self._download_audio(track_info)
            logger.info(f"Аудио скачано: {audio_path}")

            # Скачивание обложки
            cover_path = None
            thumbnail = track_info.get('thumbnail') if isinstance(track_info, dict) else getattr(track_info, 'thumbnail', None)
            if thumbnail:
                cover_path = await self._download_cover(track_info)
                logger.info(f"Обложка скачана: {cover_path}")

            return ProcessedTrack(
                audio_path=audio_path,
                cover_path=cover_path,
                track_info=track_info
            )

        except Exception as e:
            logger.error(f"Ошибка обработки трека: {e}")
            raise

    async def _download_audio(self, track_info) -> str:
        """Скачивание аудио файла"""
        # Поддержка как словарей, так и объектов TrackInfo
        if isinstance(track_info, dict):
            source = track_info.get('source', 'unknown')
            track_id = track_info.get('id', 'unknown')
            url = track_info.get('url')
        else:
            source = getattr(track_info, 'source', 'unknown')
            track_id = getattr(track_info, 'id', 'unknown')
            url = getattr(track_info, 'url')
        
        filename = f"{source}_{track_id}.mp3"
        filepath = os.path.join(self.audio_path, filename)

        # Если файл уже существует, возвращаем его
        if os.path.exists(filepath):
            logger.info(f"Аудио файл уже существует: {filepath}")
            return filepath

        logger.info(f"Скачиваю аудио с: {url}")
        
        # Проверяем, что URL валидный
        if not url or not url.startswith('http'):
            error_msg = f"Некорректный URL для скачивания: {url}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Проверяем, что URL содержит путь к файлу
        if '/get/music/' not in url:
            logger.warning(f"URL не содержит '/get/music/': {url}. Возможно, это не прямой URL файла.")

        # Заголовки для имитации браузера
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://rus.hitmotop.com/',
            'Origin': 'https://rus.hitmotop.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'audio',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }

        # Пробуем сначала через aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        async with aiofiles.open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        logger.info(f"Аудио успешно скачано: {filepath}")
                        return filepath
                    elif response.status == 403:
                        logger.warning(f"HTTP 403 при скачивании через aiohttp, пробую через requests")
                        raise Exception("HTTP 403")
                    elif response.status == 404:
                        error_msg = f"Файл не найден (HTTP 404): {url}"
                        logger.error(error_msg)
                        raise FileNotFoundError(error_msg)
                    else:
                        error_msg = f"Ошибка скачивания аудио: HTTP {response.status}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
        except Exception as e:
            if "403" in str(e) or "HTTP 403" in str(e):
                # Если получили 403, пробуем через requests с сессией
                logger.info("Пробую скачать через requests с сессией")
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self._download_with_requests, url, filepath, headers)
            else:
                raise

    def _download_with_requests(self, url: str, filepath: str, headers: dict) -> str:
        """Скачивание через requests с сессией (для обхода 403)"""
        session = requests.Session()
        session.headers.update(headers)
        
        try:
            response = session.get(url, stream=True, timeout=30)
            
            if response.status_code == 404:
                error_msg = f"Файл не найден (HTTP 404): {url}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Аудио успешно скачано через requests: {filepath}")
            return filepath
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Ошибка скачивания через requests: {e}")
            raise
        finally:
            session.close()

    async def _download_cover(self, track_info) -> str:
        """Скачивание обложки альбома"""
        # Поддержка как словарей, так и объектов TrackInfo
        if isinstance(track_info, dict):
            thumbnail = track_info.get('thumbnail')
            source = track_info.get('source', 'unknown')
            track_id = track_info.get('id', 'unknown')
        else:
            thumbnail = getattr(track_info, 'thumbnail', None)
            source = getattr(track_info, 'source', 'unknown')
            track_id = getattr(track_info, 'id', 'unknown')
        
        if not thumbnail:
            raise ValueError("Нет ссылки на обложку")

        filename = f"cover_{source}_{track_id}.jpg"
        filepath = os.path.join(self.covers_path, filename)

        logger.info(f"Скачиваю обложку с: {thumbnail}")

        # Заголовки для имитации браузера
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://rus.hitmotop.com/',
            'Origin': 'https://rus.hitmotop.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail, headers=headers) as response:
                if response.status == 200:
                    async with aiofiles.open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    logger.info(f"Обложка успешно скачана: {filepath}")
                    return filepath
                else:
                    error_msg = f"Ошибка скачивания обложки: HTTP {response.status}"
                    logger.error(error_msg)
                    raise Exception(error_msg)