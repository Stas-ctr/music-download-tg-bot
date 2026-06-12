from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Download

class DownloadRepository():
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id:int, track_id: int):
        download = Download(user_id = user_id, track_id = track_id)
        self.session.add(download)
        await self.session.commit()
        return download

    async def get_stats(self):
        result = await self.session.execute(
            select(Download.track_id, func.count(Download.id)).group_by(Download.track_id)
        )
        return result.all()