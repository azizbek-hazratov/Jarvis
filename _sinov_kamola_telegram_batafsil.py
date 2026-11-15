"""SINOV -- 2026-09-28 kechqurun, Kamola/Instagram voqeasidan keyingi
tuzatishni Telegram tomonida tasdiqlash uchun bir martalik skript.

jarvis_fon.py (asosiy jarayon)ni qayta ishga tushirmasdan, ALOHIDA
`telegram.Bot` obyekti orqali (bir xil TOKEN, polling'ga aralashmaydi)
jarvis_telegram.py'dagi HAQIQIY `_xodim_javobini_yubor()` funksiyasini
chaqiradi -- xuddi mavjud `_sinov_xodim_telegram.py` naqshi kabi.

Sinaladigan narsa: Kamolaga "instagramda ahvol qanday tekshir" deb
so'ralganda (aynan bugungi voqeadagi savol) endi Telegramga QISQA
("Azizbek aka, ...") xabar + (agar batafsil bo'lsa) "📄 Batafsil" tugmasi
bilan kelishi, UZUN texnik matn ENDI caption'da emasligi."""
import asyncio
import sys

sys.path.insert(0, r"C:\Users\Dell\jarvis")

from telegram import Bot  # noqa: E402
from config import TELEGRAM_TOKEN, OWNER_ID  # noqa: E402
import jarvis_xodim_telegram as jxt  # noqa: E402
import jarvis_telegram as jt  # noqa: E402


class _SoxtaContext:
    """jarvis_telegram._xodim_javobini_yubor faqat `context.bot`dan
    foydalanadi -- shuning uchun to'liq Application o'rniga shu yengil
    o'ram yetarli."""

    def __init__(self, bot):
        self.bot = bot


async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    ctx = _SoxtaContext(bot)

    await bot.send_message(OWNER_ID, "[SINOV] === Kamola/Instagram tuzatish sinovi boshlandi ===")

    matn = "instagramda ahvol qanday tekshir"
    print(f"Bridge'ga so'rov: kamola -> {matn!r}")
    data = jxt.bridge_savol("kamola", matn)
    print("turi:", data.get("turi"))
    print("javob (QISQA bo'lishi kerak):", data.get("javob"))
    print("batafsil bormi:", bool(data.get("batafsil")))

    caption_uzunligi = len(data.get("javob") or "")
    print(f"caption uzunligi: {caption_uzunligi} belgi (qisqa uslub uchun ~300dan kam bo'lishi kutiladi)")

    await jt._xodim_javobini_yubor(
        OWNER_ID, ctx, "kamola",
        data.get("javob", ""),
        batafsil_matn=data.get("batafsil"),
    )

    await bot.send_message(
        OWNER_ID,
        "[SINOV] === Tugadi. Yuqoridagi Kamola xabari QISQA ('Azizbek aka...') bo'lishi, "
        "texnik so'z (API/token/Buffer) BO'LMASLIGI kerak. Agar '📄 Batafsil' tugmasi "
        "ko'rinsa -- bosilganda to'liq matn alohida xabar sifatida kelishi kerak. ===",
    )
    print("SINOV TUGADI.")


asyncio.run(main())
