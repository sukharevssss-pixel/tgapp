import os
import asyncio
from datetime import datetime, timedelta
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

import db
from db import DB_PATH 

# --- Конфигурация ---
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID_STR = os.environ.get("CHAT_ID")
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS")
BACKEND_URL = os.environ.get("BACKEND_URL")

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
    poll = db.get_poll(poll_id)
    if not poll: return None
    status = "🔴 СТАВКИ ЗАКРЫТЫ" if not poll['is_open'] else "🟢 СТАВКИ ПРИНИМАЮТСЯ"
    text = f"📊 <b>Опрос #{poll['id']}</b> | {status}\n\n"
    text += f"<b>{poll['question']}</b>\n\n"
    total_pool = sum(opt['total_bet'] for opt in poll['options'])
    text += f"💰 Общий банк: {total_pool} монет\n\n"
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

# --- ОТПРАВКА И ОБРАБОТКА КНОПОК ---
async def send_new_poll_notification(poll_id: int):
    text = format_poll_text(poll_id)
    poll = db.get_poll(poll_id)
    if not text or not poll:
        return

    fixed_bets = [100, 200, 500]
    keyboard_rows = []
    
    for option in poll['options']:
        button_row = []
        for amount in fixed_bets:
            callback_data = f"bet:{poll['id']}:{option['id']}:{amount}"
            button_text = f"{option['option_text']} - {amount}"
            button_row.append(
                InlineKeyboardButton(text=button_text, callback_data=callback_data)
            )
        keyboard_rows.append(button_row)
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    sent_message = await bot.send_message(chat_id=CHAT_ID, text=text, reply_markup=keyboard)
    db.set_poll_message_id(poll_id, sent_message.message_id)

@dp.callback_query(lambda c: c.data and c.data.startswith('bet:'))
async def process_bet_callback(query: CallbackQuery):
    try:
        _, poll_id_str, option_id_str, amount_str = query.data.split(':')
        poll_id = int(poll_id_str)
        option_id = int(option_id_str)
        amount = int(amount_str)
        telegram_id = query.from_user.id
        username = query.from_user.username or f"user{telegram_id}"

        db.ensure_user(telegram_id, username)
        result = db.place_bet(telegram_id, poll_id, option_id, amount)

        if result.get("ok"):
            await query.answer(f"✅ Ваша ставка в {amount} монет принята!", show_alert=False)
            new_text = format_poll_text(poll_id)
            if new_text:
                # Обновляем сообщение, сохраняя кнопки
                await bot.edit_message_text(new_text, query.message.chat.id, query.message.message_id, reply_markup=query.message.reply_markup)
        else:
            await query.answer(f"❌ Ошибка: {result.get('error')}", show_alert=True)

    except Exception as e:
        print(f"Error in bet callback: {e}")
        await query.answer("Произошла ошибка при обработке ставки.", show_alert=True)

# --- КОМАНДЫ БОТА ---
@dp.message(Command("bet"))
async def create_poll_command(message: Message):
    try:
        lines = message.text.strip().split('\n')
        if len(lines) < 3: raise ValueError("Invalid format")
        question, options = lines[1], lines[2:]
        if len(options) < 2: raise ValueError("Minimum 2 options required.")
        db.ensure_user(message.from_user.id, message.from_user.username or f"user{message.from_user.id}")
        poll_id = db.create_poll(message.from_user.id, question, options)
        await send_new_poll_notification(poll_id)
    except (ValueError, IndexError):
        await message.reply("❌ <b>Неверный формат.</b>\nИспользуйте многострочный формат:\n<code>/bet\nВопрос\nВариант 1\nВариант 2</code>")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message(Command("p"))
async def place_bet_command(message: Message):
    try:
        args = message.text.split()
        if len(args) < 4: raise ValueError("Invalid format")
        poll_id, amount, option_text = int(args[1]), int(args[-1]), " ".join(args[2:-1])
        db.ensure_user(message.from_user.id, message.from_user.username or f"user{message.from_user.id}")
        poll = db.get_poll(poll_id)
        if not poll: return await message.reply("❌ Опрос с таким ID не найден.")
        target_option = next((opt for opt in poll['options'] if opt['option_text'].lower() == option_text.lower()), None)
        if not target_option: return await message.reply("❌ Вариант ответа не найден.")
        result = db.place_bet(message.from_user.id, poll_id, target_option['id'], amount)
        if result.get("ok"):
            await message.reply("✅ Ваша ставка принята!")
            if poll.get('message_id'):
                new_text = format_poll_text(poll_id)
                if new_text:
                    await bot.edit_message_text(new_text, CHAT_ID, poll['message_id'])
        else:
            await message.reply(f"❌ {result.get('error')}")
    except (ValueError, IndexError):
        await message.reply("❌ <b>Неверный формат.</b>\nИспользуйте: <code>/p ID Текст_варианта Сумма</code>\n<b>Пример:</b> <code>/p 1 Команда А 123</code>")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message(Command("close"))
async def close_poll_command(message: Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3: raise ValueError("Invalid format")
        poll_id, winning_option_text = int(args[1]), args[2]
        result = db.close_poll(message.from_user.id, poll_id, winning_option_text)
        if not result.get("ok"): raise ValueError(result.get("error"))
        winners = result.get('winners', [])
        response_text = f"🎉 <b>Опрос #{poll_id} завершен!</b>\n🏆 Победил вариант: <b>{result['winning_option_text']}</b>\n\n"
        if not winners:
            response_text += "Никто не угадал исход."
        else:
            response_text += "Поздравляем победителей:\n"
            for winner in winners:
                response_text += f" - <b>{winner['username']}</b> выигрывает <b>{winner['payout']}</b> монет!\n"
        await bot.send_message(CHAT_ID, response_text)
        poll = db.get_poll(poll_id)
        if poll and poll.get('message_id'):
            final_text = format_poll_text(poll_id)
            if final_text:
                await bot.edit_message_text(final_text, CHAT_ID, poll['message_id'], reply_markup=None)
    except (ValueError, IndexError):
        await message.reply("❌ <b>Неверный формат.</b>\nИспользуйте: <code>/close ID Текст_победителя</code>\n<b>Пример:</b> <code>/close 1 Команда А</code>")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message(Command("winrate"))
async def winrate_command(message: Message):
    rating = db.get_rating(limit=10)
    text = "🏆 <b>Топ-10 игроков по проценту побед:</b>\n\n"
    if not rating:
        text += "Пока нет данных для рейтинга."
    else:
        for i, user in enumerate(rating, 1):
            text += f"{i}. <b>{user['username']}</b> - {user['winrate']}% ({user['wins']} W / {user['losses']} L)\n"
    await message.answer(text)

# --- ФОНОВЫЕ ЗАДАЧИ ---
last_backup_time = None
async def scheduler():
    global last_backup_time
    print("--- Планировщик запущен ---")
    while True:
        await asyncio.sleep(60 * 10)
        if BACKEND_URL:
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{BACKEND_URL}/health")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Пинг самого себя для поддержания активности прошел успешно.")
            except Exception as e:
                print(f"Ошибка само-пинга: {e}")
        should_backup = False
        if last_backup_time is None or (datetime.now() - last_backup_time).total_seconds() > 86400:
            should_backup = True
        if should_backup:
            try:
                print("--- Создание резервной копии базы данных... ---")
                if os.path.exists(DB_PATH):
                    backup_file = FSInputFile(DB_PATH)
                    backup_caption = f"🗓️ Резервная копия бд\nот {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    await bot.send_document(chat_id=ADMIN_IDS[0], document=backup_file, caption=backup_caption)
                    last_backup_time = datetime.now()
                    print("✅ Резервная копия успешно отправлена.")
                else:
                    print("⚠️ Файл бд не найден для создания бэкапа.")
            except Exception as e:
                print(f"❌ Ошибка при создании бэкапа: {e}")
        try:
            polls_to_close = db.auto_close_due_polls()
            for poll in polls_to_close:
                try:
                    new_text = format_poll_text(poll['id'])
                    if poll.get('message_id') and new_text:
                        await bot.edit_message_text(new_text, CHAT_ID, poll['message_id'], reply_markup=None)
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