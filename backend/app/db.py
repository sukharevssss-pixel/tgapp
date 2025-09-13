import sqlite3
from pathlib import Path
import random
from typing import List, Dict, Any
import json
import os

DB_PATH = Path(__file__).resolve().parent.parent / "tg_miniapp.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    # Проверяем, есть ли переменная окружения, которая приказывает пересоздать БД
    if os.environ.get("RECREATE_DB_ON_STARTUP") == "true":
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("✅ Старая база данных удалена для принудительного пересоздания.")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users ( telegram_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 1000, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0 );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS polls ( id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL, creator_id INTEGER NOT NULL, min_bet_amount INTEGER NOT NULL DEFAULT 1, is_open INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(creator_id) REFERENCES users(telegram_id) ON DELETE CASCADE );
    """)
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

    cur.execute("SELECT COUNT(*) as cnt FROM chests")
    cnt = cur.fetchone()["cnt"]
    if cnt == 0:
        small_chest_rewards = json.dumps({"rewards": [20, 50, 100, 300], "weights": [65, 25, 8, 2]})
        medium_chest_rewards = json.dumps({"rewards": [100, 200, 400, 800], "weights": [60, 28, 10, 2]})
        large_chest_rewards = json.dumps({"rewards": [300, 500, 1000, 3000], "weights": [55, 30, 13, 2]})
        
        chests_data = [
            ("Малый сундук", 50, small_chest_rewards),
            ("Средний сундук", 200, medium_chest_rewards),
            ("Большой сундук", 500, large_chest_rewards),
        ]
        
        cur.executemany("INSERT INTO chests (name, price, rewards_json) VALUES (?, ?, ?)", chests_data)
        conn.commit()

    conn.close()


def ensure_user(telegram_id: int, username: str | None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (telegram_id, username, balance) VALUES (?, ?, ?)",
            (telegram_id, username or f"user{telegram_id}", 1000),
        )
        conn.commit()
    conn.close()


def get_user(telegram_id: int) -> Dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT telegram_id, username, balance, wins, losses FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


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


def list_polls(open_only: bool = True) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    query = "SELECT * FROM polls WHERE is_open = 1 ORDER BY created_at DESC" if open_only else "SELECT * FROM polls ORDER BY created_at DESC"
    cur.execute(query)
    polls = []
    for p in cur.fetchall():
        poll = dict(p)
        cur2 = conn.cursor()
        cur2.execute("SELECT po.id, po.option_text, IFNULL(SUM(b.amount), 0) as total_bet FROM poll_options po LEFT JOIN bets b ON b.option_id = po.id WHERE po.poll_id = ? GROUP BY po.id", (poll["id"],))
        poll["options"] = [dict(r) for r in cur2.fetchall()]
        polls.append(poll)
    conn.close()
    return polls


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
        if amount < min_bet_amount:
            return {"ok": False, "error": f"Сумма ставки не может быть меньше {min_bet_amount}"}

        cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cur.fetchone()
        if not user_row: return {"ok": False, "error": "Пользователь не найден"}
        if user_row["balance"] < amount:
            return {"ok": False, "error": "Недостаточно средств"}

        cur.execute("SELECT * FROM bets WHERE poll_id = ? AND telegram_id = ?", (poll_id, telegram_id))
        if cur.fetchone(): return {"ok": False, "error": "Вы уже сделали ставку в этом опросе"}

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