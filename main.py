import sqlite3, asyncio, os, uuid, aiohttp, json
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

# Load settings from .env
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
    "thinking": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "greeting": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "success": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "secret": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "guide": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

def init_db():
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, mode TEXT DEFAULT 'guide', user_lang TEXT DEFAULT 'Russian', bot_lang TEXT DEFAULT 'Russian')")
    conn.commit(); conn.close()

async def react(message, text, sticker_key="neutral"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["neutral"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text, lang='ru')
    tts.save(filename)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Share", switch_inline_query=f"Try this guide: {BOT_LINK}")]])
    await message.answer_voice(voice=types.FSInputFile(filename), reply_markup=kb)
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

async def process_ai_logic(message, user_input):
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("DELETE FROM history WHERE rowid NOT IN (SELECT rowid FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 20) AND user_id=?", (message.from_user.id, message.from_user.id))
    s = conn.execute("SELECT mode, user_lang, bot_lang FROM user_settings WHERE user_id=?", (message.from_user.id,)).fetchone()
    mode, u_lang, b_lang = s if s else ('guide', 'Russian', 'Russian')
    
    if mode == 'translator':
        messages = [{"role": "system", "content": f"You are a translator. Translate from {u_lang} to {b_lang}."}, {"role": "user", "content": user_input}]
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages)
        await react(message, f"Translation: {resp.choices[0].message.content.replace('*', '')}", "neutral")
    else:
        conn.execute("INSERT INTO history VALUES (?, ?, ?)", (message.from_user.id, "user", user_input))
        rows = conn.execute("SELECT role, content FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10", (message.from_user.id,)).fetchall()
        system_prompt = "You are Angela, a universal guide. Write in CLEAR text."
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system_prompt}] + [{"role": r[0], "content": r[1]} for r in reversed(rows)])
        answer = resp.choices[0].message.content.replace("*", "")
        conn.execute("INSERT INTO history VALUES (?, ?, ?)", (message.from_user.id, "assistant", answer))
        await react(message, answer, "guide")
    conn.commit(); conn.close()

@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    await react(message, "Hello! I am Angela, your universal guide and translator.", sticker_key="greeting")
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Location")], [KeyboardButton(text="🌐 Translator"), KeyboardButton(text="🤖 Guide")]], resize_keyboard=True)
    await message.answer("Choose an action:", reply_markup=kb)

@dp.message(F.text == "🤖 Guide")
async def back_to_guide(message: types.Message):
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("UPDATE user_settings SET mode='guide' WHERE user_id=?", (message.from_user.id,))
    conn.commit(); conn.close()
    await react(message, "I am your guide again!", "happy")

@dp.message(F.location)
async def handle_loc(message: types.Message):
    loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='en')
    await process_ai_logic(message, f"I am here: {loc.address}. Tell me all about this place.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if "guide" in message.text.lower(): await back_to_guide(message)
    else: await process_ai_logic(message, message.text)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
    
