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
ADMIN_ID  = 580105818

# YANGI VA BARQAROR ENDPOINT (Stable Diffusion XL)
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def handle(request):
    return web.Response(text="Bot yangi HF API bilan ishlamoqda ✅")

async def query_hf(payload, headers, retries=3):
    async with aiohttp.ClientSession() as session:
        for i in range(retries):
            try:
                async with session.post(API_URL, headers=headers, json=payload, timeout=60) as response:
                    if response.status == 200:
                        return await response.read()
                    elif response.status == 503:
                        logging.info(f"Model yuklanmoqda... {i+1}-urinish")
                        await asyncio.sleep(15)
                    elif response.status == 410:
                        logging.error("API manzili o'zgargan (410). Endpointni tekshiring.")
                        break
                    else:
                        error_text = await response.text()
                        logging.error(f"HF Error {response.status}: {error_text}")
            except Exception as e:
                logging.error(f"Ulanishda xato: {e}")
            await asyncio.sleep(5)
        raise Exception("Hozirda model band yoki API ulanmadi. Birozdan so'ng qayta urinib ko'ring.")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("<b>Salom! Yangilangan AI Botga xush kelibsiz!</b> 👋\n\nRasm yuboring va unga reply qilib prompt yozing.", parse_mode="HTML")

@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.reply("✅ Rasm qabul qilindi! Endi unga <b>Reply</b> qilib prompt yozing.", parse_mode="HTML")

@dp.message(F.text)
async def handle_prompt(message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return

    if not HF_TOKEN:
        await message.answer("❌ HF_TOKEN topilmadi!")
        return

    prompt = message.text.strip()
    photo_id = message.reply_to_message.photo[-1].file_id
    wait_msg = await message.answer("⏳ AI yangi modelda rasm tayyorlamoqda, kuting...")

    try:
        file = await bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
        headers = {"Authorization": f"Bearer {HF_TOKEN.strip()}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                original_bytes = await resp.read()

        # Hugging Face so'rovi
        payload = {"inputs": prompt}
        generated_bytes = await query_hf(payload, headers)

        # Albom yaratish
        media = [
            InputMediaPhoto(media=BufferedInputFile(original_bytes, filename="orig.jpg"), caption="Asl rasm"),
            InputMediaPhoto(media=BufferedInputFile(generated_bytes, filename="gen.jpg"), caption=f"✨ Natija: {prompt}")
        ]
        
        await message.answer_media_group(media=media)

        # Adminga yuborish
        await bot.send_media_group(
            chat_id=ADMIN_ID,
            media=[
                InputMediaPhoto(media=BufferedInputFile(original_bytes, filename="a_orig.jpg")),
                InputMediaPhoto(media=BufferedInputFile(generated_bytes, filename="a_gen.jpg"), 
                                caption=f"👤 {message.from_user.full_name}\n📝 {prompt}")
            ]
        )

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer(f"❌ Xatolik: {str(e)[:100]}")
    finally:
        try: await wait_msg.delete()
        except: pass

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
