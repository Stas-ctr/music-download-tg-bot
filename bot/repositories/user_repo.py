from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import User

class UserRepository():
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, telegram_id: int):
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, username: str, telegram_id: int):
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            return user
        else:
            user = User(username = username, telegram_id = telegram_id)
            self.session.add(user)
            await self.session.commit()
            return user