from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import db

app = FastAPI(title="TG MiniApp Backend")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ в проде лучше ограничить
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
    db.init_db()

# --- Пользователи ---
@app.post("/api/auth")
async def api_auth(payload: InitPayload):
    """Регистрация или возврат существующего пользователя"""
    db.ensure_user(payload.telegram_id, payload.username)
    user = db.get_user(payload.telegram_id)

    if not user:
        raise HTTPException(status_code=500, detail="User creation failed")

    # Явно возвращаем словарь, а не SQLRow
    return {
        "ok": True,
        "user": {
            "telegram_id": user["telegram_id"],
            "username": user["username"],
            "balance": user["balance"],
        },
    }

