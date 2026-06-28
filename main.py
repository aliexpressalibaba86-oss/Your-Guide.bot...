import asyncio, os, uuid, re
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
    "angela": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "guide": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "teacher": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "translator": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "friend": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "ready": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "welcome": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

user_data = {}

def clean_for_speech(text):
    return re.sub(r'[*_~`#]', '', text)

def get_share_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться с друзьями", url=f"https://t.me/share/url?url={BOT_URL}&text=Привет! Попробуй Анжелу - твоего профессионального ИИ-гида, учителя и переводчика:")]
    ])

async def react(message, text, sticker_key="ready", lang='ru'):
    await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=clean_for_speech(text), lang=lang, slow=False)
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

@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"history": [], "name": None, "waiting_name": True, "lang": "ru", "mode": "friend"}
    intro = "Ассаламу алейкум! Я Анжела. Я твой гид, переводчик, учитель и мудрый друг. Я отвечу на любые вопросы точно и ясно. Как тебя зовут?"
    await react(message, intro, "welcome", "ru")

@dp.message(F.text == "🧹 Очистить память")
async def clear_memory(message: types.Message):
    uid = message.from_user.id
    user_data[uid]["history"] = []
    await react(message, "Память очищена! Готова к новым задачам.", "ready", user_data[uid].get("lang", "ru"))

@dp.message(F.location)
async def handle_location(message: types.Message):
    uid = message.from_user.id
    # Получаем максимально подробные данные о локации
    loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='ru', addressdetails=True)
    addr = loc.raw.get('address', {})
    # Собираем точный адрес
    full_addr = f"{addr.get('country', '')}, {addr.get('city') or addr.get('town') or addr.get('village', '')}, {addr.get('suburb') or addr.get('quarter', '')}, {addr.get('road', '')} {addr.get('house_number', '')}"
    
    text = f"Я определила твое местоположение: {full_addr}. Я как профессиональный гид проанализирую историю этих зданий, района и расскажу обо всем с идеальной точностью."
    await handle_text_logic(message, text)

@dp.message(F.voice | F.text)
async def handle_text(message: types.Message):
    text = await transcribe_voice(message.voice.file_id) if message.voice else message.text
    await handle_text_logic(message, text)

async def handle_text_logic(message: types.Message, text: str):
    uid = message.from_user.id
    if uid not in user_data: user_data[uid] = {"history": [], "waiting_name": True, "lang": "ru", "mode": "friend"}
    
    if user_data[uid].get("waiting_name"):
        user_data[uid]["lang"] = detect(text)
        user_data[uid]["name"] = text
        user_data[uid]["waiting_name"] = False
        await react(message, f"Приятно познакомиться, {text}! Чем могу помочь сегодня?", "angela", user_data[uid]["lang"])
        return

    text_lower = text.lower()
    if "учи" in text_lower or "lesson" in text_lower: mode = "teacher"
    elif "перевод" in text_lower or "translate" in text_lower: mode = "translator"
    elif "гид" in text_lower or "путешеств" in text_lower: mode = "guide"
    else: mode = "friend"

    system_content = {
        "teacher": "Ты профессиональный учитель. Стиль — игровой, мотивирующий. Хвали за успехи, как салют. Говори как носитель.",
        "translator": "Ты профессиональный лингвист-переводчик. Переводи идеально, точно, ясно.",
        "guide": "Ты элитный международный гид. Рассказывай историю, архитектуру и факты с безупречной точностью.",
        "friend": "Ты Анжела, мудрый друг. Отвечай с юмором, легкостью и теплом."
    }.get(mode, "Ты Анжела, универсальный помощник.")

    user_data[uid]["history"].append({"role": "user", "content": text})
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", 
        messages=[{"role": "system", "content": system_content + f" Общайся на {user_data[uid]['lang']}."}] + user_data[uid]["history"][-10:])
    
    reply = resp.choices[0].message.content
    user_data[uid]["history"].append({"role": "assistant", "content": reply})
    await react(message, reply, mode, user_data[uid]["lang"])

async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
