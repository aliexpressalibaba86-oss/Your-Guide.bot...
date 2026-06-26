import asyncio, os, uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim

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

# --- ПРИВЕТСТВИЕ И РЕЖИМЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"mode": "friend", "history": [], "name": None}
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Анжела 🤖"), KeyboardButton(text="Твой Гид 🧭")],
        [KeyboardButton(text="Локация 📍", request_location=True), KeyboardButton(text="Переводчик 🌐")],
        [KeyboardButton(text="Учитель языка 🎓"), KeyboardButton(text="Поделиться 🔗")],
        [KeyboardButton(text="Очистить память 🧹")]
    ], resize_keyboard=True)
    
    welcome_text = (
        "Привет! Меня зовут Анжела. Я твой персональный ИИ-помощник, гид по миру, профессиональный учитель языков и переводчик. "
        "Я умею рассказывать истории зданий, переводить фразы и учить языкам в игровом стиле. "
        "Как тебя зовут?"
    )
    await react(message, welcome_text, "ready")
    await message.answer("Выбери режим ниже:", reply_markup=kb)

@dp.message(F.text == "Очистить память 🧹")
async def clear_memory(message: types.Message):
    user_data[message.from_user.id]["history"] = []
    await message.answer("Я всё забыла! Память очищена. ✨")

@dp.message(F.text == "Твой Гид 🧭")
async def cmd_guide(message: types.Message):
    user_data[message.from_user.id]["mode"] = "guide"
    await react(message, "Режим Гида включен! Я знаю историю любой точки мира. Что тебя интересует?", "guide")

@dp.message(F.text == "Анжела 🤖")
async def cmd_angela(message: types.Message):
    user_data[message.from_user.id]["mode"] = "friend"
    await react(message, "Я здесь, твой мудрый друг! Спрашивай о чем угодно.", "angela")

# --- ЛОГИКА ОБРАБОТКИ ---
@dp.message(F.text | F.location)
async def handle_everything(message: types.Message):
    uid = message.from_user.id
    if uid not in user_data: user_data[uid] = {"mode": "friend", "history": [], "name": None}
    
    # Сохранение имени
    if not user_data[uid]["name"] and message.text and not message.text.startswith("/"):
        user_data[uid]["name"] = message.text
        await react(message, f"Приятно познакомиться, {message.text}! Чем могу помочь сегодня?", "angela")
        return

    # Логика работы
    text = message.location and f"Координаты: {message.location.latitude}, {message.location.longitude}" or message.text
    user_data[uid]["history"].append({"role": "user", "content": text})
    
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[
        {"role": "system", "content": f"Ты Анжела. Режим: {user_data[uid]['mode']}. Имя юзера: {user_data[uid]['name']}."}
    ] + user_data[uid]["history"][-10:])
    
    reply = resp.choices[0].message.content
    user_data[uid]["history"].append({"role": "assistant", "content": reply})
    
    await react(message, reply, user_data[uid]["mode"] if user_data[uid]["mode"] in STICKERS else "ready")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
    
