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

# --- KONFIGURATSIYA ---
API_TOKEN       = "8305734962:AAGFTI29uR8EI2jbgjWMIIM6x2MnrKImBNw"
REPLICATE_TOKEN = "r8_Kgev4Gwe538Ii1d3lIxPZq5h4gsUu9I17ztmt"
ADMIN_ID        = 580105818

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_TOKEN

bot = Bot(token=API_TOKEN)
dp  = Dispatcher()

async def handle(request):
    return web.Response(text="Bot ishlayapti ✅")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Salom! 👋\n\n"
        "1️⃣ Rasm yuboring\n"
        "2️⃣ Rasmga <b>reply</b> qilib prompt yozing\n"
        "3️⃣ AI yangi rasm yaratadi ✨",
        parse_mode="HTML"
    )

@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.reply(
        "✅ Rasm qabul qilindi!\n"
        "Endi shu rasmga <b>reply</b> qilib prompt yozing.\n\n"
        "Masalan: <i>anime style, oil painting, cyberpunk</i>",
        parse_mode="HTML"
    )

@dp.message(F.text)
async def handle_prompt(message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.answer(
            "⚠️ Avval rasm yuboring, so'ng unga <b>reply</b> qilib prompt yozing.",
            parse_mode="HTML"
        )
        return

    prompt   = message.text.strip()
    photo_id = message.reply_to_message.photo[-1].file_id
    wait_msg = await message.answer("⏳ AI rasm yaratmoqda, kuting...")

    try:
        file     = await bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                image_bytes = await resp.read()

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        output = await asyncio.to_thread(
            replicate.run,
            "black-forest-labs/flux-schnell",
            input={
                "prompt":         prompt,
                "image":          buf,
                "strength":       0.75,
                "num_outputs":    1,
                "aspect_ratio":   "1:1",
                "output_format":  "png",
                "output_quality": 100,
            }
        )

        image_url = str(output[0]) if isinstance(output, list) else str(output)

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                result_bytes = await resp.read()

        await message.answer_photo(
            photo=BufferedInputFile(result_bytes, filename="result.png"),
            caption="✨ Mana yangi rasm!"
        )

        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=BufferedInputFile(result_bytes, filename="admin.png"),
            caption=(
                f"✅ Yangi generatsiya\n"
                f"👤 {message.from_user.full_name}\n"
                f"🆔 {message.from_user.id}\n"
                f"📝 {prompt}"
            )
        )

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("❌ Xatolik yuz berdi, qayta urinib ko'ring.")
        await bot.send_message(ADMIN_ID, f"❌ Xato: {str(e)[:500]}")

    finally:
        try:
            await bot.delete_message(message.chat.id, wait_msg.message_id)
        except:
            pass

async def main():
    logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)

    await asyncio.gather(
        site.start(),
        dp.start_polling(bot, drop_pending_updates=True)
    )

if __name__ == "__main__":
    asyncio.run(main())
