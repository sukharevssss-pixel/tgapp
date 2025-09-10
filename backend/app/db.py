# backend/app/db.py
import sqlite3
from pathlib import Path
import random
from typing import List, Dict, Any

DB_PATH = Path(__file__).resolve().parent.parent / "tg_miniapp.db"

def get_conn():
    # isolation_level=None -> allows explicit BEGIN/COMMIT. timeout helps avoid "database is locked".
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # создаём таблицы
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 1000,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS polls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        bet_amount INTEGER NOT NULL,
        is_open INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS poll_options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        poll_id INTEGER NOT NULL,
        option_text TEXT NOT NULL,
        FOREIGN KEY(poll_id) REFERENCES polls(id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        poll_id INTEGER NOT NULL,
        option_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(poll_id, user_id),
        FOREIGN KEY(poll_id) REFERENCES polls(id) ON DELETE CASCADE,
        FOREIGN KEY(option_id) REFERENCES poll_options(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        reward_min INTEGER,
        reward_max INTEGER
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        type TEXT,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    # Инициализация нескольких стандартных сундуков (если ещё нет)
    cur.execute("SELECT COUNT(*) as cnt FROM chests")
    cnt = cur.fetchone()["cnt"]
    if cnt == 0:
        chests = [
            ("Малый сундук", 50, 20, 200),
            ("Средний сундук", 200, 100, 600),
            ("Большой сундук", 500, 300, 2000),
        ]
        cur.executemany("INSERT INTO chests (name, price, reward_min, reward_max) VALUES (?, ?, ?, ?)", chests)
        conn.commit()
    conn.close()

# Users
def ensure_user(user_id: int, username: str | None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, username or f"user{user_id}", 1000))
        conn.commit()
    conn.close()

def get_user(user_id: int) -> Dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, balance, wins, losses FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# Polls
def create_poll(creator_id: int, question: str, options: List[str], bet_amount: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    cur.execute("INSERT INTO polls (question, creator_id, bet_amount) VALUES (?, ?, ?)", (question, creator_id, bet_amount))
    poll_id = cur.lastrowid
    for opt in options:
        cur.execute("INSERT INTO poll_options (poll_id, option_text) VALUES (?, ?)", (poll_id, opt))
    conn.commit()
    conn.close()
    return poll_id

def list_polls(open_only: bool = True) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    if open_only:
        cur.execute("SELECT * FROM polls WHERE is_open = 1 ORDER BY created_at DESC")
    else:
        cur.execute("SELECT * FROM polls ORDER BY created_at DESC")
    polls = []
    for p in cur.fetchall():
        poll = dict(p)
        # options
        cur2 = conn.cursor()
        cur2.execute("SELECT po.id, po.option_text, IFNULL(SUM(b.amount),0) as total_bet FROM poll_options po LEFT JOIN bets b ON b.option_id = po.id GROUP BY po.id WHERE po.poll_id = ?" )
        # simpler: query for options with totals
        cur2.execute("""
            SELECT po.id, po.option_text, IFNULL(SUM(b.amount), 0) as total_bet
            FROM poll_options po
            LEFT JOIN bets b ON b.option_id = po.id
            WHERE po.poll_id = ?
            GROUP BY po.id
        """, (poll["id"],))
        poll["options"] = [dict(r) for r in cur2.fetchall()]
        polls.append(poll)
    conn.close()
    return polls

def get_poll(poll_id: int) -> Dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM polls WHERE id = ?", (poll_id,))
    p = cur.fetchone()
    if not p:
        conn.close()
        return None
    poll = dict(p)
    cur.execute("""
        SELECT po.id, po.option_text, IFNULL(SUM(b.amount), 0) as total_bet
        FROM poll_options po
        LEFT JOIN bets b ON b.option_id = po.id
        WHERE po.poll_id = ?
        GROUP BY po.id
    """, (poll_id,))
    poll["options"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return poll

# Bets
def place_bet(user_id: int, poll_id: int, option_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        # check poll
        cur.execute("SELECT bet_amount, is_open FROM polls WHERE id = ?", (poll_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); return {"ok": False, "error": "Poll not found"}
        if row["is_open"] != 1:
            conn.rollback(); return {"ok": False, "error": "Poll is closed"}
        bet_amount = int(row["bet_amount"])
        # check option belongs to poll
        cur.execute("SELECT id FROM poll_options WHERE id = ? AND poll_id = ?", (option_id, poll_id))
        if not cur.fetchone():
            conn.rollback(); return {"ok": False, "error": "Option not found for this poll"}
        # check user exists and balance
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        u = cur.fetchone()
        if not u:
            conn.rollback(); return {"ok": False, "error": "User not found"}
        if u["balance"] < bet_amount:
            conn.rollback(); return {"ok": False, "error": "Insufficient balance"}
        # check user hasn't already bet on this poll
        cur.execute("SELECT * FROM bets WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
        if cur.fetchone():
            conn.rollback(); return {"ok": False, "error": "User already bet on this poll"}
        # deduct balance and insert bet
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet_amount, user_id))
        cur.execute("INSERT INTO bets (poll_id, option_id, user_id, amount) VALUES (?, ?, ?, ?)", (poll_id, option_id, user_id, bet_amount))
        cur.execute("INSERT INTO transactions (user_id, amount, type, note) VALUES (?, ?, ?, ?)", (user_id, -bet_amount, "bet", f"Bet on poll {poll_id}"))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

# Closing poll & payout
def close_poll(creator_id: int, poll_id: int, winning_option_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT creator_id, is_open FROM polls WHERE id = ?", (poll_id,))
        p = cur.fetchone()
        if not p:
            conn.rollback(); return {"ok": False, "error": "Poll not found"}
        if p["creator_id"] != creator_id:
            conn.rollback(); return {"ok": False, "error": "Only creator can close poll"}
        if p["is_open"] != 1:
            conn.rollback(); return {"ok": False, "error": "Poll already closed"}
        # check option valid
        cur.execute("SELECT id FROM poll_options WHERE id = ? AND poll_id = ?", (winning_option_id, poll_id))
        if not cur.fetchone():
            conn.rollback(); return {"ok": False, "error": "Winning option not found"}
        # total pool
        cur.execute("SELECT IFNULL(SUM(amount), 0) as pool FROM bets WHERE poll_id = ?", (poll_id,))
        pool = cur.fetchone()["pool"] or 0
        # total on winning option
        cur.execute("SELECT IFNULL(SUM(amount), 0) as win_total FROM bets WHERE poll_id = ? AND option_id = ?", (poll_id, winning_option_id))
        win_total = cur.fetchone()["win_total"] or 0
        # fetch all bets
        cur.execute("SELECT id, user_id, option_id, amount FROM bets WHERE poll_id = ?", (poll_id,))
        bets = [dict(r) for r in cur.fetchall()]
        # distribute
        if pool > 0 and win_total > 0:
            # winners get payout proportional to their bet
            for b in bets:
                if b["option_id"] == winning_option_id:
                    payout = (b["amount"] * pool) // win_total
                    # credit payout
                    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (payout, b["user_id"]))
                    cur.execute("INSERT INTO transactions (user_id, amount, type, note) VALUES (?, ?, ?, ?)", (b["user_id"], payout, "bet_win", f"Win for poll {poll_id}"))
                    cur.execute("UPDATE users SET wins = wins + 1 WHERE user_id = ?", (b["user_id"],))
                else:
                    cur.execute("UPDATE users SET losses = losses + 1 WHERE user_id = ?", (b["user_id"],))
        else:
            # no winners: all bettors count as losses
            for b in bets:
                cur.execute("UPDATE users SET losses = losses + 1 WHERE user_id = ?", (b["user_id"],))
        # mark poll closed
        cur.execute("UPDATE polls SET is_open = 0 WHERE id = ?", (poll_id,))
        conn.commit()
        return {"ok": True, "pool": pool, "win_total": win_total}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

# Rating
def get_rating(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, balance, wins, losses FROM users")
    users = []
    for r in cur.fetchall():
        u = dict(r)
        w = u["wins"]
        l = u["losses"]
        total = w + l
        winrate = round(w / total, 4) if total > 0 else 0.0
        u["winrate"] = winrate
        users.append(u)
    users.sort(key=lambda x: (x["winrate"], x["wins"]), reverse=True)
    conn.close()
    return users[:limit]

# Chests
def list_chests() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, reward_min, reward_max FROM chests ORDER BY price")
    res = [dict(r) for r in cur.fetchall()]
    conn.close()
    return res

def open_chest(user_id: int, chest_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT price, reward_min, reward_max FROM chests WHERE id = ?", (chest_id,))
        ch = cur.fetchone()
        if not ch:
            conn.rollback(); return {"ok": False, "error": "Chest not found"}
        price = ch["price"]
        rmin = ch["reward_min"]
        rmax = ch["reward_max"]
        # check funds
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        u = cur.fetchone()
        if not u:
            conn.rollback(); return {"ok": False, "error": "User not found"}
        if u["balance"] < price:
            conn.rollback(); return {"ok": False, "error": "Insufficient balance"}
        # deduct price
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        # reward
        reward = random.randint(rmin, rmax)
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
        cur.execute("INSERT INTO transactions (user_id, amount, type, note) VALUES (?, ?, ?, ?)", (user_id, -price, "chest_buy", f"Bought chest {chest_id}"))
        cur.execute("INSERT INTO transactions (user_id, amount, type, note) VALUES (?, ?, ?, ?)", (user_id, reward, "chest_reward", f"Reward from chest {chest_id}"))
        conn.commit()
        return {"ok": True, "reward": reward}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
