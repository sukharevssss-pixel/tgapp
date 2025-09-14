import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import db
import traceback
import bot 

app = FastAPI(title="TG MiniApp Backend")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic-схемы ---
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

# --- СХЕМЫ CreatePollPayload и ClosePollPayload УДАЛЕНЫ, ТАК КАК ОНИ БОЛЬШЕ НЕ НУЖНЫ ---

# --- Startup ---
@app.on_event("startup")
def startup():
    print("🚀 Startup: инициализация базы данных")
    db.init_db()
    asyncio.create_task(bot.start_bot())
    print("🤖 Бот и планировщик запущены...")


# --- Пользователи ---
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
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/api/me/{telegram_id}")
async def api_me(telegram_id: int):
    user = db.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# --- Опросы (только для чтения и ставок из Mini App) ---

# --- ЭНДПОИНТ POST /api/polls УДАЛЕН, ТАК КАК ОПРОСЫ СОЗДАЮТСЯ ЧЕРЕЗ БОТА ---

@app.get("/api/polls")
async def api_list_polls():
    return db.list_polls(open_only=True)

@app.get("/api/polls/{poll_id}")
async def api_get_poll(poll_id: int):
    poll = db.get_poll(poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll

@app.post("/api/bet")
async def api_place_bet(payload: PlaceBetPayload):
    try:
        res = db.place_bet(payload.telegram_id, payload.poll_id, payload.option_id, payload.amount)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# --- ЭНДПОИНТ POST /api/polls/close УДАЛЕН, ТАК КАК ОПРОСЫ ЗАКРЫВАЮТСЯ ЧЕРЕЗ БОТА ---

# --- Сундуки ---
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
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# --- Рейтинг ---
@app.get("/api/rating")
async def api_rating():
    return db.get_rating()