from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, Integer, String, DateTime, ForeignKey
from sqlalchemy.exc import DataError
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class User(Base):
    __tablename__ = "users"

    telegram_id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username:Mapped[str | None] = mapped_column(String, nullable=True)
    is_active:Mapped[bool] = mapped_column(Boolean, default=True)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    downloads:Mapped[list["Download"]] = relationship(back_populates="user")

class Track(Base):
    __tablename__ = "tracks"

    id: Mapped  [int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    artist: Mapped[str] = mapped_column(String)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    download_url: Mapped[str] = mapped_column(String, unique=True)
    file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    downloads: Mapped[list["Download"]] = relationship(back_populates="track")

class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("tracks.id"))
    download_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="downloads")
    track: Mapped["Track"] = relationship(back_populates="downloads")