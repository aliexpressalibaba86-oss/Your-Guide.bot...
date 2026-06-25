import sqlite3, asyncio, os, uuid, logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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

# СТИКЕРЫ (Анжела реагирует на каждый режим)
STICKERS = {
    "angela": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "location": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "translator": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "teacher": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "guide": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "ready": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

user_data = {} # Временная память: {user_id: {"name": "...", "mode": "..."}}

async def react(message, text, sticker_key="ready"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text[:200], lang='ru')
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename))
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

# --- РЕЖИМЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Анжела 🤖"), KeyboardButton(text="Твой Гид 🧭")],
        [KeyboardButton(text="Локация 📍", request_location=True), KeyboardButton(text="Переводчик 🌐")],
        [KeyboardButton(text="Учитель языка 🎓"), KeyboardButton(text="Поделиться 🔗")]
    ], resize_keyboard=True)
    await react(message, "Привет! Я Анжела. Я твой гид, учитель и друг. Как тебя зовут?", "ready")

@dp.message(F.text == "Анжела 🤖")
async def cmd_angela(message: types.Message):
    await react(message, "Я — Анжела, твой мудрый друг. Спрашивай о чем угодно, я отвечу честно и правильно.", "angela")

@dp.message(F.location)
async def handle_loc(message: types.Message):
    loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='ru')
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": f"Где я? Дай точные координаты и описание здания/места: {loc.address}"}])
    await react(message, resp.choices[0].message.content, "location")

@dp.message(F.text == "Переводчик 🌐")
async def cmd_trans(message: types.Message):
    user_data[message.from_user.id] = "translator"
    await react(message, "Режим переводчика. Напиши слово или фразу, я переведу.", "translator")

@dp.message(F.text == "Учитель языка 🎓")
async def cmd_teacher(message: types.Message):
    user_data[message.from_user.id] = "teacher"
    await react(message, "Я твой учитель для туристов! Какой язык тренируем?", "teacher")

@dp.message(F.text == "Твой Гид 🧭")
async def cmd_guide(message: types.Message):
    user_data[message.from_user.id] = "guide"
    await react(message, "Режим Гида активен! Я знаю историю всех точек мира. Куда направимся?", "guide")

@dp.message(F.text == "Поделиться 🔗")
async def cmd_share(message: types.Message):
    await message.answer("Скопируй и отправь друзьям:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поделиться 🔗", switch_inline_query="Привет! Попробуй Анжелу - лучшего ИИ-гида: @your_guide_pro_bot")]
    ]))

@dp.message(F.text)
async def handle_text(message: types.Message):
    uid = message.from_user.id
    mode = user_data.get(uid)

    if mode == "translator":
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Переведи фразу: {message.text}"}])
        await react(message, resp.choices[0].message.content, "translator")
    elif mode == "teacher":
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Ты учитель языка. Объясни фразу: {message.text}"}])
        await react(message, resp.choices[0].message.content, "teacher")
    elif mode == "guide":
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Расскажи интересную историю для туриста: {message.text}"}])
        await react(message, resp.choices[0].message.content, "guide")
    else:
        # Анжела (дружеский режим)
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": message.text}])
        await react(message, resp.choices[0].message.content, "angela")

# --- ЗАПУСК ---
async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Angela System Online"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
