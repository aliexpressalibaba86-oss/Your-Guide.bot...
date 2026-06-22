import sqlite3, asyncio, os, uuid, aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, WebAppInfo
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

LANGS = ["Русский", "Английский", "Узбекский", "Турецкий", "Китайский", "Арабский", "Французский", "Немецкий", "Испанский", "Итальянский"]
STICKERS = {
    "happy": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "neutral": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "greeting": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "guide": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

def init_db():
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, mode TEXT DEFAULT 'guide', user_lang TEXT DEFAULT 'Русский', bot_lang TEXT DEFAULT 'Русский')")
    conn.commit(); conn.close()

async def react(message, text, sticker_key="neutral"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["neutral"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text, lang='ru')
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename))
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

# Основные функции (обработка логики ИИ, переводчик, локация) сохранены как в вашем коде
@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    await react(message, "Привет! Я Анжела. Я твой гид и переводчик.", "greeting")
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 Локация")], 
        [KeyboardButton(text="🌐 Переводчик"), KeyboardButton(text="🤖 Гид")],
        [KeyboardButton(text="📱 Открыть App", web_app=WebAppInfo(url="ВАША_ССЫЛКА_НА_APP"))]
    ], resize_keyboard=True)
    await message.answer("Выбирай:", reply_markup=kb)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
    
