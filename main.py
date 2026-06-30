import os
import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# ФИКС ОШИБКИ ИМПОРТА: Добавляем текущую папку в путь поиска
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Теперь модули точно найдутся
from modules.writer import generate_script
from modules.generator import create_frames
from modules.editor import assemble_video

# Инициализация
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Логика конвейера
async def run_pipeline(niche):
    plan = await generate_script(niche, GROQ_API_KEY)
    images = await create_frames(plan)
    final_video = await assemble_video(images)
    return final_video

@dp.message() # Обработка любого текстового сообщения
async def handle_message(message: types.Message):
    await message.answer("🔍 Запуск конвейера: Анализ и генерация...")
    try:
        video_path = await run_pipeline(message.text)
        await message.answer_video(video=types.FSInputFile(video_path))
        await message.answer("✅ Готово! Контент создан.")
    except Exception as e:
        await message.answer(f"❌ Ошибка в конвейере: {str(e)}")

# Веб-сервер
async def on_startup(bot: Bot):
    url = os.getenv("RENDER_EXTERNAL_URL")
    await bot.set_webhook(f"{url}/webhook")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda app: on_startup(bot))
    
    # Запуск
    web.run_app(app, host="0.0.0.0", port=10000)
    
