# backend/app/db.py
# (Импорты sqlite3, Path, random, json и т.д. остаются)
import sqlite3
from pathlib import Path
import random
from typing import List, Dict, Any
import json

DB_PATH = Path(__file__).resolve().parent.parent / "tg_miniapp.db"

def get_conn(): # ... без изменений
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ... таблицы users, poll_options, bets, chests, transactions без изменений ...
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users ( telegram_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 1000, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0 );
    """)
    # --- ✨ ИЗМЕНЕНИЕ: bet_amount -> min_bet_amount ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS polls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        min_bet_amount INTEGER NOT NULL DEFAULT 1, -- Сумма ставки стала минимальной
        is_open INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(creator_id) REFERENCES users(telegram_id) ON DELETE CASCADE
    );
    """)
    # ... остальные таблицы ...
    cur.execute("""
    CREATE TABLE IF NOT EXISTS poll_options ( id INTEGER PRIMARY KEY AUTOINCREMENT, poll_id INTEGER NOT NULL, option_text TEXT NOT NULL, FOREIGN KEY(poll_id) REFERENCES polls(id) ON DELETE CASCADE );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bets ( id INTEGER PRIMARY KEY AUTOINCREMENT, poll_id INTEGER NOT NULL, option_id INTEGER NOT NULL, telegram_id INTEGER NOT NULL, amount INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(poll_id, telegram_id), FOREIGN KEY(poll_id) REFERENCES polls(id) ON DELETE CASCADE, FOREIGN KEY(option_id) REFERENCES poll_options(id) ON DELETE CASCADE, FOREIGN KEY(telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chests ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, rewards_json TEXT );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions ( id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, amount INTEGER, type TEXT, note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE );
    """)

    conn.commit()
    # ... логика создания сундуков без изменений ...
    conn.close()

# --- Users (без изменений) ---
def ensure_user(telegram_id: int, username: str | None): # ...
def get_user(telegram_id: int) -> Dict[str, Any] | None: # ...

# --- Polls ---
# --- ✨ ИЗМЕНЕНИЕ: bet_amount -> min_bet_amount ---
def create_poll(creator_id: int, question: str, options: List[str], min_bet_amount: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    cur.execute(
        "INSERT INTO polls (question, creator_id, min_bet_amount) VALUES (?, ?, ?)",
        (question, creator_id, min_bet_amount),
    )
    poll_id = cur.lastrowid
    for opt in options:
        cur.execute("INSERT INTO poll_options (poll_id, option_text) VALUES (?, ?)", (poll_id, opt))
    conn.commit()
    conn.close()
    return poll_id

def list_polls(open_only: bool = True) -> List[Dict[str, Any]]: # ... без изменений
def get_poll(poll_id: int) -> Dict[str, Any] | None: # ... без изменений

# --- Bets ---
# --- ✨ ИЗМЕНЕНИЕ: Функция теперь принимает сумму ставки `amount` ---
def place_bet(telegram_id: int, poll_id: int, option_id: int, amount: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT min_bet_amount, is_open FROM polls WHERE id = ?", (poll_id,))
        poll_row = cur.fetchone()
        if not poll_row: return {"ok": False, "error": "Опрос не найден"}
        if poll_row["is_open"] != 1: return {"ok": False, "error": "Опрос закрыт"}
        
        min_bet_amount = int(poll_row["min_bet_amount"])
        # Новая проверка: сумма ставки не должна быть меньше минимальной
        if amount < min_bet_amount:
            return {"ok": False, "error": f"Сумма ставки не может быть меньше {min_bet_amount}"}

        cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cur.fetchone()
        if not user_row: return {"ok": False, "error": "Пользователь не найден"}
        # Проверяем баланс с учетом новой суммы ставки
        if user_row["balance"] < amount:
            return {"ok": False, "error": "Недостаточно средств"}

        cur.execute("SELECT * FROM bets WHERE poll_id = ? AND telegram_id = ?", (poll_id, telegram_id))
        if cur.fetchone(): return {"ok": False, "error": "Вы уже сделали ставку в этом опросе"}

        # Списываем и записываем ту сумму, которую указал пользователь
        cur.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (amount, telegram_id))
        cur.execute(
            "INSERT INTO bets (poll_id, option_id, telegram_id, amount) VALUES (?, ?, ?, ?)",
            (poll_id, option_id, telegram_id, amount),
        )
        cur.execute(
            "INSERT INTO transactions (telegram_id, amount, type, note) VALUES (?, ?, ?, ?)",
            (telegram_id, -amount, "bet", f"Ставка в опросе {poll_id}"),
        )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

# --- Close Poll, Rating, Chests (без изменений) ---
def close_poll(creator_id: int, poll_id: int, winning_option_id: int) -> Dict[str, Any]: # ...
def get_rating(limit: int = 50) -> List[Dict[str, Any]]: # ...
def list_chests() -> List[Dict[str, Any]]: # ...
def open_chest(telegram_id: int, chest_id: int) -> Dict[str, Any]: # ...
