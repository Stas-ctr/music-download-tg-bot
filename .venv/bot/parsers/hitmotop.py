import re
import asyncio
import urllib.parse
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class HitmotopParser:
    def __init__(self):
        self.client = None
        self.timeout = 30
        self.base_url = "https://rus.hitmotop.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def init_client(self):
        """Инициализация HTTP клиента"""
        try:
            self.client = httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True
            )
            logger.info("HTTP клиент инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации клиента: {e}")
            raise

    async def search(self, query: str, limit: int = 5) -> List[dict]:
        """Поиск треков на Hitmotop"""
        if not self.client:
            await self.init_client()

        try:
            search_url = f"{self.base_url}/search"
            params = {"q": query}

            logger.info(f"Ищу треки: {query}")
            response = await self.client.get(search_url, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            tracks = soup.select('li.tracks__item')[:limit]
            results = []

            for i, track in enumerate(tracks, 1):
                try:
                    track_info = await self._parse_track_element(track, i)
                    if track_info:
                        results.append(track_info)
                except Exception as e:
                    logger.error(f"Ошибка парсинга трека {i}: {e}")
                    continue

            logger.info(f"Успешно найдено {len(results)} треков")
            return results

        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []

    async def _parse_track_element(self, track_element, index: int) -> Optional[dict]:
        """Парсинг отдельного элемента трека"""
        try:
            # Извлечение обложки
            cover_url = await self._extract_cover_url(track_element, index)

            # Извлечение названия и исполнителя
            title_element = track_element.select_one('div.track__title')
            artist_element = track_element.select_one('div.track__desc')

            if not title_element or not artist_element:
                logger.warning(f"Не найдены название или исполнитель для трека {index}")
                return None

            title = title_element.get_text(strip=True)
            artist = artist_element.get_text(strip=True)

            # Извлечение ссылки на скачивание
            download_url = await self._extract_download_url(track_element, title, artist)

            if not download_url:
                logger.warning(f"Не удалось получить URL для скачивания: {title} - {artist}")
                return None

            track_info = {
                'source': 'hitmotop',
                'id': f"hitmotop_{hash(title + artist)}_{index}",
                'title': title,
                'artist': artist,
                'duration': 0,
                'url': download_url,
                'thumbnail': cover_url,
                'relevance': 0.9 - (index * 0.1)
            }

            logger.debug(f"Парсинг трека успешен: {title} - {artist}")
            return track_info

        except Exception as e:
            logger.error(f"Ошибка парсинга элемента: {e}")
            return None

    async def _extract_download_url(self, track_element, title: str, artist: str) -> Optional[str]:
        """Извлечение URL для скачивания"""
        try:
            # Пробуем найти кнопку скачивания
            download_btn = track_element.select_one('a.track__download-btn')
            if not download_btn:
                logger.warning(f"Не найдена кнопка скачивания для: {title} - {artist}")
                return None

            # Пробуем разные атрибуты для получения URL
            download_url = (
                    download_btn.get('href') or
                    download_btn.get('data-url') or
                    download_btn.get('data-href')
            )

            # Если нашли URL в onclick
            if not download_url:
                onclick = download_btn.get('onclick')
                if onclick and 'get/music' in onclick:
                    url_match = re.search(r"https://[^\s'\"\)]+", onclick)
                    if url_match:
                        download_url = url_match.group(0)

            # Если URL относительный, делаем абсолютным
            if download_url and not download_url.startswith('http'):
                if download_url.startswith('/'):
                    download_url = self.base_url + download_url
                else:
                    download_url = self.base_url + '/' + download_url

            # Если все еще нет прямого URL, пробуем получить через страницу трека
            if download_url and '/get/music/' not in download_url:
                download_url = await self._get_download_url_from_track_page(download_url, title, artist)

            return download_url

        except Exception as e:
            logger.error(f"Ошибка извлечения URL скачивания: {e}")
            return None

    async def _get_download_url_from_track_page(self, track_page_url: str, title: str, artist: str) -> Optional[str]:
        """Получение URL скачивания со страницы трека"""
        try:
            logger.info(f"Пробуем получить прямой URL со страницы трека: {track_page_url}")

            response = await self.client.get(track_page_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем кнопку скачивания на странице трека
            download_btn = soup.select_one('a.track__download-btn, a[href*="/get/music/"]')
            if download_btn:
                download_url = (
                        download_btn.get('href') or
                        download_btn.get('data-url') or
                        download_btn.get('data-href')
                )

                # Если нашли URL в onclick
                if not download_url:
                    onclick = download_btn.get('onclick')
                    if onclick and 'get/music' in onclick:
                        url_match = re.search(r"https://[^\s'\"\)]+", onclick)
                        if url_match:
                            download_url = url_match.group(0)

                # Делаем URL абсолютным если нужно
                if download_url and not download_url.startswith('http'):
                    if download_url.startswith('/'):
                        download_url = self.base_url + download_url
                    else:
                        download_url = self.base_url + '/' + download_url

                if download_url and '/get/music/' in download_url:
                    logger.info(f"Найден прямой URL на странице трека: {download_url}")
                    return download_url

            logger.warning(f"Не удалось найти прямой URL на странице трека: {track_page_url}")
            return track_page_url  # Возвращаем оригинальный URL как fallback

        except Exception as e:
            logger.error(f"Ошибка получения URL со страницы трека: {e}")
            return track_page_url  # Возвращаем оригинальный URL как fallback

    async def _extract_cover_url(self, track_element, index: int) -> Optional[str]:
        """Извлечение URL обложки"""
        try:
            cover_element = track_element.select_one('div.track__img')
            if not cover_element:
                return None

            style = cover_element.get('style', '')
            url_match = re.search(r"https://[^']+\.(jpg|jpeg|png|webp)", style)

            if url_match:
                cover_url = url_match.group(0)
                logger.debug(f"Найдена обложка для трека {index}: {cover_url}")
                return cover_url
            else:
                logger.warning(f"Не удалось извлечь URL обложки для трека {index}")
                return None

        except Exception as e:
            logger.error(f"Ошибка извлечения обложки: {e}")
            return None

    async def close(self):
        """Закрытие клиента"""
        if self.client:
            await self.client.aclose()
            logger.info("HTTP клиент закрыт")