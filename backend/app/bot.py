import os
import asyncio
from datetime import datetime, timedelta
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

import db
from db import DB_PATH 

# --- Конфигурация ---
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID_STR = os.environ.get("CHAT_ID")
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS")
BACKEND_URL = os.environ.get("BACKEND_URL") # URL для само-пинга

if not all([BOT_TOKEN, CHAT_ID_STR, ADMIN_IDS_STR]):
    raise ValueError("BOT_TOKEN, CHAT_ID, и ADMIN_IDS должны быть установлены")

try:
    CHAT_ID = int(CHAT_ID_STR)
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',')]
except (ValueError, TypeError):
    raise ValueError("CHAT_ID и ADMIN_IDS должны быть числами")

# --- Инициализация ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- ФОРМАТИРОВАНИЕ СООБЩЕНИЙ ---
def format_poll_text(poll_id: int) -> str | None:
    # ... (код этой функции без изменений)
    poll = db.get_poll(poll_id)
    if not poll: return None
    status = "🔴 СТАВКИ ЗАКРЫТЫ" if not poll['is_open'] else "🟢 СТАВКИ ПРИНИМАЮТСЯ"
    text = f"📊 <b>Опрос #{poll['id']}</b> | {status}\n\n"
    text += f"<b>{poll['question']}</b>\n\n"
    total_pool = sum(opt['total_bet'] for opt in poll['options'])
    text += f"💰 Общий банк: {total_pool} монет\n"
    text += f"💵 Мин. ставка: {poll['min_bet_amount']}\n\n"
    text += "<b>Варианты и ставки:</b>\n"
    bets = db.get_bets_for_poll(poll_id)
    for opt in poll['options']:
        text += f"  - {opt['option_text']} ({opt['total_bet']} монет)\n"
        bettors = [b for b in bets if b['option_id'] == opt['id']]
        if bettors:
            for bettor in bettors:
                text += f"      <i>└ {bettor['username']}: {bettor['amount']} монет</i>\n"
    if poll.get('closes_at'):
        closes_at_str = datetime.fromisoformat(poll['closes_at']).strftime('%H:%M')
        text += f"\n<i>Ставки закроются в {closes_at_str}</i>"
    return text

# --- КОМАНДЫ БОТА ---
@dp.message(Command("bet"))
async def create_poll_command(message: Message):
    # ... (код этой функции без изменений)
    
@dp.message(Command("p"))
async def place_bet_command(message: Message):
    # ... (код этой функции без изменений)

@dp.message(Command("close"))
async def close_poll_command(message: Message):
    # ... (код этой функции без изменений)

@dp.message(Command("winrate"))
async def winrate_command(message: Message):
    # ... (код этой функции без изменений)

# --- ФОНОВЫЕ ЗАДАЧИ ---
last_backup_time = None

async def scheduler():
    global last_backup_time
    print("--- Планировщик запущен ---")
    
    while True:
        await asyncio.sleep(60) # Проверка каждую минуту
        
        # --- Блок само-пинга для поддержания активности ---
        if BACKEND_URL:
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{BACKEND_URL}/health")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Пинг самого себя для поддержания активности прошел успешно.")
            except Exception as e:
                print(f"Ошибка само-пинга: {e}")

        # --- Блок создания бэкапов (раз в 24 часа) ---
        should_backup = False
        if last_backup_time is None:
            should_backup = True
        elif (datetime.now() - last_backup_time).total_seconds() > 86400: # 24 часа
            should_backup = True
        
        if should_backup:
            try:
                print("--- Создание резервной копии базы данных... ---")
                if os.path.exists(DB_PATH):
                    backup_file = FSInputFile(DB_PATH)
                    backup_caption = f"🗓️ Резервная копия базы данных\nот {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    await bot.send_document(chat_id=ADMIN_IDS[0], document=backup_file, caption=backup_caption)
                    last_backup_time = datetime.now()
                    print("✅ Резервная копия успешно отправлена.")
                else:
                    print("⚠️ Файл базы данных не найден для создания бэкапа.")
            except Exception as e:
                print(f"❌ Ошибка при создании бэкапа: {e}")
        
        # --- Блок автоматического закрытия опросов ---
        try:
            polls_to_close = db.auto_close_due_polls()
            for poll in polls_to_close:
                try:
                    new_text = format_poll_text(poll['id'])
                    if poll.get('message_id') and new_text:
                        await bot.edit_message_text(new_text, CHAT_ID, poll['message_id'])
                except Exception as e:
                    print(f"Не удалось обновить сообщение для опроса #{poll['id']}: {e}")
        except Exception as e:
            print(f"Ошибка в планировщике (закрытие опросов): {e}")

# --- ЗАПУСК БОТА ---
async def start_bot():
    try:
        me = await bot.get_me()
        print(f"--- Бот @{me.username} успешно авторизован ---")
    except Exception as e:
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Не удалось подключиться к Telegram. Проверьте BOT_TOKEN. Ошибка: {e}")
        return

    print("--- Запуск планировщика и опроса Telegram ---")
    asyncio.create_task(scheduler())
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Бот упал во время работы с ошибкой: {e}")
    finally:
        print("!!! Бот ЗАВЕРШИЛ работу.")