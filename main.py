import logging
import asyncio
import base64
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

# --- SOZLAMALAR ---
# @BotFather dan olgan tokeningizni qo'ying
API_TOKEN = '8305734962:AAGFTI29uR8EI2jbgjWMIIM6x2MnrKImBNw' 
# DreamStudio dan olgan API keyni qo'ying
STABILITY_KEY = 'sk-CJfzKSl4fHK3wV4lW3x8VRFyW3ZMXNpj5dgnojWB6He5vOac'
# O'zingizning ID raqamingizni yozing
ADMIN_ID = 580105818 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
user_photos = {}

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Salom! Rasm yuboring, keyin inglizcha prompt yozing (Masalan: hyper-realistic portrait).")

@dp.message(F.photo)
async def handle_photo(message: Message):
    user_photos[message.from_user.id] = message.photo[-1].file_id
    await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Rasm qabul qilindi! Endi prompt yozing.")

@dp.message(F.text)
async def handle_prompt(message: Message):
    user_id = message.from_user.id
    if user_id not in user_photos:
        await message.answer("Avval rasm yuboring!")
        return

    prompt = message.text
    await message.answer("AI ishlamoqda, kuting...")

    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_KEY}"
    }
    body = {
        "text_prompts": [{"text": f"{prompt}, photorealistic, 8k, ultra-detailed", "weight": 1}],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as response:
            if response.status == 200:
                data = await response.json()
                image_bytes = base64.b64decode(data["artifacts"][0]["base64"])
                photo_file = BufferedInputFile(image_bytes, filename="ai_result.png")
                await message.answer_photo(photo=photo_file, caption="Natija tayyor!")
            else:
                await message.answer("Xatolik: API kalit yoki serverda muammo.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
