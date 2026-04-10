import logging
import asyncio
import base64
import aiohttp
import os
import io
from PIL import Image
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, ContentType
from aiohttp import web

# --- KONFIGURATSIYA ---
API_TOKEN = '8305734962:AAGFTI29uR8EI2jbgjWMIIM6x2MnrKImBNw'
STABILITY_KEY = 'sk-CJfzKSl4fHK3wV4lW3x8VRFyW3ZMXNpj5dgnojWB6He5vOac'
ADMIN_ID = 580105818

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
user_data = {}

async def handle(request):
    return web.Response(text="Bot Admin & Error Fix Mode Active!")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Salom! Rasm yuboring, so'ng prompt yozing. Admin nazorati yoqilgan.")

@dp.message(F.photo)
async def handle_photo(message: Message):
    user_data[message.from_user.id] = {'photo_id': message.photo[-1].file_id}
    await message.answer("Rasm qabul qilindi. Endi prompt yozing.")

@dp.message(F.text)
async def handle_prompt(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Avval rasm yuboring!")
        return

    prompt = message.text
    photo_id = user_data[user_id]['photo_id']
    await message.answer("AI ishlamoqda...")

    file = await bot.get_file(photo_id)
    file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            image_bytes = await resp.read()

        # O'lchamni 1024x1024 ga majburlash (SDXL uchun qat'iy talab)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((1024, 1024))
        
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='PNG')
        resized_bytes = byte_arr.getvalue()

        data = aiohttp.FormData()
        data.add_field("init_image", resized_bytes, filename="img.png", content_type="image/png")
        data.add_field("text_prompts[0][text]", prompt)
        data.add_field("image_strength", "0.4")
        data.add_field("cfg_scale", "7")
        data.add_field("steps", "30")

        headers = {"Accept": "application/json", "Authorization": f"Bearer {STABILITY_KEY}"}

        async with session.post(url, headers=headers, data=data) as response:
            if response.status == 200:
                res = await response.json()
                img_data = base64.b64decode(res["artifacts"][0]["base64"])
                
                # Foydalanuvchiga yuborish
                await message.answer_photo(photo=BufferedInputFile(img_data, filename="res.png"), caption="Tayyor!")
                
                # Adminga yuborish (Sizga)
                admin_msg = f"👤 {message.from_user.full_name}\n🆔 {user_id}\n📝 {prompt}"
                await bot.send_photo(chat_id=ADMIN_ID, photo=BufferedInputFile(img_data, filename="adm.png"), caption=admin_msg)
                
                del user_data[user_id]
            else:
                # Xatolikni to'liq ko'rish uchun logga chiqaramiz
                error_json = await response.json()
                error_text = error_json.get('message', str(error_json))
                await message.answer(f"AI Xatosi: {error_text}")
                # Adminga xatoni ham yuboramiz
                await bot.send_message(ADMIN_ID, f"❌ Xatolik yuz berdi:\nUser: {user_id}\nError: {error_text}")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await asyncio.gather(site.start(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
