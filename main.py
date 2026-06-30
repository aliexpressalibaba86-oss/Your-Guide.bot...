import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Теперь импорты работают напрямую из корня
from writer import generate_script
from generator import create_frames
from editor import assemble_video

# Инициализация
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def run_pipeline(niche):
    # Генерация сценария
    plan = await generate_script(niche, GROQ_API_KEY)
    # Создание кадров
    images = await create_frames(plan)
    # Сборка видео
    final_video = await assemble_video(images)
    return final_video

@dp.message()
async def handle_message(message: types.Message):
    await message.answer("🔍 Запуск конвейера: Анализ трендов и генерация контента...")
    try:
        video_path = await run_pipeline(message.text)
        await message.answer_video(video=types.FSInputFile(video_path))
        await message.answer("✅ Контент готов к публикации!")
    except Exception as e:
        await message.answer(f"❌ Ошибка в конвейере: {str(e)}")

async def on_startup(bot: Bot):
    url = os.getenv("RENDER_EXTERNAL_URL")
    if url:
        await bot.set_webhook(f"{url}/webhook")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda app: on_startup(bot))
    
    # Render требует порт 10000
    web.run_app(app, host="0.0.0.0", port=10000)
    
