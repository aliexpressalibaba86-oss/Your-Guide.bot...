import asyncio, os, uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_LINK = "https://t.me/your_guide_pro_bot"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

STICKERS = {
    "angela": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "location": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "translator": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "teacher": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "guide": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "ready": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

user_data = {} 

async def react(message, text, sticker_key="ready"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text[:300], lang='ru')
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename))
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

# --- РАСПОЗНАВАНИЕ ГОЛОСА ---
async def transcribe_voice(voice_file_id):
    file = await bot.get_file(voice_file_id)
    file_path = file.file_path
    await bot.download_file(file_path, "voice.ogg")
    audio_file = open("voice.ogg", "rb")
    # Используем модель Whisper через Groq для быстрого распознавания
    transcript = await client.audio.transcriptions.create(model="whisper-large-v3", file=audio_file)
    return transcript.text

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"mode": "friend", "history": [], "name": None}
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Анжела 🤖"), KeyboardButton(text="Твой Гид 🧭")],
        [KeyboardButton(text="Локация 📍", request_location=True), KeyboardButton(text="Переводчик 🌐")],
        [KeyboardButton(text="Учитель языка 🎓"), KeyboardButton(text="Поделиться 🔗")],
        [KeyboardButton(text="Очистить память 🧹")]
    ], resize_keyboard=True)
    await react(message, "Привет! Я Анжела. Как тебя зовут?", "ready")
    await message.answer("Выбери действие:", reply_markup=kb)

@dp.message(F.text == "Поделиться 🔗")
async def cmd_share(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выбрать друга и отправить 🚀", switch_inline_query=f"Попробуй этого ИИ-гида: {BOT_LINK}")]
    ])
    await message.answer("Нажми кнопку ниже, выбери друга, и я отправлю ему ссылку:", reply_markup=kb)

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    text = await transcribe_voice(message.voice.file_id)
    await process_request(message, text)

@dp.message(F.text | F.location)
async def handle_text_or_loc(message: types.Message):
    text = message.location and f"Мои координаты: {message.location.latitude}, {message.location.longitude}" or message.text
    await process_request(message, text)

async def process_request(message, text):
    uid = message.from_user.id
    if uid not in user_data: user_data[uid] = {"mode": "friend", "history": [], "name": None}
    
    if not user_data[uid]["name"] and not message.text.startswith("/"):
        user_data[uid]["name"] = text
        await react(message, f"Приятно познакомиться, {text}! Чем помочь?", "angela")
        return

    user_data[uid]["history"].append({"role": "user", "content": text})
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[
        {"role": "system", "content": f"Ты Анжела. Режим: {user_data[uid]['mode']}."}
    ] + user_data[uid]["history"][-10:])
    
    reply = resp.choices[0].message.content
    await react(message, reply, user_data[uid].get("mode", "ready"))

# --- WEB СЕРВЕР ---
async def web_server(request):
    return web.Response(text="Angela Bot is alive!")

async def main():
    app = web.Application()
    app.router.add_get('/', web_server)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
