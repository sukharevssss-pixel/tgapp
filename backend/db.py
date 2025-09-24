import sqlite3
from pathlib import Path
import random
from typing import List, Dict, Any
import json
import os
from datetime import datetime, timedelta, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "tg_miniapp.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
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
    CREATE TABLE IF NOT EXISTS polls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        status TEXT DEFAULT 'accepting_bets',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        message_id INTEGER,
        closes_at TIMESTAMP
    );
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

    if cur.execute("SELECT COUNT(*) FROM chests").fetchone()[0] == 0:
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
        cur.execute("INSERT INTO users (telegram_id, username, balance) VALUES (?, ?, ?)", (telegram_id, username or f"user{telegram_id}", 1000))
        conn.commit()
    conn.close()


def get_user(telegram_id: int) -> Dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username: str) -> Dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_poll(creator_id: int, question: str, options: List[str]) -> int:
    conn = get_conn()
    cur = conn.cursor()
    closes_at = datetime.now(timezone.utc) + timedelta(minutes=20)
    cur.execute(
        "INSERT INTO polls (question, creator_id, closes_at, status) VALUES (?, ?, ?, ?)",
        (question, creator_id, closes_at.isoformat(), 'accepting_bets'),
    )
    poll_id = cur.lastrowid
    for opt in options:
        cur.execute("INSERT INTO poll_options (poll_id, option_text) VALUES (?, ?)", (poll_id, opt))
    conn.commit()
    conn.close()
    return poll_id


def set_poll_message_id(poll_id: int, message_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE polls SET message_id = ? WHERE id = ?", (message_id, poll_id))
    conn.commit()
    conn.close()


def auto_close_due_polls() -> List[Dict[str, Any]]:
    conn = get_conn()
    now_utc = datetime.now(timezone.utc)
    cur = conn.cursor()
    cur.execute("SELECT id, closes_at FROM polls WHERE status = 'accepting_bets'")
    all_open_polls = cur.fetchall()
    
    polls_to_close_ids = []
    if all_open_polls:
        for poll_data in all_open_polls:
            closes_at_dt = datetime.fromisoformat(poll_data["closes_at"])
            if closes_at_dt <= now_utc:
                polls_to_close_ids.append(poll_data["id"])

    if polls_to_close_ids:
        cur.execute(f"UPDATE polls SET status = 'voting_closed' WHERE id IN ({','.join('?' for _ in polls_to_close_ids)})", polls_to_close_ids)
        conn.commit()
    
    if polls_to_close_ids:
        cur.execute(f"SELECT id, message_id FROM polls WHERE id IN ({','.join('?' for _ in polls_to_close_ids)})", polls_to_close_ids)
        closed_polls_info = [dict(row) for row in cur.fetchall()]
        conn.close()
        return closed_polls_info

    conn.close()
    return []


def get_poll(poll_id: int) -> Dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM polls WHERE id = ?", (poll_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    poll = dict(row)
    cur.execute("SELECT po.id, po.option_text, IFNULL(SUM(b.amount), 0) as total_bet FROM poll_options po LEFT JOIN bets b ON b.option_id = po.id WHERE po.poll_id = ? GROUP BY po.id ORDER BY po.id", (poll_id,))
    poll["options"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return poll


def list_polls(open_only: bool = True) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM polls WHERE status IN ('accepting_bets', 'voting_closed') ORDER BY created_at DESC")
    polls = []
    for p in cur.fetchall():
        poll = dict(p)
        cur2 = conn.cursor()
        cur2.execute("SELECT po.id, po.option_text, IFNULL(SUM(b.amount), 0) as total_bet FROM poll_options po LEFT JOIN bets b ON b.option_id = po.id WHERE po.poll_id = ? GROUP BY po.id", (poll["id"],))
        poll["options"] = [dict(r) for r in cur2.fetchall()]
        polls.append(poll)
    conn.close()
    return polls


def list_all_polls() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, question, status, creator_id FROM polls ORDER BY id DESC")
    all_polls = [dict(row) for row in cur.fetchall()]
    conn.close()
    return all_polls


def get_bets_for_poll(poll_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT b.option_id, b.amount, u.username FROM bets b JOIN users u ON u.telegram_id = b.telegram_id WHERE b.poll_id = ? ORDER BY b.created_at", (poll_id,))
    bets = [dict(row) for row in cur.fetchall()]
    conn.close()
    return bets


def place_bet(telegram_id: int, poll_id: int, option_id: int, amount: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT status FROM polls WHERE id = ?", (poll_id,))
        poll_row = cur.fetchone()
        if not poll_row: return {"ok": False, "error": "Опрос не найден"}
        if poll_row["status"] != 'accepting_bets': return {"ok": False, "error": "Ставки на этот опрос больше не принимаются"}
        if amount <= 0: return {"ok": False, "error": "Сумма ставки должна быть больше нуля"}
        cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cur.fetchone()
        if not user_row: return {"ok": False, "error": "Пользователь не найден"}
        if user_row["balance"] < amount: return {"ok": False, "error": "Недостаточно средств"}
        cur.execute("SELECT * FROM bets WHERE poll_id = ? AND telegram_id = ?", (poll_id, telegram_id))
        if cur.fetchone(): return {"ok": False, "error": "Вы уже сделали ставку в этом опросе"}
        cur.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (amount, telegram_id))
        cur.execute("INSERT INTO bets (poll_id, option_id, telegram_id, amount) VALUES (?, ?, ?, ?)", (poll_id, option_id, telegram_id, amount))
        cur.execute("INSERT INTO transactions (telegram_id, amount, type, note) VALUES (?, ?, ?, ?)", (telegram_id, -amount, "bet", f"Ставка в опросе {poll_id}"))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def close_poll(user_id: int, poll_id: int, winning_option_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT id, status FROM polls WHERE id = ?", (poll_id,))
        poll = cur.fetchone()
        if not poll: return {"ok": False, "error": "Опрос не найден"}
        if poll["status"] == 'resolved': return {"ok": False, "error": "Этот опрос уже был разрешен."}
        
        cur.execute("SELECT option_text FROM poll_options WHERE poll_id = ? AND id = ?", (poll_id, winning_option_id))
        option_row = cur.fetchone()
        if not option_row: return {"ok": False, "error": "Такой вариант ответа не принадлежит этому опросу."}
        winning_option_text = option_row['option_text']
        
        cur.execute("SELECT telegram_id, option_id, amount FROM bets WHERE poll_id = ?", (poll_id,))
        all_bets = [dict(r) for r in cur.fetchall()]
        pool = sum(b['amount'] for b in all_bets)
        win_total = sum(b['amount'] for b in all_bets if b['option_id'] == winning_option_id)
        
        winners_data = []
        if pool > 0 and win_total > 0:
            is_only_winners = (pool == win_total)
            for bet in all_bets:
                bettor_id = bet["telegram_id"]
                if bet["option_id"] == winning_option_id:
                    payout = bet["amount"] * 2 if is_only_winners else (bet["amount"] * pool) // win_total
                    cur.execute("UPDATE users SET balance = balance + ?, wins = wins + 1 WHERE telegram_id = ?", (payout, bettor_id))
                    cur.execute("INSERT INTO transactions (telegram_id, amount, type, note) VALUES (?, ?, ?, ?)", (bettor_id, payout, "bet_win", f"Win poll {poll_id}"))
                    user_info = get_user(bettor_id)
                    if user_info: winners_data.append({"username": user_info.get('username', 'N/A'), "payout": payout})
                else: 
                    cur.execute("UPDATE users SET losses = losses + 1 WHERE telegram_id = ?", (bettor_id,))
        elif pool > 0 and win_total == 0:
             for bet in all_bets:
                cur.execute("UPDATE users SET losses = losses + 1 WHERE telegram_id = ?", (bet["telegram_id"],))

        cur.execute("UPDATE polls SET status = 'resolved', message_id = NULL WHERE id = ?", (poll_id,))
        conn.commit()
        return {"ok": True, "pool": pool, "winners": winners_data, "winning_option_text": winning_option_text}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
        
def get_rating(limit: int = None) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT telegram_id, username, balance, wins, losses FROM users")
    users = []
    for r in cur.fetchall():
        u = dict(r)
        total = u["wins"] + u["losses"]
        u["winrate"] = round((u["wins"] / total) * 100, 2) if total > 0 else 0.0
        users.append(u)
    users.sort(key=lambda x: (x["winrate"], x["wins"]), reverse=True)
    conn.close()
    if limit:
        return users[:limit]
    return users

def add_balance(telegram_id: int, amount: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        if not cur.fetchone(): return {"ok": False, "error": "Пользователь с таким ID не найден."}
        cur.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, telegram_id))
        cur.execute("INSERT INTO transactions (telegram_id, amount, type, note) VALUES (?, ?, ?, ?)", (telegram_id, amount, "admin_add", "Пополнение от администратора"))
        conn.commit()
        updated_user = get_user(telegram_id)
        return {"ok": True, "user": updated_user}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def list_chests() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM chests ORDER BY price")
    res = [dict(r) for r in cur.fetchall()]
    conn.close()
    return res

def open_chest(telegram_id: int, chest_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT price, rewards_json FROM chests WHERE id = ?", (chest_id,))
        ch = cur.fetchone()
        if not ch: return {"ok": False, "error": "Chest not found"}
        price, rewards_data_str = ch["price"], ch["rewards_json"]
        cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        u = cur.fetchone()
        if not u or u["balance"] < price: return {"ok": False, "error": "User not found or insufficient balance"}
        cur.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, telegram_id))
        rewards_data = json.loads(rewards_data_str)
        reward = random.choices(rewards_data["rewards"], weights=rewards_data["weights"], k=1)[0]
        cur.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (reward, telegram_id))
        cur.execute("INSERT INTO transactions (telegram_id, amount, type, note) VALUES (?, ?, ?, ?)", (telegram_id, -price, "chest_buy", f"Buy chest {chest_id}"))
        cur.execute("INSERT INTO transactions (telegram_id, amount, type, note) VALUES (?, ?, ?, ?)", (telegram_id, reward, "chest_reward", f"Reward chest {chest_id}"))
        conn.commit()
        return {"ok": True, "reward": reward}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()