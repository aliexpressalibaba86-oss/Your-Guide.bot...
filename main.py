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
        [InlineKeyboardButton(text="📤 Отправить друзьям", url=f"https://t.me/share/url?url={BOT_URL}&text=Привет! Попробуй этого крутого ИИ-помощника Анжелу:")]
    ])

async def react(message, text, sticker_key="ready", lang='ru'):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
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

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def health_check(request):
    return web.Response(text="Bot is running!")

@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"mode": "friend", "history": [], "name": None, "waiting_name": True, "lang": "ru"}
    await message.answer("Привет! / Hi! Please write your name or say hello to start.")

@dp.message(F.text == "Очистить память 🧹")
async def clear_memory(message: types.Message):
    lang = user_data[message.from_user.id].get("lang", "ru")
    user_data[message.from_user.id] = {"mode": "friend", "history": [], "name": user_data[message.from_user.id].get("name"), "lang": lang}
    await message.answer("🧹 Память очищена." if lang == 'ru' else "🧹 Memory cleared.")

@dp.message(F.voice | F.text)
async def handle_all(message: types.Message):
    uid = message.from_user.id
    if uid not in user_data: user_data[uid] = {"mode": "friend", "history": [], "waiting_name": True, "lang": "ru"}
    
    text = await transcribe_voice(message.voice.file_id) if message.voice else message.text
    
    if user_data[uid].get("waiting_name"):
        try: user_data[uid]["lang"] = detect(text)
        except: user_data[uid]["lang"] = "ru"
        user_data[uid]["name"] = text
        user_data[uid]["waiting_name"] = False
        
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="Анжела 🤖"), KeyboardButton(text="Твой Гид 🧭")],
            [KeyboardButton(text="Локация 📍", request_location=True), KeyboardButton(text="Переводчик 🌐")],
            [KeyboardButton(text="Учитель языка 🎓"), KeyboardButton(text="Очистить память 🧹")]
        ], resize_keyboard=True)
        
        msg = f"Приятно познакомиться, {text}! Я Анжела. Выбери режим." if user_data[uid]["lang"] == 'ru' else f"Nice to meet you, {text}! I am Angela. Choose a mode."
        await message.answer("Режим выбран.", reply_markup=kb)
        await react(message, msg, "angela", user_data[uid]["lang"])
        return

    mode = user_data[uid].get("mode", "friend")
    lang = user_data[uid]["lang"]
    
    system_content = f"You are Angela, a wise AI assistant. Communicate in {lang}. User name: {user_data[uid]['name']}."
    
    user_data[uid]["history"].append({"role": "user", "content": text})
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", 
        messages=[{"role": "system", "content": system_content}] + user_data[uid]["history"][-10:])
    
    reply = resp.choices[0].message.content
    user_data[uid]["history"].append({"role": "assistant", "content": reply})
    await react(message, reply, mode, lang)

async def main():
    # Запуск веб-сервера
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
