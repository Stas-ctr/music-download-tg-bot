import asyncio
import ipaddress
import socket
from urllib.parse import urlparse
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from core.redis import get_search_session
from repositories.download_repo import DownloadRepository
from repositories.track_repo import TrackRepository
from core.logger import logger
import aiohttp

router = Router()

CYBER_ICON = "▓"
TRACKS_PER_PAGE = 5
FAST_TIMEOUT = aiohttp.ClientTimeout(total=30, sock_connect=5, sock_read=25)
WORKING_CDNS = ["s1.deliciouspeaches.com", "s2.deliciouspeaches.com"]

ALLOWED_HOSTS = {"rus.hitmotop.com", "rus.hitmoz.org", "s1.deliciouspeaches.com", "s2.deliciouspeaches.com"}

PRIVATE_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def _is_safe_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        for net in PRIVATE_RANGES:
            if ip in net:
                return False
        return True
    except (socket.gaierror, ValueError):
        return False


async def _refresh_cookies(session: aiohttp.ClientSession):
    try:
        async with session.get(
            "https://rus.hitmotop.com/",
            timeout=aiohttp.ClientTimeout(total=8),
        ):
            pass
    except Exception:
        pass


async def _download_with_session(session: aiohttp.ClientSession, url: str) -> bytes | None:
    parsed = urlparse(url)
    if not _is_safe_host(parsed.hostname or ""):
        logger.warning("dl_ssrf_blocked", host=parsed.hostname)
        return None

    try:
        async with session.get(url, timeout=FAST_TIMEOUT, allow_redirects=True) as resp:
            final_url = str(resp.url)
            final_host = resp.url.host or ""

            if "deliciousoranges.com" in final_host or "hitmoz.org" in final_host:
                logger.info("dl_bad_cdn", host=final_host)
            elif resp.status == 200:
                data = await resp.read()
                if len(data) >= 1000:
                    logger.info("dl_ok", size=len(data), host=final_host)
                    return data
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass
    except Exception:
        pass

    for cdn in WORKING_CDNS:
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            cdn_url = urlunparse(parsed._replace(netloc=cdn))
            async with session.get(cdn_url, timeout=FAST_TIMEOUT, allow_redirects=True) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    if len(data) >= 1000:
                        logger.info("dl_ok_cdn", size=len(data), host=cdn)
                        return data
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue
        except Exception:
            continue

    return None


async def _download_file(
    session: aiohttp.ClientSession,
    url: str,
    max_retries: int = 3,
) -> bytes | None:
    for attempt in range(max_retries):
        if attempt > 0:
            await _refresh_cookies(session)
            await asyncio.sleep(1)

        data = await _download_with_session(session, url)
        if data:
            return data

        logger.warning("dl_failed", attempt=attempt + 1, url=url)

    return None


def _page_keyboard(search_id: str, page: int, total_pages: int, tracks: list[dict], start_idx: int) -> list[list]:
    buttons = []
    for i, track in enumerate(tracks):
        dur = track.get("duration")
        dur_str = f"{dur // 60}:{dur % 60:02d}" if dur else "??:??"
        label = f"{CYBER_ICON} {track['artist']} — {track['title']} [{dur_str}]"
        if len(label) > 64:
            label = label[:61] + "..."
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"tr:{search_id}:{start_idx + i}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"pg:{search_id}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"• {page + 1}/{total_pages} •", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперед ▶", callback_data=f"pg:{search_id}:{page + 1}"))
    buttons.append(nav)

    return buttons


@router.callback_query(F.data.startswith("pg:"))
async def page_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return

    search_id = parts[1]
    try:
        page = int(parts[2])
    except ValueError:
        await callback.answer()
        return

    tracks = await get_search_session(search_id)
    if not tracks:
        await callback.answer("⚠️ Результаты устарели", show_alert=True)
        return

    total_pages = max(1, -(-len(tracks) // TRACKS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    start = page * TRACKS_PER_PAGE
    page_tracks = tracks[start : start + TRACKS_PER_PAGE]

    buttons = _page_keyboard(search_id, page, total_pages, page_tracks, start)
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("tr:"))
async def download_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    hitmotop_session: aiohttp.ClientSession,
):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    search_id = parts[1]
    try:
        track_index = int(parts[2]) - 1
    except ValueError:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    tracks = await get_search_session(search_id)
    if not tracks or track_index < 0 or track_index >= len(tracks):
        await callback.answer("⚠️ Результаты устарели, найди заново", show_alert=True)
        return

    track = tracks[track_index]

    logger.info("downloading_track", user_id=callback.from_user.id, title=track["title"])

    track_repo = TrackRepository(session)
    download_repo = DownloadRepository(session)

    db_track = await track_repo.get_by_url(track["download_url"])
    if db_track and db_track.file_id:
        await callback.message.answer_audio(
            db_track.file_id,
            title=db_track.title,
            performer=db_track.artist,
        )
        await download_repo.create(user_id=callback.from_user.id, track_id=db_track.id)
        await callback.answer()
        return

    await callback.answer(f"⬇ {track['title']}")
    status_msg = await callback.message.answer(f"▓░░░░ Загружаю: {track['title'][:40]}...")

    audio_bytes = await _download_file(hitmotop_session, track["download_url"])

    if not audio_bytes:
        try:
            await status_msg.edit_text("❌ CDN недоступен, попробуй другой трек")
        except Exception:
            pass
        return

    if len(audio_bytes) > 50 * 1024 * 1024:
        try:
            await status_msg.edit_text("❌ Файл слишком большой")
        except Exception:
            pass
        return

    try:
        await status_msg.edit_text("▓▓▓▓▓▓▓▓▓▓ Отправляю...")
    except Exception:
        pass

    audio = BufferedInputFile(
        audio_bytes,
        filename=f"{track['artist']} - {track['title']}.mp3",
    )
    sent = await callback.message.answer_audio(
        audio,
        title=track["title"],
        performer=track["artist"],
    )

    try:
        await status_msg.delete()
    except Exception:
        pass

    logger.info("track_sent", user_id=callback.from_user.id, title=track["title"])

    db_track = await track_repo.get_or_create(
        title=track["title"],
        artist=track["artist"],
        duration=track.get("duration"),
        cover_url=track.get("cover_url"),
        download_url=track["download_url"],
    )
    if not db_track.file_id:
        db_track.file_id = sent.audio.file_id
        await session.commit()

    await download_repo.create(user_id=callback.from_user.id, track_id=db_track.id)
