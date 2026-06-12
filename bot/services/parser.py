import json
import re
from urllib.parse import quote
import aiohttp
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from core.config import settings
from core.logger import logger

BASE_URL = "https://rus.hitmotop.com/search?q={}"


def _score_track(query: str, track: dict) -> float:
    q = query.lower().strip()
    artist = (track.get("artist") or "").lower()
    title = (track.get("title") or "").lower()
    combined = f"{artist} {title}"

    score_artist = fuzz.partial_ratio(q, artist)
    score_title = fuzz.partial_ratio(q, title)
    score_combined = fuzz.token_sort_ratio(q, combined)

    return max(score_artist, score_title, score_combined)


def _generate_alt_queries(query: str) -> list[str]:
    q = re.sub(r"[^\w\s]", "", query).strip()
    if not q:
        return []

    words = q.split()
    alts = []

    if len(words) > 1:
        alts.append(" ".join(reversed(words)))

    for w in words:
        if len(w) > 2 and w not in alts:
            alts.append(w)

    return alts


async def _fetch_page(query: str, session: aiohttp.ClientSession) -> str:
    url = BASE_URL.format(quote(query))
    for attempt in range(2):
        try:
            async with session.get(
                url,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status != 200:
                    logger.error("parser_bad_status", status=response.status, query=query)
                    return ""
                return await response.text()
        except aiohttp.ClientError as e:
            if attempt == 1:
                logger.error("parser_request_failed", error=str(e), query=query)
                return ""
            continue
    return ""


def _parse_tracks(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.tracks__item")

    if not items:
        return []

    tracks = []
    for item in items:
        meta = item.get("data-musmeta")
        if not meta:
            continue

        try:
            data = json.loads(meta)
        except json.JSONDecodeError:
            continue

        duration_raw = item.select_one(".track__fulltime")
        duration = None
        if duration_raw:
            parts = duration_raw.text.strip().split(":")
            if len(parts) == 2:
                try:
                    duration = int(parts[0]) * 60 + int(parts[1])
                except ValueError:
                    pass

        dl_btn = item.select_one("a.track__download-btn")
        dl_href = dl_btn.get("href", "") if dl_btn else ""
        if dl_href:
            download_url = f"https://rus.hitmotop.com{dl_href}" if dl_href.startswith("/") else dl_href
        else:
            raw_url = data.get("url", "")
            download_url = f"https://rus.hitmotop.com{raw_url}" if raw_url.startswith("/") else raw_url

        tracks.append({
            "title": data.get("title"),
            "artist": data.get("artist"),
            "download_url": download_url,
            "cover_url": data.get("img"),
            "duration": duration,
        })

    return [
        t for t in tracks
        if t["title"]
        and len(t["title"]) < 100
        and "ссылк" not in t["title"].lower()
        and "загрузк" not in t["title"].lower()
    ]


async def search_tracks(query: str, session: aiohttp.ClientSession) -> list[dict]:
    html = await _fetch_page(query, session)
    tracks = _parse_tracks(html)

    if not tracks:
        for alt in _generate_alt_queries(query):
            html = await _fetch_page(alt, session)
            tracks = _parse_tracks(html)
            if tracks:
                break

    for t in tracks:
        t["_score"] = _score_track(query, t)

    tracks.sort(key=lambda t: t["_score"], reverse=True)
    tracks = [t for t in tracks if t["_score"] > 25]

    for t in tracks:
        t.pop("_score", None)

    return tracks
