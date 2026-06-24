import asyncio
import os
import uuid
import aiohttp
import aiosqlite # Используем асинхронную базу
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim

# --- БЕЗОПАСНОСТЬ: Читаем ключи из переменных среды ---
# В Render вы добавите эти ключи во вкладку Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_pro_bot")

# --- БАЗА ДАННЫХ (Асинхронная) ---
async def init_db():
    async with aiosqlite.connect("bot_memory.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)")
        await db.commit()

async def save_history(user_id, role, content):
    async with aiosqlite.connect("bot_memory.db") as db:
        await db.execute("INSERT INTO history VALUES (?, ?, ?)", (user_id, role, content))
        await db.commit()

async def get_full_history(user_id):
    async with aiosqlite.connect("bot_memory.db") as db:
        async with db.execute("SELECT role, content FROM history WHERE user_id=? ORDER BY rowid ASC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]
            
