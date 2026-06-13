import asyncio
import aiohttp
import socket
import sys
sys.path.insert(0, '/app')

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

BOT_TOKEN = "8341360696:AAHn9QFP5IuUqV6_4hRBdC0DXqffMYYgZ8w"
BASE_URL = "https://tg-proxy.syperstad.workers.dev"

async def test():
    print("=== Test 1: Bot with base_url, default session ===")
    bot1 = Bot(token=BOT_TOKEN, base_url=BASE_URL)
    try:
        me = await bot1.get_me()
        print(f"  getMe OK: {me.username}")
    except Exception as e:
        print(f"  getMe FAILED: {e}")
    finally:
        await bot1.session.close()

    print("\n=== Test 2: Bot with base_url + custom session ===")
    session2 = AiohttpSession(timeout=30)
    bot2 = Bot(token=BOT_TOKEN, base_url=BASE_URL, session=session2)
    try:
        me = await bot2.get_me()
        print(f"  getMe OK: {me.username}")
    except Exception as e:
        print(f"  getMe FAILED: {e}")
    finally:
        await bot2.session.close()

    print("\n=== Test 3: Bot with base_url + start_polling check ===")
    session3 = AiohttpSession(timeout=30)
    bot3 = Bot(token=BOT_TOKEN, base_url=BASE_URL, session=session3)
    dp = Dispatcher()
    try:
        print("  Calling getUpdates directly...")
        updates = await bot3.get_updates(timeout=1, offset=-1)
        print(f"  getUpdates OK: {len(updates)} updates")
    except Exception as e:
        print(f"  getUpdates FAILED: {type(e).__name__}: {e}")
    finally:
        await bot3.session.close()

    print("\n=== Test 4: Check actual URL being called ===")
    session4 = AiohttpSession(timeout=30)
    bot4 = Bot(token=BOT_TOKEN, base_url=BASE_URL, session=session4)
    print(f"  bot.base_url = {bot4.base_url}")
    print(f"  bot.api = {bot4.api}")
    print(f"  bot.api.base_url = {bot4.api.base_url}")
    await bot4.session.close()

asyncio.run(test())
