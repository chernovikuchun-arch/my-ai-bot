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

# Render server uchun (Live holatini ushlab turish)
async def handle(request):
    return web.Response(text="Bot 100% Stable Mode is Active!")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Salom! Men tayyorman. \n\n1. Rasm yuboring.\n2. Rasmga **javob (reply)** sifatida prompt yozing.")

@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.reply("Rasm qabul qilindi! Endi ushbu rasmga **javob (REPLY)** sifatida inglizcha prompt yozing.")

@dp.message(F.text)
async def handle_prompt(message: Message):
    # Agar foydalanuvchi rasmga reply qilmagan bo'lsa, xatoni oldini olamiz
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.answer("Iltimos, avval rasm yuboring va unga **javob (reply)** sifatida prompt yozing.")
        return

    prompt = message.text
    photo_id = message.reply_to_message.photo[-1].file_id
    await message.answer("AI chizmoqda, bir oz kuting...")

    try:
        # 1. Telegramdan rasmni olish
        file = await bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status != 200:
                    await message.answer("Rasmni yuklab olishda xato bo'ldi.")
                    return
                image_bytes = await resp.read()

            # 2. O'lchamni SDXL uchun ideal (1024x1024) holatga keltirish
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = img.resize((1024, 1024))
            
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='PNG')
            final_bytes = byte_arr.getvalue()

            # 3. Stability AI API so'rovi
            url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image"
            headers = {"Accept": "application/json", "Authorization": f"Bearer {STABILITY_KEY}"}
            
            data = aiohttp.FormData()
            data.add_field("init_image", final_bytes, filename="img.png", content_type="image/png")
            data.add_field("text_prompts[0][text]", prompt)
            data.add_field("image_strength", "0.45") # Originalga o'xshashlik darajasi
            data.add_field("cfg_scale", "8")
            data.add_field("steps", "30")

            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 200:
                    res_json = await response.json()
                    img_base64 = res_json["artifacts"][0]["base64"]
                    result_img = base64.b64decode(img_base64)
                    
                    # Foydalanuvchiga yuborish
                    await message.answer_photo(photo=BufferedInputFile(result_img, filename="result.png"), caption="Tayyor! ✅")
                    
                    # Adminga (Sizga) xabar yuborish
                    admin_caption = f"👤 {message.from_user.full_name}\n📝 Prompt: {prompt}"
                    await bot.send_photo(chat_id=ADMIN_ID, photo=BufferedInputFile(result_img, filename="adm.png"), caption=admin_caption)
                else:
                    err_data = await response.text()
                    await message.answer(f"AI Xatolik: {response.status}")
                    await bot.send_message(ADMIN_ID, f"❌ Xato: {err_data[:500]}")

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("Tizimda xatolik yuz berdi.")

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
