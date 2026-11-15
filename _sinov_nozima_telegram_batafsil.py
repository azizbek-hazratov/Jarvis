"""SINOV qo'shimcha -- Nozima'ning qarzdorlar ro'yxati javobi HAR DOIM
"batafsil" (to'liq ro'yxat) bilan qaytadi -- shuning uchun bu bilan
Telegramdagi "📄 Batafsil" tugmasi HAQIQATDA ko'rinishini tasdiqlaymiz."""
import asyncio
import sys

sys.path.insert(0, r"C:\Users\Dell\jarvis")

from telegram import Bot
from config import TELEGRAM_TOKEN, OWNER_ID
import jarvis_xodim_telegram as jxt
import jarvis_telegram as jt


class _SoxtaContext:
    def __init__(self, bot):
        self.bot = bot


async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    ctx = _SoxtaContext(bot)
    data = jxt.bridge_savol("nozima", "Orzu akademyda kim to'lamagan?")
    print("javob:", data.get("javob")[:150])
    print("batafsil bormi:", bool(data.get("batafsil")))
    await jt._xodim_javobini_yubor(
        OWNER_ID, ctx, "nozima",
        data.get("javob", ""),
        batafsil_matn=data.get("batafsil"),
    )
    print("YUBORILDI — Telegramda '📄 Batafsil' tugmasi ko'rinishi kerak.")


asyncio.run(main())
