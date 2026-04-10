import logging
import asyncio
import base64
import aiohttp
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, ContentType
from aiohttp import web

# --- SIZNING MA'LUMOTLARINGIZ ---
API_TOKEN = '8305734962:AAGFTI29uR8EI2jbgjWMIIM6x2MnrKImBNw'
STABILITY_KEY = 'sk-CJfzKSl4fHK3wV4lW3x8VRFyW3ZMXNpj5dgnojWB6He5vOac'
ADMIN_ID = 580105818

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
user_data = {}

# Render uchun veb-server
async def handle(request):
    return web.Response(text="Bot 998 credits mode is Active!")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Salom! Bot qayta sozlandi. Rasm yuboring, so'ng prompt yozing.")

@dp.message(F.photo)
async def handle_photo(message: Message):
    # Eng yuqori sifatli rasm IDsini olish
    user_data[message.from_user.id] = {'photo_id': message.photo[-1].file_id}
    await message.answer("Rasm qabul qilindi! Endi inglizcha prompt yozing.")

@dp.message(F.text)
async def handle_prompt(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Avval rasm yuboring!")
        return

    prompt = message.text
    photo_id = user_data[user_id]['photo_id']
    await message.answer("AI ishlamoqda, kuting...")

    # 1. Telegramdan rasmni yuklab olish
    file = await bot.get_file(photo_id)
    file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    
    # 2. Stability AI API so'rovi (Soddalashtirilgan va barqaror model)
    # Modelni 'stable-diffusion-v1-6' ga o'zgartirdim (u kamroq kredit yeydi va barqaror)
    url = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/image-to-image"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {STABILITY_KEY}"
    }

    async with aiohttp.ClientSession() as session:
        # Rasmni yuklab olish
        async with session.get(file_url) as resp:
            image_bytes = await resp.read()

        # Ma'lumotlarni yuborish
        data = aiohttp.FormData()
        data.add_field("init_image", image_bytes, filename="input.png")
        data.add_field("text_prompts[0][text]", prompt)
        data.add_field("text_prompts[0][weight]", "1.0")
        data.add_field("image_strength", "0.4")
        data.add_field("cfg_scale", "7")
        data.add_field("steps", "30")

        async with session.post(url, headers=headers, data=data) as response:
            if response.status == 200:
                result = await response.json()
                img_base64 = result["artifacts"][0]["base64"]
                final_image = base64.b64decode(img_base64)
                
                await message.answer_photo(
                    photo=BufferedInputFile(final_image, filename="result.png"),
                    caption="Tayyor!"
                )
                del user_data[user_id]
            else:
                # Xatolikni aniq matnini chiqarish
                error_data = await response.json()
                error_message = error_data.get('message', 'Noma’lum xato')
                await message.answer(f"AI Xatolik: {error_message}")
                logging.error(f"Full Error: {error_data}")

async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await asyncio.gather(site.start(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
