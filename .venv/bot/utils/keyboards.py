from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from pydantic.v1.validators import enum_validator


def create_tracks_keyboard(tracks: list, user_id: int, query: str, current_page: int, total_pages: int):
    builder = InlineKeyboardBuilder()

    for i, track in enumerate(tracks):
        track_title = track['title'][:25]+"..." if len(track['title'])> 25 else track['title']
        track_artist = track['artist'][:15]+"..."if len(track['artist'])> 25 else track['artist']

        builder.button(
            text=f"🎵{track_title} - {track_artist}",
            callback_data=f"select: {user_id}:{query}:{current_page}:{i}"
        )

        pagination_row = []
        if current_page > 0:
            pagination_row.append(
                types.InlineKeyboardButton(
                    text="⬅️Назад",
                    callback_data=f"page:{user_id}:{query}:{current_page-1}"
                )
            )

        pagination_row.append(
            types.InlineKeyboardButton(
                text="❌Отмена",
                callback_data=f"cancel:{user_id}"
            )
        )

        if  current_page< total_pages - 1:
            pagination_row.append(
                types.InlineKeyboardButton(
                    text="Вперед➡️",
                    callback_data=f"page:{user_id}:{query}:{current_page+1}"
                )

            )

        builder.row(*pagination_row)

        builder.row(
            types.InlineKeyboardButton(
                text=f"Страница{current_page+1} из {total_pages}",
                callback_data="page_info"
            )
        )

        return builder.as_markup()

    def create_download_keyboard(track_url:str, track_title:str):
        builder = InlineKeyboardBuilder()

        builder.button(
            text="⬇️Скачать трек",
            callback_data=f"download:{track_url}"
        )

        builder.button(
            text="🔍Новый поиск",
            callback_data="new search"
        )

        builder.adjust(1)

        return builder.as_markup()