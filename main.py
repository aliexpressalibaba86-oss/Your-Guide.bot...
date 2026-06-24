import sqlite3, asyncio, os, uuid, aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from aiohttp import web # Добавлено для Render

# --- НАСТРОЙКИ (Берем из переменных окружения Render) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_LINK = "https://t.me/your_guide_pro_bot"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не засыпал) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- ОСТАЛЬНАЯ ЛОГИКА (ваша функция react, process_ai_logic и т.д.) ---
# (Здесь остается ваш код: init_db, react, process_ai_logic, хендлеры...)

# --- ЗАПУСК ---
async def main():
    init_db()
    await start_web_server() # Запускаем "обманку" для Render
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
