import sqlite3, asyncio, os, uuid, logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from openai import AsyncOpenAI
from gtts import gTTS
from aiohttp import web
from geopy.geocoders import Nominatim

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

STICKERS = {
    "ready": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ",
    "listening": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "success": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "guide": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "inspiration": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "wink": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ"
}

user_states = {}

async def react(message, text, sticker_key="ready"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text[:200], lang='ru')
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename))
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Анжела 🤖")],
        [KeyboardButton(text="Локация 📍"), KeyboardButton(text="Переводчик 🌐")],
        [KeyboardButton(text="Режим Гида 🧭")]
    ], resize_keyboard=True)
    await react(message, "Привет! Я снова в строю. Чем могу помочь?", "ready")
    await message.answer("Выбирай:", reply_markup=kb)

@dp.message(F.text == "Анжела 🤖")
async def cmd_who(message: types.Message):
    await react(message, "Я — Анжела, твой персональный ИИ.", "wink")

@dp.message(F.text == "Локация 📍")
async def cmd_loc(message: types.Message):
    await message.answer("Пришли мне геопозицию, чтобы я рассказала об этом месте.")

@dp.message(F.location)
async def handle_location(message: types.Message):
    loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='ru')
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": f"Расскажи факты про место: {loc.address}"}])
    await react(message, resp.choices[0].message.content, "guide")

@dp.message(F.text == "Переводчик 🌐")
async def cmd_trans(message: types.Message):
    user_states[message.from_user.id] = "lang_select"
    await react(message, "Режим учителя включен! На каком языке будем учиться?", "success")

@dp.message(F.text == "Режим Гида 🧭")
async def cmd_guide(message: types.Message):
    await react(message, "Режим гида активирован! Спрашивай о любой стране или городе.", "inspiration")

@dp.message(F.text)
async def handle_text(message: types.Message):
    uid = message.from_user.id
    if user_states.get(uid) == "lang_select":
        user_states[uid] = {"mode": "learning", "lang": message.text}
        await message.answer(f"Отлично, учим {message.text}. Напиши фразу для перевода.")
        return
    if isinstance(user_states.get(uid), dict):
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": f"Ты учитель языка {user_states[uid]['lang']}. Переведи и объясни грамматику."},
                      {"role": "user", "content": message.text}])
        await react(message, resp.choices[0].message.content, "listening")
        return

    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": message.text}])
    await react(message, resp.choices[0].message.content, "ready")

# --- ПРАВИЛЬНЫЙ ЗАПУСК ---
async def main():
    # Запускаем веб-сервер и бота одновременно
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
