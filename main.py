import asyncio, os, uuid, re, aiosqlite, logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim

# --- КОНФИГ ---
BOT_TOKEN = "ВАШ_ТОКЕН"
GROQ_API_KEY = "ВАШ_КЛЮЧ"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_pro_bot")

# СТИКЕРЫ (Сохранены как вы просили)
STICKERS = {
    "happy": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "neutral": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "thinking": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "greeting": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "success": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "secret": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "guide": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

async def init_db():
    async with aiosqlite.connect("bot_memory.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, mode TEXT DEFAULT 'guide', u_lang TEXT, b_lang TEXT)")
        await db.commit()

# --- КНОПКИ-КОМАНДЫ ---
def get_lang_kb(side):
    builder = InlineKeyboardBuilder()
    languages = ["Русский", "English", "O'zbekcha", "Türkçe", "Deutsch", "Français", "Español", "中文", "日本語", "العربية"]
    for lang in languages:
        builder.button(text=lang, callback_data=f"set_{side}_{lang}")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

async def react(message, text, sticker_key="neutral"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key))
    except: pass
    
    clean = re.sub(r'[*_~`]', '', text)
    filename = f"v_{uuid.uuid4()}.mp3"
    gTTS(text=clean, lang='ru').save(filename)
    await message.answer_voice(voice=FSInputFile(filename))
    if os.path.exists(filename): os.remove(filename)

# --- ХЕНДЛЕРЫ ---
@dp.callback_query(F.data == "main_menu")
async def main_menu(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Язык пользователя", callback_data="side_u"),
         InlineKeyboardButton(text="🤖 Язык Анжелы", callback_data="side_b")]
    ])
    await call.message.edit_text("⚙️ Выберите настройки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("side_"))
async def show_langs(call: CallbackQuery):
    side = call.data.split("_")[1]
    await call.message.edit_text("Выберите язык:", reply_markup=get_lang_kb(side))

@dp.callback_query(F.data.startswith("set_"))
async def set_lang(call: CallbackQuery):
    _, side, lang = call.data.split("_")
    async with aiosqlite.connect("bot_memory.db") as db:
        await db.execute(f"UPDATE user_settings SET {'u_lang' if side=='u' else 'b_lang'}=? WHERE user_id=?", (lang, call.from_user.id))
        await db.commit()
    await call.answer(f"✅ Язык {lang} установлен")

@dp.message(Command("start"))
async def start(message: types.Message):
    await react(message, "Привет, я Анжела. Я твой мудрый гид.", "greeting")

# --- БЕСКОНЕЧНЫЙ ЦИКЛ РАБОТЫ ---
async def main():
    await init_db()
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            print("Система запущена...")
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Системная ошибка: {e}. Перезапуск...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
  
