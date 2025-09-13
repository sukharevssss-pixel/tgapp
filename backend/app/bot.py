# backend/app/bot.py

import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv # ✨ Импортируем функцию

import db

# --- ✨ Конфигурация через переменные окружения ✨ ---
load_dotenv() # Загружаем переменные из .env файла (для локального запуска)

# os.environ.get() - это команда для чтения переменных окружения.
# Она будет работать и локально (благодаря load_dotenv), и на Render.com
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# ID чата нужно преобразовать в число
CHAT_ID = int(os.environ.get("CHAT_ID"))

# Проверка, что переменные загружены
if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Необходимо установить BOT_TOKEN и CHAT_ID в переменных окружения")

# --- Инициализация Бота ---
bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


# --- (остальной код файла bot.py остается БЕЗ ИЗМЕНЕНИЙ) ---

async def send_new_poll_notification(poll_id: int):
    # ...
    # (здесь ничего не меняется)
    # ...

@dp.callback_query(lambda c: c.data and c.data.startswith('bet:'))
async def process_bet_callback(query: CallbackQuery):
    # ...
    # (здесь ничего не меняется)
    # ...

async def start_bot():
    """Запускает long polling для бота."""
    await dp.start_polling(bot)