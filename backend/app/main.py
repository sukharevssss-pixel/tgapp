# backend/app/main.py
# (Импорты FastAPI, asyncio, db, bot и т.д. остаются)

app = FastAPI(title="TG MiniApp Backend")
# ... CORS, startup event ...

# --- Pydantic-схемы ---
# ... InitPayload ...
class InitPayload(BaseModel): #...

# --- ✨ ИЗМЕНЕНИЕ: bet_amount -> min_bet_amount ---
class CreatePollPayload(BaseModel):
    telegram_id: int
    question: str
    options: list[str]
    min_bet_amount: int

# --- ✨ ИЗМЕНЕНИЕ: Добавляем поле amount ---
class PlaceBetPayload(BaseModel):
    telegram_id: int
    poll_id: int
    option_id: int
    amount: int

# ... ClosePollPayload, OpenChestPayload ...
class ClosePollPayload(BaseModel): #...
class OpenChestPayload(BaseModel): #...

# --- Пользователи (без изменений) ---
@app.post("/api/auth")
async def api_auth(payload: InitPayload): # ...
@app.get("/api/me/{telegram_id}")
async def api_me(telegram_id: int): # ...

# --- Опросы ---
# --- ✨ ИЗМЕНЕНИЕ: принимаем min_bet_amount ---
@app.post("/api/polls")
async def api_create_poll(payload: CreatePollPayload):
    try:
        # ...
        poll_id = db.create_poll(
            payload.telegram_id, payload.question, payload.options, payload.min_bet_amount
        )
        # ...
    except Exception as e: # ...

@app.get("/api/polls")
async def api_list_polls(): # ... без изменений

@app.get("/api/polls/{poll_id}")
async def api_get_poll(poll_id: int): # ... без изменений

# --- ✨ ИЗМЕНЕНИЕ: принимаем и передаем amount ---
@app.post("/api/bet")
async def api_place_bet(payload: PlaceBetPayload):
    try:
        print("📥 /api/bet payload:", payload.dict())
        res = db.place_bet(payload.telegram_id, payload.poll_id, payload.option_id, payload.amount)
        print("📤 bet result:", res)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    except Exception as e: # ...

# ... /api/polls/close, Сундуки, Рейтинг (без изменений)
@app.post("/api/polls/close")
async def api_close_poll(payload: ClosePollPayload): #...
@app.get("/api/chests")
async def api_chests(): #...
@app.post("/api/chests/open")
async def api_open_chest(payload: OpenChestPayload): #...
@app.get("/api/rating")
async def api_rating(): #...

