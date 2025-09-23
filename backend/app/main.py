import importlib.metadata

try:
    version = importlib.metadata.version('google-generativeai')
    print(f"✅ Обнаружена версия google-generativeai: {version}")
except importlib.metadata.PackageNotFoundError:
    print("❌ Библиотека google-generativeai НЕ НАЙДЕНА.")

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import traceback
from . import db, bot 

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Startup: инициализация базы данных")
    db.init_db()
    bot_task = asyncio.create_task(bot.start_bot())
    print("🤖 Бот и планировщик запущены...")
    yield
    print("🛑 Shutting down bot...")
    bot_task.cancel()

app = FastAPI(title="TG MiniApp Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InitPayload(BaseModel):
    telegram_id: int
    username: str | None = None

class PlaceBetPayload(BaseModel):
    telegram_id: int
    poll_id: int
    option_id: int
    amount: int

class OpenChestPayload(BaseModel):
    telegram_id: int
    chest_id: int

@app.post("/api/auth")
async def api_auth(payload: InitPayload):
    try:
        db.ensure_user(payload.telegram_id, payload.username)
        user = db.get_user(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")
        return {"ok": True, "user": user}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/me/{telegram_id}")
async def api_me(telegram_id: int):
    user = db.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/polls")
async def api_list_polls():
    return db.list_polls(open_only=True)

@app.post("/api/bet")
async def api_place_bet(payload: PlaceBetPayload):
    try:
        res = db.place_bet(payload.telegram_id, payload.poll_id, payload.option_id, payload.amount)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        
        poll = db.get_poll(payload.poll_id)
        if poll and poll.get('message_id'):
            new_text = bot.format_poll_text(payload.poll_id)
            if new_text and bot.CHAT_ID:
                try:
                    await bot.bot.edit_message_text(new_text, bot.CHAT_ID, poll['message_id'])
                except Exception as e:
                    print(f"Failed to edit message after web bet: {e}")
        return res
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chests")
async def api_chests():
    return db.list_chests()

@app.post("/api/chests/open")
async def api_open_chest(payload: OpenChestPayload):
    try:
        res = db.open_chest(payload.telegram_id, payload.chest_id)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rating")
async def api_rating():
    return db.get_rating()

@app.get("/health")
async def health_check():
    return {"status": "ok"}