import asyncio, os, uuid, re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="angela_ai_pro")

user_data = {}

def get_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 Отправить локацию", request_location=True)],
        [KeyboardButton(text="🔄 Режим Переводчика"), KeyboardButton(text="🎓 Режим Учителя")],
        [KeyboardButton(text="🌍 Режим Гида"), KeyboardButton(text="💬 Режим Друга")]
    ], resize_keyboard=True)

async def speak(message, text, mode, lang='ru'):
    filename = f"v_{uuid.uuid4()}.mp3"
    tts = gTTS(text=re.sub(r'[*_~`#]', '', text), lang=lang, slow=False)
    tts.save(filename)
    await message.answer_voice(voice=types.FSInputFile(filename), reply_markup=get_kb())
    if os.path.exists(filename): os.remove(filename)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"mode": "friend", "lang": "ru"}
    await message.answer("Анжела активирована. Приветствую! Как я могу помочь вам сегодня?", reply_markup=get_kb())

@dp.message(F.text.startswith("🔄 Режим Переводчика"))
async def set_trans(message: types.Message):
    user_data[message.from_user.id].update({"mode": "trans", "step": "lang"})
    await message.answer("Введите язык, на который нужно переводить (например: английский, узбекский).")

@dp.message(F.location)
async def handle_loc(message: types.Message):
    loc = geolocator.reverse((message.location.latitude, message.location.longitude), language='ru')
    system = "Ты профессиональный гид мирового уровня. Опиши историю, архитектуру и атмосферу места профессионально и доступно."
    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system}, {"role": "user", "content": loc.address}])
    await speak(message, resp.choices[0].message.content, "guide")

@dp.message(F.text | F.voice)
async def process(message: types.Message):
    uid = message.from_user.id
    text = message.text
    u = user_data.get(uid, {"mode": "friend", "lang": "ru"})
    
    if u.get("step") == "lang":
        u["target"] = text
        u["step"] = "ready"
        await message.answer(f"Принято. Переводчик настроен на {text}. Пишите фразу.")
        return

    # Ролевая логика
    if u["mode"] == "trans":
        system = f"Переведи строго на {u.get('target', 'английский')}. Никаких пояснений, только перевод."
    elif u["mode"] == "teacher":
        system = "Ты учитель языка. Обучай через игру, мотивируй, объясняй ошибки новичкам просто и вдохновляюще."
    else:
        system = "Ты Анжела, эмпатичный и мудрый друг. Отвечай кратко, четко и по делу."

    resp = await client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system}, {"role": "user", "content": text}])
    await speak(message, resp.choices[0].message.content, u["mode"])

async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Angela is Online"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
