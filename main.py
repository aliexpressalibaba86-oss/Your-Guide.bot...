import asyncio, os, uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from langdetect import detect
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_URL = "https://t.me/your_guide_pro_bot" 
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

STICKERS = {
    "angela": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "guide": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "translator": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "teacher": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "ready": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

user_data = {}

def get_share_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить друзьям", url=f"https://t.me/share/url?url={@your_guide_pro_bot}&text=Привет! Попробуй Анжелу - твоего личного ИИ-помощника:")]
    ])

async def react(message, text, sticker_key="ready", lang='ru'):
    # Сначала всегда отправляем стикер
    await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    
    filename = f"v_{uuid.uuid4()}.mp3"
    # Настройки для более естественного голоса
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename))
    await message.answer(text, reply_markup=get_share_kb())
    if os.path.exists(filename): os.remove(filename)

async def transcribe_voice(voice_file_id):
    file = await bot.get_file(voice_file_id)
    await bot.download_file(file.file_path, "voice.ogg")
    audio_file = open("voice.ogg", "rb")
    transcript = await client.audio.transcriptions.create(model="whisper-large-v3", file=audio_file)
    return transcript.text

async def handle_ping(request):
    return web.Response(text="Bot is running!")

@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"mode": "friend", "history": [], "name": None, "waiting_name": True, "lang": "ru"}
    msg = "Привет! Я Анжела, твой персональный ИИ-помощник. Я мудрый друг, профессиональный гид, переводчик и учитель языков. Как тебя зовут?"
    await react(message, msg, "angela", "ru")

@dp.message(F.text == "Очистить память 🧹")
async def clear_memory(message: types.Message):
    lang = user_data[message.from_user.id].get("lang", "ru")
    user_data[message.from_user.id] = {"mode": "friend", "history": [], "name": user_data[message.from_user.id].get("name"), "lang": lang}
    await react(message, "Память очищена, начинаем с чистого листа!", "ready", lang)

@dp.message(F.voice | F.text | F.location)
async def handle_all(message: types.Message):
    uid = message.from_user.id
    if uid not in user_data: user_data[uid] = {"mode": "friend", "history": [], "waiting_name": True, "lang": "ru"}
    
    text = await transcribe_voice(message.voice.file_id) if message.voice else message.text
    
    # 1. Знакомство
    if user_data[uid].get("waiting_name"):
        try: user_data[uid]["lang"] = detect(text)
        except: user_data[uid]["lang"] = "ru"
        user_data[uid]["name"] = text
        user_data[uid]["waiting_name"] = False
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Анжела 🤖"), KeyboardButton(text="Твой Гид 🧭")], [KeyboardButton(text="Локация 📍", request_location=True), KeyboardButton(text="Переводчик 🌐")], [KeyboardButton(text="Учитель языка 🎓"), KeyboardButton(text="Очистить память 🧹")]], resize_keyboard=True)
        msg = f"Приятно познакомиться, {text}! Чем я могу помочь тебе сегодня?"
        await message.answer("Режим активирован.", reply_markup=kb)
        await react(message, msg, "angela", user_data[uid]["lang"])
        return

    # 2. Локация
    if message.location:
        loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='ru')
        text = f"Я нахожусь здесь: {loc.address}. Расскажи мне подробную историю этого места, что здесь интересного, какие здания и достопримечательности рядом."

    # 3. Ответ ИИ
    mode = user_data[uid].get("mode", "friend")
    lang = user_data[uid]["lang"]
    system_content = f"Ты Анжела, лучший помощник для {user_data[uid]['name']}. Общайся на {lang}. Будь точна, экспертна и дружелюбна."
    
    user_data[uid]["history"].append({"role": "user", "content": text})
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system_content}] + user_data[uid]["history"][-10:])
    reply = resp.choices[0].message.content
    user_data[uid]["history"].append({"role": "assistant", "content": reply})
    await react(message, reply, mode, lang)

async def main():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
