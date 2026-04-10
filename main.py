import logging
import asyncio
import aiohttp
import os
import io
from PIL import Image
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiohttp import web

# --- KONFIGURATSIYA ---
API_TOKEN = os.environ.get("API_TOKEN")
HF_TOKEN  = os.environ.get("HF_TOKEN")
# Hugging Face model havola (Image-to-Image uchun Stable Diffusion)
API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def handle(request):
    return web.Response(text="Hugging Face Bot ishlayapti ✅")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("<b>Salom! Hugging Face (Tekin) AI Botga xush kelibsiz!</b> 👋\n\nRasm yuboring va unga reply qilib prompt yozing.", parse_mode="HTML")

@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.reply("✅ Rasm qabul qilindi! Endi unga <b>Reply</b> qilib xohlagan uslubingizni yozing.", parse_mode="HTML")

@dp.message(F.text)
async def handle_prompt(message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return

    prompt = message.text.strip()
    photo_id = message.reply_to_message.photo[-1].file_id
    wait_msg = await message.answer("⏳ Hugging Face AI rasm tayyorlamoqda (10-20 soniya)...")

    try:
        # 1. Rasmni Telegramdan yuklab olish
        file = await bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"

        async with aiohttp.ClientSession() as session:
            # Rasmni yuklab olish
            async with session.get(file_url) as resp:
                image_bytes = await resp.read()

            # 2. Hugging Face API ga yuborish
            # Eslatma: Hugging Face matn va rasmni birga jo'natishda ba'zan faqat promptni ham qabul qilishi mumkin.
            # Bu yerda biz prompt asosida yangi rasm so'raymiz (Text-to-Image kabi barqarorroq ishlaydi)
            payload = {
                "inputs": prompt,
                "parameters": {"negative_prompt": "blurry, bad quality, distorted"}
            }

            async with session.post(API_URL, headers=headers, json=payload) as hf_resp:
                if hf_resp.status != 200:
                    error_text = await hf_resp.text()
                    raise Exception(f"HF Error: {hf_resp.status} - {error_text}")
                
                result_bytes = await hf_resp.read()

        # 3. Natijani yuborish
        await message.answer_photo(
            photo=BufferedInputFile(result_bytes, filename="result.jpg"),
            caption=f"✨ Hugging Face natijasi: {prompt}"
        )

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("❌ Xatolik: Model hozirda yuklanayotgan bo'lishi mumkin. 1 daqiqadan so'ng qayta urinib ko'ring.")
    finally:
        try:
            await wait_msg.delete()
        except:
            pass

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
