import logging
import asyncio
import aiohttp
import os
import io
import replicate
from PIL import Image
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiohttp import web

# --- KONFIGURATSIYA (Render Environment Variables'dan oladi) ---
API_TOKEN       = os.environ.get("API_TOKEN") # Render'da qo'shishni unutmang
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
ADMIN_ID        = 580105818 # O'zingizning ID'ingizni qoldiring

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def handle(request):
    return web.Response(text="Bot muvaffaqiyatli ishlayapti! ✅")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "<b>Salom! AI Rasm Botga xush kelibsiz!</b> 👋\n\n"
        "1️⃣ Avval rasm yuboring.\n"
        "2️⃣ Keyin o'sha rasmga <b>Reply</b> qilib xohlagan uslubingizni yozing.\n"
        "<i>Masalan: cyberpunk style, anime, oil painting</i>",
        parse_mode="HTML"
    )

@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.reply("✅ Rasm qabul qilindi! Endi unga <b>Reply</b> qilib prompt yozing.")

@dp.message(F.text)
async def handle_prompt(message: Message):
    # Faqat reply qilingan va rasm bor xabarlarni tekshirish
    if not message.reply_to_message or not message.reply_to_message.photo:
        return

    prompt = message.text.strip()
    photo_id = message.reply_to_message.photo[-1].file_id
    wait_msg = await message.answer("⏳ AI rasm tayyorlamoqda, kuting...")

    try:
        # 1. Rasmni yuklab olish
        file = await bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                image_bytes = await resp.read()

        # 2. Rasmni optimallashtirish
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)

        # 3. Replicate orqali generatsiya
        # Flux-dev modeli image-to-image uchun 'image' parametrini ishlatadi
        output = await asyncio.to_thread(
            replicate.run,
            "black-forest-labs/flux-dev",
            input={
                "prompt": prompt,
                "image": buf,
                "prompt_strength": 0.8,
                "num_outputs": 1,
                "guidance_scale": 7.5
            }
        )

        image_url = str(output[0]) if isinstance(output, list) else str(output)

        # 4. Natijani yuborish
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                result_bytes = await resp.read()

        await message.answer_photo(
            photo=BufferedInputFile(result_bytes, filename="result.jpg"),
            caption=f"✨ <b>Natija:</b> {prompt}",
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Xatolik: {e}")
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
    logging.info(f"Server {port}-portda ishga tushdi")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
