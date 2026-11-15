"""
SINOV -- Jarvis OS 1-bosqich, band 1 (Telegram->xodim murojaati).

jarvis_fon.py (asosiy jarayon)ni RESTART qilmasdan, yangi kodni imkon
qadar to'liq sinash uchun: alohida `telegram.Bot` obyekti orqali (bir xil
TOKEN, lekin polling'ga aralashmaydi -- faqat chiquvchi xabar yuboradi)
jarvis_xodim_telegram.py'dagi funksiyalarni real ishlatib ko'radi.

Sinaladigan holatlar:
  1) yo'naltirish (Samandarga zaxira savoli -> Sardorga boradi)
  2) "ma'lumot yo'q" (Malikaga kofe savoli)
  3) to'g'ridan-to'g'ri o'qish (Bekzodga "hamma ishlayaptimi?")
  4) tasdiq talab qiladigan (SINOV_ prefiksli) -- tugma ko'rinishini
     ko'rsatish uchun xabar yuboriladi, keyin DARHOL bekor_qilish bilan
     tozalanadi (haqiqiy bajarish yo'q).
"""
import asyncio
import io
import sys

sys.path.insert(0, r"C:\Users\Dell\jarvis")

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup  # noqa: E402
from config import TELEGRAM_TOKEN, OWNER_ID  # noqa: E402
import jarvis_xodim_telegram as jxt  # noqa: E402


async def yubor_xodim_javobi(bot: Bot, xodim_id: str, ekran: str, ovoz: str | None = None, markup=None):
    ism = jxt.xodim_nomi(xodim_id)
    matn = f"[SINOV] {ism}:\n{ekran}"
    portret = jxt.portret_yoli(xodim_id)
    if portret and len(matn) <= 1024:
        with open(portret, "rb") as f:
            await bot.send_photo(OWNER_ID, photo=f, caption=matn, reply_markup=markup)
    else:
        if portret:
            with open(portret, "rb") as f:
                await bot.send_photo(OWNER_ID, photo=f)
        await bot.send_message(OWNER_ID, matn, reply_markup=markup)
    mp3 = jxt.bridge_speak_mp3(xodim_id, ovoz or ekran)
    if mp3:
        ogg = jxt.mp3_ni_ogg_ga_otkaz(mp3)
        if ogg:
            await bot.send_voice(OWNER_ID, voice=io.BytesIO(ogg))
    return True


async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    natijalar = {}

    await bot.send_message(OWNER_ID, "[SINOV] === Band 1 sinovi boshlandi (4 holat) ===")

    # 1) yo'naltirish
    d1 = jxt.bridge_savol("samandar", "SINOV_ zaxira nusxa holati qanday?")
    print("1 turi:", d1.get("turi"))
    await yubor_xodim_javobi(bot, "samandar", d1.get("ekran", ""), d1.get("javob"))
    yon = d1.get("yonaltirilgan") or {}
    if yon.get("xodim"):
        await yubor_xodim_javobi(bot, yon["xodim"], yon.get("ekran", ""), yon.get("ovoz"))
    natijalar["yonaltirish"] = d1.get("turi") == "yonaltirildi"

    # 2) ma'lumot yo'q
    d2 = jxt.bridge_savol("malika", "SINOV_ bugun qancha kofe sotildi?")
    print("2 turi:", d2.get("turi"))
    await yubor_xodim_javobi(bot, "malika", d2.get("ekran", ""), d2.get("javob"))
    natijalar["malumot_yoq"] = d2.get("turi") == "malumot_yoq"

    # 3) to'g'ridan-to'g'ri o'qish
    d3 = jxt.bridge_savol("bekzod", "SINOV_ hamma ishlayaptimi?")
    print("3 turi:", d3.get("turi"))
    await yubor_xodim_javobi(bot, "bekzod", d3.get("ekran", ""), d3.get("javob"))
    natijalar["oqish"] = d3.get("turi") == "oqish"

    # 4) tasdiq talab qiladigan -- tugmalar ko'rinishini ko'rsatish, DARHOL tozalash
    d4 = jxt.bridge_savol("samandar", "SINOV_ Orzu ota-onalariga eslatma yubor")
    print("4 turi:", d4.get("turi"), "id:", d4.get("id"))
    task_id = d4.get("id")
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"tasdiq:{task_id}"),
        InlineKeyboardButton("❌ Bekor", callback_data=f"bekor:{task_id}"),
    ]]) if task_id else None
    await yubor_xodim_javobi(bot, "samandar", d4.get("ekran", "") + "\n\n(bu SINOV -- avtomatik bekor qilinadi)", d4.get("javob"), markup=markup)
    natijalar["yozish"] = d4.get("turi") == "yozish"
    if task_id:
        bekor = jxt.bridge_bekor_qilish(task_id)
        print("bekor natija:", bekor)
        natijalar["yozish_tozalandi"] = bekor.get("holat") == "bekor_qilindi"

    await bot.send_message(OWNER_ID, f"[SINOV] === Band 1 sinovi tugadi. Natija: {natijalar} ===")
    print("NATIJALAR:", natijalar)
    print("HAMMASI OK:", all(natijalar.values()))


asyncio.run(main())
