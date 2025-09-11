from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import db
import traceback

app = FastAPI(title="TG MiniApp Backend")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ в проде лучше ограничить на проде
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic-схемы ---
class InitPayload(BaseModel):
    telegram_id: int
    username: str | None = None

class CreatePollPayload(BaseModel):
    telegram_id: int
    question: str
    options: list[str]
    bet_amount: int

class PlaceBetPayload(BaseModel):
    telegram_id: int
    poll_id: int
    option_id: int

class ClosePollPayload(BaseModel):
    telegram_id: int
    poll_id: int
    winning_option_id: int

class OpenChestPayload(BaseModel):
    telegram_id: int
    chest_id: int


# --- Startup ---
@app.on_event("startup")
def startup():
    print("🚀 Startup: инициализация базы данных")
    db.init_db()


# --- Пользователи ---
@app.post("/api/auth")
async def api_auth(payload: InitPayload):
    """Регистрация или возврат существующего пользователя"""
    try:
        print("📥 /api/auth payload:", payload.dict())
        db.ensure_user(payload.telegram_id, payload.username)
        user = db.get_user(payload.telegram_id)
        print("📤 user from db:", user)

        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")

        return {
            "ok": True,
            "user": {
                "telegram_id": user["telegram_id"],
                "username": user["username"],
                "balance": user["balance"],
            },
        }
    except Exception as e:
        print("❌ Ошибка в /api/auth:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/me/{telegram_id}")
async def api_me(telegram_id: int):
    try:
        print(f"📥 /api/me/{telegram_id}")
        user = db.get_user(telegram_id)
        print("📤 user from db:", user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "telegram_id": user["telegram_id"],
            "username": user["username"],
            "balance": user["balance"],
        }
    except Exception as e:
        print("❌ Ошибка в /api/me:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# --- Опросы ---
@app.post("/api/polls")
async def api_create_poll(payload: CreatePollPayload):
    try:
        print("📥 /api/polls payload:", payload.dict())
        if len(payload.options) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 options")
        poll_id = db.create_poll(
            payload.telegram_id, payload.question, payload.options, payload.bet_amount
        )
        print("✅ Poll created, id:", poll_id)
        return {"ok": True, "poll_id": poll_id}
    except Exception as e:
        print("❌ Ошибка в /api/polls:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/polls")
async def api_list_polls():
    try:
        polls = db.list_polls(open_only=True)
        print("📤 polls:", polls)
        return polls
    except Exception as e:
        print("❌ Ошибка в /api/polls (list):", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/polls/{poll_id}")
async def api_get_poll(poll_id: int):
    try:
        print(f"📥 /api/polls/{poll_id}")
        poll = db.get_poll(poll_id)
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        return poll
    except Exception as e:
        print("❌ Ошибка в /api/polls/{id}:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/bet")
async def api_place_bet(payload: PlaceBetPayload):
    try:
        print("📥 /api/bet payload:", payload.dict())
        res = db.place_bet(payload.telegram_id, payload.poll_id, payload.option_id)
        print("📤 bet result:", res)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    except Exception as e:
        print("❌ Ошибка в /api/bet:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/polls/close")
async def api_close_poll(payload: ClosePollPayload):
    try:
        print("📥 /api/polls/close payload:", payload.dict())
        res = db.close_poll(payload.telegram_id, payload.poll_id, payload.winning_option_id)
        print("📤 close poll result:", res)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    except Exception as e:
        print("❌ Ошибка в /api/polls/close:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# --- Сундуки ---
@app.get("/api/chests")
async def api_chests():
    try:
        chests = db.list_chests()
        print("📤 chests:", chests)
        return chests
    except Exception as e:
        print("❌ Ошибка в /api/chests:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/chests/open")
async def api_open_chest(payload: OpenChestPayload):
    try:
        print("📥 /api/chests/open payload:", payload.dict())
        res = db.open_chest(payload.telegram_id, payload.chest_id)
        print("📤 chest open result:", res)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    except Exception as e:
        print("❌ Ошибка в /api/chests/open:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# --- Рейтинг ---
@app.get("/api/rating")
async def api_rating():
    try:
        rating = db.get_rating()
        print("📤 rating:", rating)
        return rating
    except Exception as e:
        print("❌ Ошибка в /api/rating:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

