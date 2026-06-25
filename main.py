import sqlite3, asyncio, os, uuid, logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from openai import AsyncOpenAI
from gtts import gTTS
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_LINK = "https://t.me/your_guide_pro_bot"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

STICKERS = {
    "listening": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "success": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "warm": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "guide": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "inspiration": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "wink": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "ready": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

# --- ФУНКЦИИ ---
def init_db():
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit(); conn.close()

async def react(message, text, sticker_key="ready"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text[:200], lang='ru')
    tts.save(filename)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Поделиться 🔗", switch_inline_query=f"Попробуй: {BOT_LINK}")]])
    await message.answer_voice(voice=types.FSInputFile(filename), reply_markup=kb)
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

# --- ХЕНДЛЕРЫ-КОМАНДЫ (Кнопки) ---
@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Анжела 🤖")],
        [KeyboardButton(text="Локация 📍"), KeyboardButton(text="Режим Гида 🧭")],
        [KeyboardButton(text="Переводчик 🌐"), KeyboardButton(text="Поделиться 🔗")]
    ], resize_keyboard=True)
    await react(message, "Привет! Я Анжела, твой гид. Что делаем?", "ready")
    await message.answer("Выбирай:", reply_markup=kb)

@dp.message(F.text == "Анжела 🤖")
async def cmd_angela(message: types.Message):
    await react(message, "Я здесь! Готова помогать тебе в любой задаче.", "wink")

@dp.message(F.text == "Режим Гида 🧭")
async def cmd_guide(message: types.Message):
    await react(message, "Режим Гида активен. Спрашивай о любом месте!", "guide")

@dp.message(F.text == "Переводчик 🌐")
async def cmd_translator(message: types.Message):
    await react(message, "Я переведу любой текст. Просто напиши его.", "success")

# --- ЛОГИКА ОБРАБОТКИ ---
@dp.message(F.text)
async def handle_text(message: types.Message):
    # Если это не кнопка, отправляем в ИИ
    if message.text in ["Анжела 🤖", "Режим Гида 🧭", "Переводчик 🌐", "Поделиться 🔗"]: return
    
    try:
        resp = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": message.text}]
        )
        await react(message, resp.choices[0].message.content, "listening")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# --- ВЕБ-СЕРВЕР ---
async def start_web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    
