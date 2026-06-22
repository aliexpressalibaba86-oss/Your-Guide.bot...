import sqlite3, asyncio, os, uuid, aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim

# --- НАСТРОЙКИ ---
BOT_TOKEN = "тs"
GROQ_API_KEY = "gsi"
BOT_LINK = "https://t.me/your_guide_pro_bot"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_bot")

LANGS = ["Русский", "Английский", "Узбекский", "Турецкий", "Китайский", "Арабский", "Французский", "Немецкий", "Испанский", "Итальянский"]
STICKERS = {
    "happy": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
    "neutral": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
    "thinking": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
    "greeting": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
    "success": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
    "secret": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
    "guide": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
}

def init_db():
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, mode TEXT DEFAULT 'guide', user_lang TEXT DEFAULT 'Русский', bot_lang TEXT DEFAULT 'Русский')")
    conn.commit(); conn.close()

async def react(message, text, sticker_key="neutral"):
    try: await message.answer_sticker(sticker=STICKERS.get(sticker_key, STICKERS["neutral"]))
    except: pass
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=text, lang='ru')
    tts.save(filename)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отправить другу", switch_inline_query=f"Попробуй этого гида: {BOT_LINK}")]])
    await message.answer_voice(voice=types.FSInputFile(filename), reply_markup=kb)
    await message.answer(text)
    if os.path.exists(filename): os.remove(filename)

# --- ЛОГИКА ---
async def process_ai_logic(message, user_input):
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("DELETE FROM history WHERE rowid NOT IN (SELECT rowid FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 20) AND user_id=?", (message.from_user.id, message.from_user.id))
    s = conn.execute("SELECT mode, user_lang, bot_lang FROM user_settings WHERE user_id=?", (message.from_user.id,)).fetchone()
    mode, u_lang, b_lang = s if s else ('guide', 'Русский', 'Русский')
    
    if mode == 'translator':
        messages = [{"role": "system", "content": f"Ты переводчик. Переведи текст с {u_lang} на {b_lang}."}, {"role": "user", "content": user_input}]
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages)
        await react(message, f"Перевод: {resp.choices[0].message.content.replace('*', '')}", "neutral")
    else:
        conn.execute("INSERT INTO history VALUES (?, ?, ?)", (message.from_user.id, "user", user_input))
        rows = conn.execute("SELECT role, content FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10", (message.from_user.id,)).fetchall()
        system_prompt = "Ты Анжела, универсальный гид. Пиши ЧИСТЫМ текстом."
        resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system_prompt}] + [{"role": r[0], "content": r[1]} for r in reversed(rows)])
        answer = resp.choices[0].message.content.replace("*", "")
        conn.execute("INSERT INTO history VALUES (?, ?, ?)", (message.from_user.id, "assistant", answer))
        await react(message, answer, "guide")
    conn.commit(); conn.close()

# --- ХЕНДЛЕРЫ МЕНЮ ПЕРЕВОДЧИКА ---
@dp.message(F.text == "🌐 Переводчик")
async def show_main_translator_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Я", callback_data="side_user"), 
         InlineKeyboardButton(text="🤖 Анжела", callback_data="side_bot")]
    ])
    await message.answer("Выберите, для кого настраиваем язык:", reply_markup=kb)

@dp.callback_query(F.data.startswith("side_"))
async def show_lang_list(callback: CallbackQuery):
    side = callback.data.split("_")[1]
    buttons = [[InlineKeyboardButton(text=lang, callback_data=f"lang_set_{side}_{lang}")] for lang in LANGS]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    await callback.message.edit_text(f"Выберите язык для {side}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Я", callback_data="side_user"), 
         InlineKeyboardButton(text="🤖 Анжела", callback_data="side_bot")]
    ])
    await callback.message.edit_text("Выберите, для кого настраиваем язык:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("lang_set_"))
async def set_final_lang(callback: CallbackQuery):
    _, _, side, lang = callback.data.split("_")
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("INSERT OR REPLACE INTO user_settings (user_id, mode) VALUES (?, 'translator')", (callback.from_user.id,))
    col = "user_lang" if side == "user" else "bot_lang"
    conn.execute(f"UPDATE user_settings SET {col}=? WHERE user_id=?", (lang, callback.from_user.id))
    conn.commit(); conn.close()
    await callback.message.answer(f"✅ Установлено: {lang}. Режим перевода включен.")
    await callback.answer()

# --- ОСНОВНЫЕ ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    
    # Текст приветствия
    welcome_text = "Привет! Я Анжела. Я твой универсальный гид и переводчик. Чем могу помочь?"
    
    # Используем вашу функцию react: она отправит стикер, голос и текст
    # Мы используем ключ "greeting" для стикера
    await react(message, welcome_text, sticker_key="greeting")
    
    # Отправляем кнопки меню
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 Локация")], 
        [KeyboardButton(text="🌐 Переводчик"), KeyboardButton(text="🤖 Гид")]
    ], resize_keyboard=True)
    
    await message.answer("Выбирай действие:", reply_markup=kb)


@dp.message(F.text == "🤖 Гид")
async def back_to_guide(message: types.Message):
    conn = sqlite3.connect("bot_memory.db")
    conn.execute("UPDATE user_settings SET mode='guide' WHERE user_id=?", (message.from_user.id,))
    conn.commit(); conn.close()
    await react(message, "Я снова твой гид!", "happy")

@dp.message(F.location)
async def handle_loc(message: types.Message):
    loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='ru')
    await process_ai_logic(message, f"Я здесь: {loc.address}. Расскажи всё про это место.")

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    file = await bot.get_file(message.voice.file_id)
    path = f"{uuid.uuid4()}.ogg"
    await bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        data = aiohttp.FormData(); data.add_field('file', f); data.add_field('model', 'whisper-large-v3')
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, data=data) as resp:
                text = (await resp.json()).get("text", "...")
    os.remove(path); await process_ai_logic(message, text)

@dp.message(F.text)
async def handle_text(message: types.Message):
    if any(cmd in message.text.lower() for cmd in ["стоп", "выключить", "гид"]):
        await back_to_guide(message)
    else:
        await process_ai_logic(message, message.text)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
    
