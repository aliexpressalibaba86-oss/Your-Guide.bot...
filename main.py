import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TOKEN")
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ (Умная память) ---
def init_db():
    conn = sqlite3.connect("angela_memory.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, name TEXT, lang TEXT, behavior TEXT)""")
    conn.commit()
    conn.close()

# --- СТИКЕРЫ REXY И ИХ РЕАКЦИИ ---
REXY_MAP = {
    "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ": ("Rexy_Listening", "Слушаю тебя внимательно, мой друг! Всё записываю. 🎧"),
    "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ": ("Rexy_Success", "Блестяще! 🎆 Вот это уровень! Ты настоящий профи!"),
    "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE": ("Rexy_Warm", "Приятно слышать! Я всегда рядом, если что-то нужно. ✨"),
    "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ": ("Rexy_Guide", "Уже прокладываю маршрут! Это место таит много легенд. 🧭"),
    "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ": ("Rexy_Inspiration", "Отличный выбор! Давай сделаем это грандиозно. 🚀"),
    "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ": ("Rexy_Wink", "Ха-ха, я оценила! У тебя отличное чувство стиля. 😉"),
    "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ": ("Rexy_Ready", "Система активна. Я готова. Какая у нас сегодня цель? 🛠️")
}

# --- КНОПКИ ---
def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Анжела 🤖")],
        [KeyboardButton(text="Локация 📍"), KeyboardButton(text="Режим Гида 🧭")],
        [KeyboardButton(text="Переводчик 🌐"), KeyboardButton(text="Учитель языка 📚")],
        [KeyboardButton(text="Поделиться 🔗")]
    ], resize_keyboard=True)

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет. Я — Анжела. Твой друг, гид и универсальный помощник. Как тебя зовут?", reply_markup=get_main_menu())

@dp.message(F.sticker)
async def handle_sticker(message: types.Message):
    s_id = message.sticker.file_id
    if s_id in REXY_MAP:
        name, reaction = REXY_MAP[s_id]
        await message.answer(f"[{name}] {reaction}")

@dp.message(F.text == "Поделиться 🔗")
async def share(message: types.Message):
    await message.answer("Приглашай друзей в нашу команду: https://t.me/your_guide_pro_bot")

# --- WEB-СЕРВЕР ---
async def web_handler(request):
    return web.Response(text="Angela Bot is live!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', web_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    init_db()
    await asyncio.gather(start_server(), dp.start_polling(bot))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
