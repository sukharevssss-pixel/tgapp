from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import db
import json


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)


class InitPayload(BaseModel):
    user_id: int
    username: str | None = None


@app.on_event("startup")
def startup():
    db.init_db()


@app.post("/api/init")
async def api_init(payload: InitPayload):
    db.ensure_user(payload.user_id, payload.username)
    user = db.get_user(payload.user_id)
    return {"ok": True, "user": user}


@app.get("/api/me/{user_id}")
async def api_me(user_id: int):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Заглушка: список опросов
@app.get("/api/polls")
async def api_polls():
    return []