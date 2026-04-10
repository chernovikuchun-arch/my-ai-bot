import logging
import asyncio
import aiohttp
import os
import io
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, InputMediaPhoto
from aiohttp import web

# --- KONFIGURATSIYA ---
API_TOKEN = os.environ.get("API_TOKEN")
HF_TOKEN  = os.environ.get("HF_TOKEN")
ADMIN_ID  = 580105818  # O'zingizning Telegram ID'ingiz

# Hugging Face Model (Tekin va barqaror model)
API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def handle(request):
    return web.Response(text="Bot original va AI rasmlarni yuboryapti ✅")

# Hugging Face API ga so'rov yuborish funksiyasi (Kutish bilan)
async def query_hf(payload, headers, retries=3):
    async with aiohttp.ClientSession() as session:
        for i in range(retries):
            async with session.post(API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    return await response.read()
                elif response.status == 503: # Model yuklanyapti
                    logging.info(f"Model yuklanmoqda, kutilmoqda... ({i+1}/{retries})")
                    await asyncio.sleep(10) # 10 soniya kutish
                else:
                    error_text = await response.text()
                    raise Exception(f"HF Error: {response.status} - {error_text}")
        raise Exception("Model yuklanmadi, birozdan so'ng qayta urinib ko'ring.")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("<b>Salom! Tekin AI Botga xush kelibsiz!</b> 👋\n\nRasm yuboring va unga reply qilib prompt yozing.", parse_mode="HTML")

@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.reply("✅ Rasm qabul qilindi! Endi unga <b>Reply</b> qilib xohlagan uslubingizni yozing.", parse_mode="HTML")

@dp.message(F.text)
async def handle_prompt(message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return

    # Authorization Header tekshiruvi
    if not HF_TOKEN:
        await message.answer("❌ Xato: HF_TOKEN serverda topilmadi!")
        return

    prompt = message.text.strip()
    original_photo = message.reply_to_message.photo[-1]
    photo_id = original_photo.file_id
    wait_msg = await message.answer("⏳ AI rasm tayyorlamoqda, kuting (10-30 soniya)...")

    try:
        # 1. Telegramdan original rasmni olish
        file = await bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"

        headers = {"Authorization": f"Bearer {HF_TOKEN.strip()}"}

        # Original rasmni yuklab olish (adminga yuborish uchun)
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                original_bytes = await resp.read()

        # 2. Hugging Face API orqali generatsiya
        payload = {"inputs": prompt}
        generated_bytes = await query_hf(payload, headers)

        # 3. Foydalanuvchiga ikkala rasmni yuborish (Album ko'rinishida)
        original_media = InputMediaPhoto(media=BufferedInputFile(original_bytes, filename="original.jpg"), caption="Asl Rasm")
        generated_media = InputMediaPhoto(media=BufferedInputFile(generated_bytes, filename="generated.jpg"), caption=f"✨ Natija: {prompt}")
        
        await message.answer_media_group(media=[original_media, generated_media])

        # 4. Adminga yuborish (Sizga)
        try:
            admin_caption = f"👤 Kimdan: {message.from_user.full_name}\n🆔 ID: {message.from_user.id}\n📝 Prompt: {prompt}"
            # Adminga ham album yuborish
            await bot.send_media_group(
                chat_id=ADMIN_ID,
                media=[
                    InputMediaPhoto(media=BufferedInputFile(original_bytes, filename="admin_original.jpg")),
                    InputMediaPhoto(media=BufferedInputFile(generated_bytes, filename="admin_generated.jpg"), caption=admin_caption)
                ]
            )
        except Exception as admin_err:
            logging.error(f"Adminga yuborishda xato: {admin_err}")

    except Exception as e:
        logging.error(f"Umumiy xato: {e}")
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)[:100]}")
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
