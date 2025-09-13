import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic, hcode
from dotenv import load_dotenv

import db

# --- Конфигурация ---
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
# ВАЖНО: Замените на ID вашего Telegram-аккаунта
ADMIN_IDS = [359469476] 

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN и CHAT_ID должны быть установлены")

# --- Инициализация ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- ФОРМАТИРОВАНИЕ СООБЩЕНИЙ ---
def format_poll_text(poll_id: int) -> str:
    poll = db.get_poll(poll_id)
    if not poll:
        return "Опрос не найден."

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
    
    closes_at_str = datetime.fromisoformat(poll['closes_at']).strftime('%H:%M')
    text += f"\n<i>Ставки закроются в {closes_at_str}</i>"
    return text

# --- КОМАНДЫ БОТА ---
@dp.message(Command("bet"))
async def create_poll_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("У вас нет прав для создания опросов.")
        return

    try:
        lines = message.text.strip().split('\n')
        if len(lines) < 4:
            raise ValueError("Invalid format")

        question = lines[1]
        min_bet_amount = int(lines[-1])
        options = lines[2:-1]

        if len(options) < 2:
            raise ValueError("Minimum 2 options required.")

        poll_id = db.create_poll(
            creator_id=message.from_user.id,
            question=question,
            options=options,
            min_bet_amount=min_bet_amount
        )

        text = format_poll_text(poll_id)
        sent_message = await bot.send_message(CHAT_ID, text)
        db.set_poll_message_id(poll_id, sent_message.message_id)
        
        await message.reply("✅ Опрос успешно создан и отправлен в чат!")

    except (ValueError, IndexError):
        await message.reply(
            "❌ <b>Неверный формат команды.</b>\n\n"
            "Используйте многострочный формат:\n"
            "<code>/bet\nТекст вопроса\nВариант 1\nВариант 2\n100</code>"
        )

@dp.message(Command("p"))
async def place_bet_command(message: Message):
    try:
        args = message.text.split()
        if len(args) < 4:
            raise ValueError("Invalid format")

        poll_id = int(args[1])
        amount = int(args[-1])
        option_text = " ".join(args[2:-1])

        poll = db.get_poll(poll_id)
        if not poll:
            await message.reply("❌ Опрос с таким ID не найден.")
            return

        target_option = None
        for opt in poll['options']:
            if opt['option_text'].lower() == option_text.lower():
                target_option = opt
                break
        
        if not target_option:
            await message.reply("❌ Вариант ответа не найден. Проверьте написание.")
            return

        result = db.place_bet(message.from_user.id, poll_id, target_option['id'], amount)

        if result.get("ok"):
            await message.reply("✅ Ваша ставка принята!")
            # Update the original poll message
            if poll.get('message_id'):
                new_text = format_poll_text(poll_id)
                await bot.edit_message_text(new_text, CHAT_ID, poll['message_id'])
        else:
            await message.reply(f"❌ {result.get('error')}")

    except (ValueError, IndexError):
        await message.reply(
            "❌ <b>Неверный формат команды.</b>\n\n"
            "Используйте: <code>/p ID_опроса Текст_варианта Сумма</code>\n"
            "<b>Пример:</b> <code>/p 1 Команда А 123</code>"
        )

@dp.message(Command("close"))
async def close_poll_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("У вас нет прав для закрытия опросов.")
        return
        
    try:
        args = message.text.split()
        poll_id = int(args[1])
        winning_option_text = " ".join(args[2:])

        result = db.close_poll(message.from_user.id, poll_id, winning_option_text)
        
        if not result.get("ok"):
            raise ValueError(result.get("error"))

        winners = result.get('winners', [])
        response_text = f"🎉 <b>Опрос #{poll_id} завершен!</b>\n"
        response_text += f"🏆 Победил вариант: <b>{result['winning_option_text']}</b>\n\n"

        if not winners:
            response_text += "Никто не угадал исход. Банк остается в системе."
        else:
            response_text += "Поздравляем победителей:\n"
            for winner in winners:
                response_text += f" - <b>{winner['username']}</b> выигрывает <b>{winner['payout']}</b> монет!\n"
        
        await bot.send_message(CHAT_ID, response_text)
        
        poll = db.get_poll(poll_id)
        if poll and poll.get('message_id'):
            final_text = format_poll_text(poll_id)
            await bot.edit_message_text(final_text, CHAT_ID, poll['message_id'])

    except (ValueError, IndexError):
        await message.reply(
            "❌ <b>Неверный формат команды.</b>\n\n"
            "Используйте: <code>/close ID_опроса Текст_варианта_победителя</code>\n"
            "<b>Пример:</b> <code>/close 1 Команда А</code>"
        )

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
async def scheduler():
    while True:
        await asyncio.sleep(60)
        try:
            polls_to_close = db.auto_close_due_polls()
            for poll in polls_to_close:
                try:
                    new_text = format_poll_text(poll['id'])
                    if poll.get('message_id'):
                        await bot.edit_message_text(new_text, CHAT_ID, poll['message_id'])
                except Exception as e:
                    print(f"Failed to auto-update poll message #{poll['id']}: {e}")
        except Exception as e:
            print(f"Error in scheduler: {e}")

# --- ЗАПУСК ---
async def start_bot():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)