from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Track

class TrackRepository():
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_url(self, track_url: str):
        result = await self.session.execute(
            select(Track).where(Track.download_url == track_url)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, title:str, artist:str, duration:int, cover_url: str, download_url: str):
        result = await self.session.execute(
            select(Track).where(Track.download_url == download_url)
        )
        track = result.scalar_one_or_none()

        if track:
            return track
        else:
            track = Track(title = title,artist = artist, duration = duration, cover_url=cover_url, download_url=download_url)
            self.session.add(track)
            await self.session.commit()
            return track