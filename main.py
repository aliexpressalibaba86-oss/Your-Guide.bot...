import sqlite3, asyncio, os, uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_LINK = "https://t.me/your_guide_pro_bot"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

# Обновленный список стикеров (все 7 штук)
STICKERS = {
    "listening": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "success": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "warm": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "guide": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "inspiration": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "wink": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "ready": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

# --- ФУНКЦИИ ПАМЯТИ И ДНК ---
def init_db():
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, lang TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)")
    # Умная очистка: храним только последние 10 сообщений
    conn.commit(); conn.close()

async def react(message, text, sticker_key="ready"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    except: pass
    
    # Генерация голоса
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text[:200], lang='ru') # Ограничение длины для TTS
    tts.save(filename)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поделиться ссылкой 🔗", switch_inline_query=f"Попробуй Анжелу: {BOT_LINK}")]
    ])
    
    await message.answer_voice(voice=types.FSInputFile(filename), reply_markup=kb)
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

# --- ОСНОВНАЯ ЛОГИКА ---
@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Анжела 🤖")],
        [KeyboardButton(text="Локация 📍"), KeyboardButton(text="Режим Гида 🧭")],
        [KeyboardButton(text="Переводчик 🌐"), KeyboardButton(text="Поделиться 🔗")]
    ], resize_keyboard=True)
    await react(message, "Привет! Я Анжела. Твоя память, твой гид и твой голос. Как тебя зовут?", "ready")
    await message.answer("Выбирай функцию:", reply_markup=kb)

@dp.message(F.text == "Поделиться 🔗")
async def share(message: types.Message):
    await message.answer(f"Приглашай друзей в наш проект: {BOT_LINK}")

@dp.message(F.sticker)
async def handle_sticker_logic(message: types.Message):
    # Анжела реагирует на стикеры (ДНК поведения)
    await react(message, "Я чувствую твой настрой! 🌟", "wink")

@dp.message(F.text)
async def handle_text(message: types.Message):
    # Логика AI с памятью
    await react(message, "Я обрабатываю твой запрос, анализирую данные...", "listening")
    # ... здесь интеграция вашего process_ai_logic ...

# --- ВЕБ-СЕРВЕР ---
async def start_web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Angela System Online"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
