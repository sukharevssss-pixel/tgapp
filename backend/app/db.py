import sqlite3
from pathlib import Path

# Путь к БД (лежит в корне проекта рядом с docker-compose.yml)
DB_PATH = Path(__file__).resolve().parent.parent / "tg_miniapp.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # чтобы получать dict-подобные строки
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Таблица пользователей
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )
        """
    )

    # Таблица опросов
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS polls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            question TEXT,
            options TEXT, -- json array
            is_open INTEGER DEFAULT 1
        )
        """
    )

    conn.commit()
    conn.close()


def ensure_user(user_id: int, username: str | None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)",
            (user_id, username or f"user{user_id}", 1000),
        )

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()

    conn.close()
    return dict(row) if row else None