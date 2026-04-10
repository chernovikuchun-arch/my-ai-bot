import logging
import asyncio
import base64
import aiohttp
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, ContentType
from aiohttp import web

# --- MA'LUMOTLAR ---
API_TOKEN = '8305734962:AAGFTI29uR8EI2jbgjWMIIM6x2MnrKImBNw'
STABILITY_KEY = 'sk-CJfzKSl4fHK3wV4lW3x8VRFyW3ZMXNpj5dgnojWB6He5vOac'
ADMIN_ID = 580105818

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
user_data = {}

async def handle(request):
    return web.Response(text="Bot is running with 1000 credits!")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Salom! Sizda 1000 ga yaqin kredit bor! 😎\n\n1. Rasm yuboring.\n2. Uni qanday o'zgartirishni yozing.")

@dp.message(F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message):
    user_data[message.from_user.id] = {'photo_id': message.photo[-1].file_id}
    await message.answer("Rasm qabul qilindi. Endi prompt yozing (masalan: 'cyberpunk style').")

@dp.message(F.text)
async def handle_prompt(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Avval rasm yuboring!")
        return

    prompt = message.text
    photo_id = user_data[user_id]['photo_id']
    await message.answer("AI ishlamoqda, bir oz kuting...")

    # Telegramdan rasmni olish
    file = await bot.get_file(photo_id)
    file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    
    # Stability AI API (Image-to-Image) - Engine ID ni yangiladim
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {STABILITY_KEY}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            image_bytes = await resp.read()

        data = aiohttp.FormData()
        data.add_field("init_image", image_bytes, filename="img.png", content_type="image/png")
        data.add_field("text_prompts[0][text]", f"{prompt}, highly detailed, 8k")
        data.add_field("image_strength", "0.4") # Rasmni o'zgarish darajasi
        data.add_field("cfg_scale", "7")
        data.add_field("steps", "30")

        async with session.post(url, headers=headers, data=data) as response:
            if response.status == 200:
                res = await response.json()
                img_data = base64.b64decode(res["artifacts"][0]["base64"])
                await message.answer_photo(photo=BufferedInputFile(img_data, filename="res.png"), caption="Tayyor!")
                del user_data[user_id]
            else:
                err = await response.text()
                await message.answer(f"Xatolik yuz berdi. Balans: 998 kredit.")
                logging.error(f"Error: {err}")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await asyncio.gather(site.start(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
