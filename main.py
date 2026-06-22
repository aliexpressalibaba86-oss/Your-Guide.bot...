import sqlite3, asyncio, os, uuid, aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, WebAppInfo
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

# Load security keys
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_LINK = "https://t.me/your_guide_pro_bot"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

LANGS = ["Russian", "English", "Uzbek", "Turkish", "Chinese", "Arabic", "French", "German", "Spanish", "Italian"]
STICKERS = {
    "happy": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "neutral": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "guide": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ",
    "greeting": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ"
}

def init_db():
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, mode TEXT DEFAULT 'guide', user_lang TEXT DEFAULT 'Russian', bot_lang TEXT DEFAULT 'Russian')")
    conn.commit(); conn.close()

async def react(message, text, sticker_key="neutral"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["neutral"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename))
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

async def process_ai_logic(message, user_input):
    conn = sqlite3.connect("bot_memory.db")
    s = conn.execute("SELECT mode, user_lang, bot_lang FROM user_settings WHERE user_id=?", (message.from_user.id,)).fetchone()
    mode, u_lang, b_lang = s if s else ('guide', 'Russian', 'Russian')
    
    if mode == 'translator':
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": f"Translate {u_lang} to {b_lang}."}, {"role": "user", "content": user_input}])
        await react(message, resp.choices[0].message.content, "neutral")
    else:
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": "You are Angela, guide."}, {"role": "user", "content": user_input}])
        await react(message, resp.choices[0].message.content, "guide")
    conn.close()

@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    await react(message, "Hello! I am Angela, your guide.", "greeting")
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 Location")], 
        [KeyboardButton(text="🌐 Translator"), KeyboardButton(text="🤖 Guide")],
        [KeyboardButton(text="🚀 Open App", web_app=WebAppInfo(url="ВАША_ССЫЛКА_НА_APP"))]
    ], resize_keyboard=True)
    await message.answer("Choose action:", reply_markup=kb)

@dp.message(F.text == "🌐 Translator")
async def show_translator_menu(message: types.Message):
    await message.answer("Select mode:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 You", callback_data="side_user"), InlineKeyboardButton(text="🤖 Angela", callback_data="side_bot")]]))

@dp.message(F.text)
async def handle_text(message: types.Message):
    await process_ai_logic(message, message.text)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
