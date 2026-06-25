import logging
import asyncio
import sqlite3
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TOKEN")
PORT = int(os.environ.get("PORT", 10000))

if not TOKEN:
    print("Критическая ошибка: Токен не задан!")
    sys.exit(1)

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

# --- ДНК АНЖЕЛЫ: СТИКЕРЫ REXY ---
REXY_MAP = {
    "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ": "Слушаю тебя внимательно, мой друг! Всё записываю. 🎧",
    "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ": "Блестяще! 🎆 Вот это уровень! Ты настоящий профи!",
    "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE": "Приятно слышать! Я всегда рядом, если что-то нужно. ✨",
    "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ": "Уже прокладываю маршрут! Это место таит много легенд. 🧭",
    "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ": "Отличный выбор! Давай сделаем это грандиозно. 🚀",
    "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ": "Ха-ха, я оценила! У тебя отличное чувство стиля. 😉",
    "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ": "Система активна. Я готова. Какая у нас сегодня цель? 🛠️"
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
        await message.answer(REXY_MAP[s_id])

@dp.message(F.text == "Поделиться 🔗")
async def share(message: types.Message):
    await message.answer("Приглашай друзей в нашу команду: https://t.me/your_guide_pro_bot")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def start_bot():
    await dp.start_polling(bot)

async def main():
    init_db()
    # Запуск веб-сервера (Render требует открытый порт)
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    # Работа бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
        
