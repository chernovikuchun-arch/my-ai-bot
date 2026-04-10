import logging
import asyncio
import base64
import aiohttp
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiohttp import web

# --- SIZNING MA'LUMOTLARINGIZ ---
API_TOKEN = '8305734962:AAGFTI29uR8EI2jbgjWMIIM6x2MnrKImBNw'
STABILITY_KEY = 'sk-CJfzKSl4fHK3wV4lW3x8VRFyW3ZMXNpj5dgnojWB6He5vOac'
ADMIN_ID = 580105818

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
user_data = {}

# Render o'chirib qo'ymasligi uchun veb-server qismi
async def handle(request):
    return web.Response(text="AI Image-to-Image Bot is Active!")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Salom! Men rasmlarni o'zgartiruvchi AI botman.\n\n1. Menga rasm yuboring.\n2. Keyin uni qanday o'zgartirishni inglizcha promptda yozing.")

@dp.message(F.photo)
async def handle_photo(message: Message):
    # Eng sifatli rasm IDsini saqlash
    photo_id = message.photo[-1].file_id
    user_data[message.from_user.id] = {'photo_id': photo_id}
    
    # Adminga (sizga) nusxasini yuborish
    await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Rasm qabul qilindi! Endi unga nima qo'shish yoki o'zgartirishni yozing (masalan: 'cyberpunk style, neon lights').")

@dp.message(F.text)
async def handle_prompt(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Avval rasm yuboring!")
        return

    prompt = message.text
    photo_id = user_data[user_id]['photo_id']
    await message.answer("AI rasmni qayta ishlamoqda, kuting...")

    # 1. Telegramdan rasmni yuklab olish
    file = await bot.get_file(photo_id)
    file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    
    # 2. Stability AI API (Image-to-Image)
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {STABILITY_KEY}"
    }

    async with aiohttp.ClientSession() as session:
        # Rasmni yuklab olish
        async with session.get(file_url) as resp:
            if resp.status != 200:
                await message.answer("Xatolik: Rasmni yuklashda muammo bo'ldi.")
                return
            image_bytes = await resp.read()

        # AI ga yuborish uchun ma'lumotlarni tayyorlash
        data = aiohttp.FormData()
        data.add_field("init_image", image_bytes, filename="input.png", content_type="image/png")
        data.add_field("text_prompts[0][text]", f"{prompt}, high resolution, 8k, realistic")
        data.add_field("text_prompts[0][weight]", "1")
        data.add_field("image_strength", "0.35") # 0 dan 1 gacha. Qanchalik past bo'lsa, shunchalik ko'p o'zgaradi
        data.add_field("cfg_scale", "7")
        data.add_field("samples", "1")
        data.add_field("steps", "30")

        async with session.post(url, headers=headers, data=data) as response:
            if response.status == 200:
                result = await response.json()
                image_base64 = result["artifacts"][0]["base64"]
                final_image = base64.b64decode(image_base64)
                
                output = BufferedInputFile(final_image, filename="result.png")
                await message.answer_photo(photo=output, caption="Natija tayyor!")
                del user_data[user_id] # Xotirani tozalash
            else:
                error_msg = await response.text()
                await message.answer("Xatolik: AI bilan bog'lanishda muammo. Kredit tugagan bo'lishi mumkin.")
                logging.error(f"AI Error: {error_msg}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Render uchun port sozlamalari
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    
    await asyncio.gather(site.start(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
