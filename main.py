import asyncio, os, uuid, re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
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

def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 Отправить мою локацию")],
        [KeyboardButton(text="🔄 Режим Переводчика")],
        [KeyboardButton(text="🎓 Режим Учителя")],
        [KeyboardButton(text="🌍 Режим Гида")],
        [KeyboardButton(text="💬 Режим Друга")]
    ], resize_keyboard=True)

def get_share_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться с друзьями", url=f"https://t.me/share/url?url={BOT_URL}&text=Попробуй Анжелу - профессиональный ИИ-инструмент:")]
    ])

async def react(message, text, sticker_key="ready", lang='ru'):
    await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["ready"]))
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=clean_for_speech(text), lang=lang, slow=False)
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename), reply_markup=get_share_kb())
    if os.path.exists(filename): os.remove(filename)

async def transcribe_voice(voice_file_id):
    file = await bot.get_file(voice_file_id)
    await bot.download_file(file.file_path, "voice.ogg")
    audio_file = open("voice.ogg", "rb")
    transcript = await client.audio.transcriptions.create(model="whisper-large-v3", file=audio_file)
    return transcript.text

@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"waiting_name": True, "mode": "friend", "target_lang": None}
    await react(message, "Ассаламу алейкум! Я Анжела. Я твой гид, переводчик, учитель и мудрый друг. Как тебя зовут?", "welcome", "ru")

@dp.message(F.text.in_(["🔄 Режим Переводчика", "🎓 Режим Учителя", "🌍 Режим Гида", "💬 Режим Друга"]))
async def change_mode(message: types.Message):
    uid = message.from_user.id
    if "Переводчика" in message.text:
        user_data[uid]["mode"] = "translator"
        user_data[uid]["target_lang"] = None
        await react(message, "Режим переводчика. На какой язык мне переводить?", "translator", "ru")
    elif "Учителя" in message.text:
        user_data[uid]["mode"] = "teacher"
        await react(message, "Режим учителя активирован. Жду твои вопросы по языку.", "teacher", "ru")
    elif "Гида" in message.text:
        user_data[uid]["mode"] = "guide"
        await react(message, "Режим гида. Отправь локацию, я расскажу историю места.", "guide", "ru")
    else:
        user_data[uid]["mode"] = "friend"
        await react(message, "Режим друга. Мы можем пообщаться.", "friend", "ru")

@dp.message(F.location)
async def handle_location(message: types.Message):
    loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='ru', addressdetails=True)
    addr = loc.raw.get('address', {})
    full_addr = f"{addr.get('country', '')}, {addr.get('city') or addr.get('town') or addr.get('road', '')}"
    system = "Ты профессиональный гид. Анализируй локацию и рассказывай историю с безупречной точностью."
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system}, {"role": "user", "content": f"Я в {full_addr}"}])
    await react(message, resp.choices[0].message.content, "guide", "ru")

@dp.message(F.voice | F.text)
async def handle_text(message: types.Message):
    uid = message.from_user.id
    text = await transcribe_voice(message.voice.file_id) if message.voice else message.text
    
    if user_data.get(uid, {}).get("waiting_name"):
        user_data[uid]["name"] = text
        user_data[uid]["waiting_name"] = False
        await react(message, f"Приятно познакомиться, {text}! Выбери режим в меню.", "angela", "ru")
        await message.answer("Выбери режим:", reply_markup=get_main_kb())
        return

    mode = user_data[uid].get("mode", "friend")
    
    if mode == "translator":
        if not user_data[uid].get("target_lang"):
            user_data[uid]["target_lang"] = text
            await react(message, f"Принято. Перевожу на {text}. Пиши текст.", "translator", "ru")
            return
        system = f"Переведи строго на {user_data[uid]['target_lang']}. НИКАКИХ КОММЕНТАРИЕВ, ТОЛЬКО ПЕРЕВОД."
    elif mode == "teacher":
        system = "Ты строгий учитель языка. Исправляй ошибки, объясняй правила. Без лишней болтовни."
    else:
        system = "Ты Анжела, мудрый друг. Отвечай кратко и с теплом."

    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system}, {"role": "user", "content": text}])
    await react(message, resp.choices[0].message.content, mode, "ru")

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
         
