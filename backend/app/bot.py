# backend/app/bot.py (полностью переработанная версия)

import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic, hcode
from dotenv import load_dotenv
import db

# --- Конфигурация ---
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
# Замените на ID тех, кто может управлять ботом
ADMIN_IDS = [359469476] 

# --- Инициализация ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- ФОРМАТИРОВАНИЕ СООБЩЕНИЙ ---
def format_poll_text(poll_id: int) -> str:
    """Формирует текст для сообщения с опросом."""
    poll = db.get_poll(poll_id)
    if not poll: return "Опрос не найден."

    status = "🔴 СТАВКИ ЗАКРЫТЫ" if not poll['is_open'] else "🟢 СТАВКИ ПРИНИМАЮТСЯ"
    
    text = f"📊 <b>Опрос #{poll['id']}</b> | {status}\n\n"
    text += f"<b>{poll['question']}</b>\n\n"
    
    total_pool = sum(opt['total_bet'] for opt in poll['options'])
    text += f"💰 Общий банк: {total_pool} монет\n"
    text += f"💵 Мин. ставка: {poll['min_bet_amount']}\n\n"
    text += "<b>Варианты и ставки:</b>\n"

    bets = db.get_bets_for_poll(poll_id) # (нужно будет добавить эту функцию в db.py)
    
    for opt in poll['options']:
        text += f"  - {opt['option_text']} ({opt['total_bet']} монет)\n"
        # Показываем, кто поставил на этот вариант
        bettors = [b for b in bets if b['option_id'] == opt['id']]
        if bettors:
            for bettor in bettors:
                text += f"      <i>└ {bettor['username']}: {bettor['amount']} монет</i>\n"
    
    closes_at_str = datetime.fromisoformat(poll['closes_at']).strftime('%H:%M')
    text += f"\n<i>Ставки закроются в {closes_at_str}</i>"
    return text

# --- КОМАНДЫ БОТА ---
@dp.message(Command("bet"))
async def create_poll_command(message: types.Message):
    # ... (логика создания опроса, как в предыдущем ответе) ...

@dp.message(Command("p"))
async def place_bet_command(message: types.Message):
    # ... (логика размещения ставки) ...

@dp.message(Command("close"))
async def close_poll_command(message: types.Message):
    # ... (логика закрытия опроса) ...

@dp.message(Command("winrate"))
async def winrate_command(message: types.Message):
    # ... (логика показа винрейта) ...

# --- ФОНОВЫЕ ЗАДАЧИ ---
async def scheduler():
    """Каждую минуту проверяет, не пора ли закрыть какие-то опросы."""
    while True:
        await asyncio.sleep(60)
        polls_to_close = db.auto_close_due_polls()
        for poll in polls_to_close:
            try:
                new_text = format_poll_text(poll['id'])
                await bot.edit_message_text(new_text, CHAT_ID, poll['message_id'])
            except Exception as e:
                print(f"Не удалось обновить сообщение для опроса #{poll['id']}: {e}")

# --- ЗАПУСК ---
async def start_bot():
    # Запускаем планировщик в фоновом режиме
    asyncio.create_task(scheduler())
    # Запускаем long polling для бота
    await dp.start_polling(bot)

# Дополните db.py функцией get_bets_for_poll
def get_bets_for_poll(poll_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.option_id, b.amount, u.username 
        FROM bets b 
        JOIN users u ON u.telegram_id = b.telegram_id 
        WHERE b.poll_id = ?
    """, (poll_id,))
    bets = [dict(row) for row in cur.fetchall()]
    conn.close()
    return bets