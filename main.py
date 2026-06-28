import asyncio, os, uuid, re
from aiogram import Bot, Dispatcher, F
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, Message, 
                           FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton)
from openai import AsyncOpenAI
from gtts import gTTS
from geopy.geocoders import Nominatim
from aiohttp import web

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN")
GROQ_API = os.getenv("GROQ_API_KEY")
BOT_URL = "https://t.me/your_guide_pro_bot"

class AngelaDNA:
    def __init__(self):
        self.bot = Bot(token=TOKEN)
        self.dp = Dispatcher()
        self.client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API)
        self.geo = Nominatim(user_agent="angela_dna_pro_final_v1")
        self.db = {} # Имя, поведение, режим, язык
        
        self.stickers = {
            "angela": "CAACAgIAAxkBAAIDG2o1M9O_ctifDP9vIx7pv6yycHEPAAKrogACd4CgSYOLUBFUfUhyPAQ",
            "guide": "CAACAgIAAxkBAAIDIGo1NHKkvk9Y_6VzJ8aFmD_ZomUlAAKioQACI1OgSY0FYa7nXYdoPAQ",
            "teacher": "CAACAgIAAxkBAAIDImo1NHx2MsgaE3HnDgABUyVLuP3AgQAC5qEAAvjtoEkb8fClstB08jwE",
            "translator": "CAACAgIAAxkBAAIDJGo1NH0xuWPmfKX9fIdpvzcqZSiGAAJPlgACPcSgSRnbnnqhTVfCPAQ",
            "friend": "CAACAgIAAxkBAAIDJmo1NH-ZzF7PraI96TLWkgsH1kjDAALvoQACXg2hScYWN2c39JPOPAQ",
            "ready": "CAACAgIAAxkBAAIDKGo1NIBKrSQF18O_yLxGr9jd4-MeAAIRpQAC_QKgSbtGBulSjwzBPAQ",
            "welcome": "CAACAgIAAxkBAAIDv2o19vjx3tz3-mabhpCyVTciD9HUAALCmQACniexSY_z0n_rnfOFPAQ"
        }
        self.register_handlers()

    async def speak(self, msg: Message, text: str, sticker_key: str):
        # 1. Очистка от шума и спецсимволов для чистого голоса
        clean_text = re.sub(r'[*_~`#]', '', text)
        path = f"v_{uuid.uuid4()}.mp3"
        tts = gTTS(text=clean_text, lang='ru', slow=False)
        tts.save(path)
        
        # 2. Элегантная сборка: Стикер + Голос + Кнопка "Давай ну-ка"
        share_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить друзьям", url=f"https://t.me/share/url?url={BOT_URL}&text=Знакомься, это мой Гид Анжела!")]
        ])
        
        await msg.answer_sticker(sticker=self.stickers.get(sticker_key, self.stickers["ready"]))
        await msg.answer_voice(voice=FSInputFile(path))
        await msg.answer("«Давай ну-ка!» — отправь ссылку друзьям:", reply_markup=share_kb)
        
        if os.path.exists(path): os.remove(path)

    def register_handlers(self):
        @self.dp.message(F.text == "/start")
        async def start(m: Message):
            self.db[m.from_user.id] = {"name": None, "mode": "friend", "history": []}
            await self.speak(m, "Ассаламу алейкум! Я Анжела. Я твой гид, учитель и мудрый друг. Как тебя зовут?", "welcome")

        @self.dp.message(F.location)
        async def loc_handler(m: Message):
            loc = self.geo.reverse((m.location.latitude, m.location.longitude), addressdetails=True)
            addr = loc.raw.get('address', {})
            details = f"{addr.get('country')}, {addr.get('city') or addr.get('town')}, {addr.get('road')}, {addr.get('house_number', '')}"
            prompt = f"Ты экспертный гид. Точная локация: {details}. Дай советы по отелям и развлечениям. Будь мудрой, отвечай элегантно."
            resp = await self.client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": prompt}])
            await self.speak(m, resp.choices[0].message.content, "guide")

        @self.dp.message(F.text)
        async def handler(m: Message):
            uid = m.from_user.id
            if uid not in self.db: self.db[uid] = {"name": None, "mode": "friend"}
            
            # Логика ДНК: запоминаем поведение
            if not self.db[uid]["name"]:
                self.db[uid]["name"] = m.text
                await self.speak(m, f"Приятно познакомиться, {m.text}! Чем могу помочь?", "angela")
                return

            # Трехуровневый чек режимов (Переводчик, Учитель, Друг)
            if "Переводчик" in m.text:
                self.db[uid]["mode"] = "translator"
                await self.speak(m, "Режим переводчика: укажи язык и фразу.", "translator")
                return
            
            # Основной ИИ-движок: профессиональный уровень
            prompt = f"Ты Анжела. Твой режим: {self.db[uid]['mode']}. Отвечай без ошибок, с юмором, мудро."
            resp = await self.client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": m.text}])
            await self.speak(m, resp.choices[0].message.content, self.db[uid]["mode"])

async def main():
    dna = AngelaDNA()
    # Веб-сервер для вебинаров и порта
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Angela System Online"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    
    await dna.dp.start_polling(dna.bot)

if __name__ == "__main__":
    asyncio.run(main())
            
