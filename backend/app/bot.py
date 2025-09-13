# backend/app/bot.py (Исправленная версия)

import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties # ✨ ДОБАВЛЕН НОВЫЙ ИМПОРТ
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

import db

# --- Конфигурация через переменные окружения ---
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID_STR = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID_STR:
    raise ValueError("BOT_TOKEN и CHAT_ID должны быть установлены в переменных окружения")

CHAT_ID = int(CHAT_ID_STR)

# --- ✨ ИЗМЕНЕНИЕ: Инициализация Бота по-новому ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# --- Функция для отправки уведомления о новом опросе ---
async def send_new_poll_notification(poll_id: int):
    """Отправляет сообщение с кнопками для ставок в чат."""
    poll = db.get_poll(poll_id)
    if not poll:
        return

    text = f"📊 Новый опрос!\n\n"
    text += f"{hbold(poll['question'])}\n\n"
    text += f"💰 Мин. ставка: {poll.get('min_bet_amount', 'N/A')} монет"

    buttons = []
    for option in poll['options']:
        callback_data = f"bet:{poll['id']}:{option['id']}"
        buttons.append([
            InlineKeyboardButton(text=option['option_text'], callback_data=callback_data)
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await bot.send_message(chat_id=CHAT_ID, text=text, reply_markup=keyboard)


# --- Обработчик нажатий на кнопки ставок ---
@dp.callback_query(lambda c: c.data and c.data.startswith('bet:'))
async def process_bet_callback(query: CallbackQuery):
    """Ловит нажатия на кнопки со ставками."""
    try:
        action, poll_id_str, option_id_str = query.data.split(':')
        poll_id = int(poll_id_str)
        option_id = int(option_id_str)
        telegram_id = query.from_user.id
        
        poll = db.get_poll(poll_id)
        if not poll:
            await query.answer("❌ Ошибка: Опрос не найден.", show_alert=True)
            return
            
        min_bet = poll.get('min_bet_amount', 1)

        result = db.place_bet(telegram_id, poll_id, option_id, amount=min_bet)

        if result.get("ok"):
            user = db.get_user(telegram_id)
            await query.answer(f"✅ Ставка в {min_bet} монет принята! Ваш баланс: {user['balance']} монет.", show_alert=True)
        else:
            await query.answer(f"❌ Ошибка: {result.get('error')}", show_alert=True)

    except Exception as e:
        print(f"Error in callback: {e}")
        await query.answer("Произошла ошибка при обработке ставки.", show_alert=True)


# --- Функция для запуска бота ---
async def start_bot():
    """Запускает long polling для бота."""
    await dp.start_polling(bot)