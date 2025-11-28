import os
import logging
import aiofiles
import aiohttp
from PIL import Image

logger = logging.getLogger(__name__)


async def download_file(url: str, filepath: str) -> str:
    """Асинхронное скачивание файла"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                return filepath
            else:
                raise Exception(f"Ошибка HTTP {response.status}")


async def resize_image_for_telegram(image_path: str, max_size: int = 320) -> str:
    """Изменение размера изображения для Telegram"""
    try:
        with Image.open(image_path) as img:
            # Конвертация в RGB если нужно
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Изменение размера с сохранением пропорций
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Сохранение в временный файл
            thumb_path = image_path.replace('.jpg', '_thumb.jpg')
            img.save(thumb_path, 'JPEG', quality=85)

            logger.info(f"Изображение изменено: {thumb_path}")
            return thumb_path
    except Exception as e:
        logger.error(f"Ошибка изменения размера изображения: {e}")
        return image_path  # Возвращаем оригинал если не удалось изменить размер