import os
import asyncio
from datetime import datetime, timedelta, timezone
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv
import google.generativeai as genai
import io
from PIL import Image
from aiogram.types import PhotoSize

import db
from db import DB_PATH 

# --- Конфигурация ---
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID_STR = os.environ.get("CHAT_ID")
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS")
BACKEND_URL = os.environ.get("BACKEND_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not all([BOT_TOKEN, CHAT_ID_STR, ADMIN_IDS_STR, GEMINI_API_KEY]):
    raise ValueError("Все необходимые переменные окружения (BOT_TOKEN, CHAT_ID, ADMIN_IDS, GEMINI_API_KEY) должны быть установлены")

try:
    CHAT_ID = int(CHAT_ID_STR)
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',')]
except (ValueError, TypeError):
    raise ValueError("CHAT_ID и ADMIN_IDS должны быть числами")

# --- Инициализация AI моделей Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

# --- Инициализация Бота ---
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
        moscow_tz = timezone(timedelta(hours=3))
        utc_closes_at = datetime.fromisoformat(poll['closes_at'])
        msk_closes_at = utc_closes_at.astimezone(moscow_tz)
        closes_at_str = msk_closes_at.strftime('%H:%M')
        text += f"\n<i>Ставки закроются в {closes_at_str} по МСК</i>"
    return text

# --- ОТПРАВКА И ОБРАБОТКА КНОПОК ---
async def send_new_poll_notification(poll_id: int):
    text = format_poll_text(poll_id)
    poll = db.get_poll(poll_id)
    if not text or not poll: return
    fixed_bets = [100, 200, 500]
    keyboard_rows = []
    for option in poll['options']:
        button_row = [InlineKeyboardButton(text=f"{option['option_text']} - {amount}", callback_data=f"bet:{poll['id']}:{option['id']}:{amount}") for amount in fixed_bets]
        keyboard_rows.append(button_row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    sent_message = await bot.send_message(chat_id=CHAT_ID, text=text, reply_markup=keyboard)
    db.set_poll_message_id(poll_id, sent_message.message_id)

@dp.callback_query(lambda c: c.data and c.data.startswith('bet:'))
async def process_bet_callback(query: CallbackQuery):
    try:
        _, poll_id_str, option_id_str, amount_str = query.data.split(':')
        poll_id, option_id, amount, telegram_id, username = int(poll_id_str), int(option_id_str), int(amount_str), query.from_user.id, query.from_user.username or f"user{query.from_user.id}"
        db.ensure_user(telegram_id, username)
        result = db.place_bet(telegram_id, poll_id, option_id, amount)
        if result.get("ok"):
            await query.answer(f"✅ Ваша ставка в {amount} монет принята!", show_alert=False)
            await asyncio.sleep(0.5) 
            new_text = format_poll_text(poll_id)
            if new_text:
                try:
                    await bot.edit_message_text(text=new_text, chat_id=query.message.chat.id, message_id=query.message.message_id, reply_markup=query.message.reply_markup)
                except TelegramBadRequest as e:
                    if "message is not modified" in e.message: print(f"Сообщение для опроса #{poll_id} не изменилось.")
                    else: raise e
        else:
            await query.answer(f"❌ Ошибка: {result.get('error')}", show_alert=True)
    except Exception as e:
        print(f"Критическая ошибка в обработчике ставки: {e}")
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

@dp.message(Command("close"))
async def close_poll_command(message: Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            return await message.reply("❌ <b>Неверный формат.</b>\nИспользуйте: <code>/close ID Текст_победителя</code>\n<b>Пример:</b> <code>/close 1 Команда А</code>")
        poll_id, winning_option_text = int(args[1]), args[2]
        result = db.close_poll(message.from_user.id, poll_id, winning_option_text)
        if not result.get("ok"):
            return await message.reply(f"❌ {result.get('error')}")
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
    except ValueError:
        await message.reply("❌ ID опроса должен быть числом.")
    except Exception as e:
        await message.reply(f"Произошла непредвиденная ошибка: {e}")

@dp.message(Command("winrate"))
async def winrate_command(message: Message):
    rating = db.get_rating()
    text = "🏆 <b>Рейтинг всех игроков по проценту побед:</b>\n\n"
    if not rating:
        text += "Пока нет данных для рейтинга."
    else:
        for i, user in enumerate(rating, 1):
            text += f"{i}. <b>{user['username']}</b> - {user['winrate']}% ({user['wins']} W / {user['losses']} L)\n"
    await message.answer(text)

@dp.message(Command("allpolls"))
async def list_all_polls_command(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        all_polls = db.list_all_polls()
        if not all_polls: return await message.reply("В базе данных пока нет ни одного опроса.")
        response_text = "📋 <b>Полный список всех опросов:</b>\n\n"
        for poll in all_polls:
            status = "🟢 Открыт" if poll['is_open'] else "🔴 Закрыт"
            response_text += f"ID: <code>{poll['id']}</code> | Статус: {status}\nВопрос: {poll['question']}\n--------------------\n"
        await message.reply(response_text)
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message(Command("addcoins"))
async def add_coins_command(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        if len(args) != 3: raise ValueError("Invalid format")
        target_username = args[1].replace('@', '')
        amount = int(args[2])
        if amount <= 0: return await message.reply("Сумма должна быть положительной.")
        target_user = db.get_user_by_username(target_username)
        if not target_user: return await message.reply(f"❌ Пользователь с ником @{target_username} не найден в базе.")
        target_user_id = target_user['telegram_id']
        result = db.add_balance(target_user_id, amount)
        if result.get("ok"):
            updated_user = result.get("user")
            await message.reply(f"✅ Успешно!\nПользователю: @{updated_user['username']}\nНачислено: {amount} монет\nНовый баланс: {updated_user['balance']} монет.")
        else:
            await message.reply(f"❌ Ошибка: {result.get('error')}")
    except (ValueError, IndexError):
        await message.reply("❌ <b>Неверный формат.</b>\nИспользуйте: <code>/addcoins @username Сумма</code>\n<b>Пример:</b> <code>/addcoins @Per4uk322 10000</code>")
    except Exception as e:
        await message.reply(f"Произошла непредвиденная ошибка: {e}")

@dp.message(Command("uploaddb"))
async def upload_db_command(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    if not message.document: return await message.reply("Пожалуйста, прикрепите файл `tg_miniapp.db` к этой команде.")
    if message.document.file_name != 'tg_miniapp.db': return await message.reply(f"Неверное имя файла. Ожидается `tg_miniapp.db`, получен `{message.document.file_name}`.")
    try:
        await message.reply("Начинаю загрузку файла...")
        await bot.download(message.document, destination=DB_PATH)
        await message.reply("✅ Файл базы данных успешно загружен и заменен! Рекомендую перезапустить сервис на Render.")
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка при загрузке файла: {e}")

@dp.message(Command("getdb"))
async def get_db_command(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        if os.path.exists(DB_PATH):
            db_file = FSInputFile(DB_PATH)
            await message.reply_document(db_file, caption="Вот текущая база данных.")
        else:
            await message.reply("Файл базы данных не найден на сервере.")
    except Exception as e:
        await message.reply(f"Произошла ошибка при отправке файла: {e}")


@dp.message(Command("ask"))
async def ask_ai_command(message: Message):
    prompt = message.text.replace("/ask", "").strip()
    if not prompt:
        await message.reply("Пожалуйста, напишите ваш вопрос после команды /ask.")
        return

    thinking_message = None
    try:
        thinking_message = await message.reply("🧠 Думаю...")
        response = await text_model.generate_content_async(prompt)
        
        if response.parts:
            await thinking_message.edit_text(response.text)
        else:
            await thinking_message.edit_text("Не удалось получить ответ от AI. Возможно, сработали фильтры безопасности.")

    except Exception as e:
        # ✨ ГЛАВНОЕ ИЗМЕНЕНИЕ: Отправляем точную ошибку в чат
        error_text = f"❌ Произошла детальная ошибка:\n\n<code>{e}</code>"
        if thinking_message:
            await thinking_message.edit_text(error_text)
        else:
            await message.reply(error_text)

# И также замените эту функцию
@dp.message(Command("describe"))
async def describe_image_command(message: Message):
    if not message.photo:
        await message.reply("Пожалуйста, прикрепите изображение к команде /describe.")
        return

    prompt = message.caption.replace("/describe", "").strip() if message.caption else "Опиши, что на этой картинке."
    
    thinking_message = None
    try:
        thinking_message = await message.reply("🖼️ Анализирую изображение...")
        
        photo: PhotoSize = message.photo[-1] 
        photo_bytes_io = io.BytesIO()
        await bot.download(photo, destination=photo_bytes_io)
        photo_bytes_io.seek(0)
        
        img = Image.open(photo_bytes_io)
        
        response = await vision_model.generate_content_async([prompt, img])
        
        if response.parts:
            await thinking_message.edit_text(response.text)
        else:
            await thinking_message.edit_text("Не удалось получить ответ от AI. Возможно, изображение было заблокировано фильтрами безопасности.")

    except Exception as e:
        # ✨ ГЛАВНОЕ ИЗМЕНЕНИЕ: Отправляем точную ошибку в чат
        error_text = f"❌ Произошла детальная ошибка:\n\n<code>{e}</code>"
        if thinking_message:
            await thinking_message.edit_text(error_text)
        else:
            await message.reply(error_text)

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
        now_msk = datetime.now(timezone(timedelta(hours=3)))
        if last_backup_time is None or (now_msk.hour == 9 and last_backup_time.date() != now_msk.date()):
            try:
                print("--- Создание ежедневной резервной копии... ---")
                if os.path.exists(DB_PATH):
                    backup_file = FSInputFile(DB_PATH)
                    backup_caption = f"🗓️ Резервная копия бд\nот {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    await bot.send_document(chat_id=ADMIN_IDS[0], document=backup_file, caption=backup_caption)
                    last_backup_time = now_msk
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