import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import db
import traceback
import bot 

# --- Lifespan для управления фоновыми задачами ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Этот код выполняется один раз при старте сервера
    print("🚀 Startup: инициализация базы данных")
    db.init_db()
    # Запускаем бота и его планировщик в фоновом режиме
    bot_task = asyncio.create_task(bot.start_bot())
    print("🤖 Бот и планировщик запущены...")
    
    yield # Приложение работает здесь
    
    # Этот код выполняется при остановке сервера
    print("🛑 Shutting down bot...")
    bot_task.cancel()


app = FastAPI(title="TG MiniApp Backend", lifespan=lifespan)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic-схемы (только необходимые