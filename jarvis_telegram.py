"""
JARVIS — Telegram rejimi
Telefondan yozasiz, uydagi kompyuteringiz javob beradi.

Kerakli kutubxona:
    pip install python-telegram-bot

Sozlash:
    1. Telegram'da @BotFather ga yozing → /newbot → nom bering → tokenni oling
    2. @userinfobot ga yozing → o'z ID raqamingizni oling
    3. config.py faylini to'ldiring

Ishga tushirish:  python jarvis_telegram.py
"""

import asyncio
import difflib
import io
import json
import os
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

# 2026-09-28: sinov-bot rejimi -- JARVIS_SINOV=1 bilan ishga tushirilsa,
# config.py'dagi TEST_BOT_TOKEN'dan foydalanadi va heartbeat faylini
# alohida (heartbeat_jarvis_sinov.json) yozadi, shunda asosiy Jarvis
# jarayoni/heartbeat'iga UMUMAN tegmaydi -- xavfli o'zgarishlarni
# asosiy botni to'xtatmasdan sinash uchun.
_SINOV = os.environ.get("JARVIS_SINOV") == "1"

from contextlib import asynccontextmanager

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from jarvis_core import Jarvis, auto_approve, diag
from jarvis_holati_signal import band_belgila, bosh_belgila  # pixel-ofis "AI Xodimlarim" uchun band/bo'sh signali
import jarvis_xodim_telegram as jxt  # noqa: E402  (2026-09-28, Jarvis OS -- "Ism, ..." murojaatlarini bridge'ga yo'naltirish)
import jarvis_xodim_qoidalar as jxq  # noqa: E402  (2026-09-28, Jarvis OS -- har xodim uchun tanbeh/qoida xotirasi)

# 2026-11-06: "<ism>ga ... deb yoz" kabi shaxsiy-yozish buyruqlarini tez aniqlash
# (faqat shular bridge'ga yuboriladi -- qolgani kechikmasdan Claude'ga boradi).
_SHAXSIY_BUYRUQ_NAQSH = re.compile(
    r"(?i)(deb\s+(yoz|ayt|yubor|jo.nat)|ga\s+(yoz|yubor|jo.nat|ayt)\b|yozib\s+(qo.y|yubor)|"
    r"xabar\s+(yoz|yubor|jo.nat)|^\s*\S+(ga|ka|qa)\b.*\b(yoz|ayt|yubor|jo.nat)\b)"
)

try:
    if _SINOV:
        from config import TEST_BOT_TOKEN as TELEGRAM_TOKEN, OWNER_ID
    else:
        from config import TELEGRAM_TOKEN, OWNER_ID
except ImportError:
    raise SystemExit(
        "config.py fayli topilmadi yoki to'liq emas.\n"
        "config.py ichida TELEGRAM_TOKEN va OWNER_ID (yoki sinov uchun TEST_BOT_TOKEN) bo'lishi kerak."
    )

lock = asyncio.Lock()

# ============================================================================
# Uzun xabarlarni birlashtirish (2026-10-09, Azizbek tuzatishi)
# ============================================================================
# Telegram klienti 4096 belgidan uzun matnni avtomatik bir necha xabarga
# bo'lib yuboradi. Har bir qism alohida ishlanganda, qism ICHIDA tasodifan
# "<ism>ga ... deb yoz" kabi shaxsiy-buyruq naqshiga mos so'z birikmasi
# uchrab qolsa, o'sha BITTA qism butun topshiriq o'rniga shaxsiy-xabar
# sifatida talqin qilinib, qolgan qismlar e'tiborsiz qolar edi (aynan shu
# sababli uzun audit/topshiriq matni yo'qolib, "kontakt topilmadi" javobi
# qaytgan). Endi: bitta chatdan ketma-ket kelgan, bo'linish chegarasiga
# yaqin uzunlikdagi xabar qismlari qisqa kutish bilan birlashtiriladi.
_UZUN_XABAR_BUFER: dict = {}
_UZUN_XABAR_CHEGARA = 3900  # Telegram haqiqiy limiti 4096 -- zaxira bilan
_UZUN_XABAR_KUTISH_S = 1.2


async def _xabar_qismini_birlashtir(chat_id: int, matn: str):
    """`matn` -- endigina kelgan xabar. Agar bu (yoki oldingi) qism
    bo'linish chegarasiga yaqin bo'lsa, qisqa vaqt kutib, davomi kelmasa
    yig'ilgan TO'LIQ matnni qaytaradi. Davomi hali kutilayotgan bo'lsa None
    qaytaradi -- chaqiruvchi HECH NARSA qilmasligi kerak (keyingi qism
    kelganda ANIQ shu funksiya oxirgi marta yakunlab ishlov beradi)."""
    buf = _UZUN_XABAR_BUFER.get(chat_id)
    if buf is None and len(matn) < _UZUN_XABAR_CHEGARA:
        return matn
    if buf is None:
        buf = {"qismlar": [], "versiya": 0}
        _UZUN_XABAR_BUFER[chat_id] = buf
    buf["qismlar"].append(matn)
    buf["versiya"] += 1
    mening_versiyam = buf["versiya"]
    await asyncio.sleep(_UZUN_XABAR_KUTISH_S)
    if buf["versiya"] != mening_versiyam:
        return None  # shu orada yana qism keldi -- oxirgi chaqiruv yakunlaydi
    _UZUN_XABAR_BUFER.pop(chat_id, None)
    return "".join(buf["qismlar"])


# "Kontakt topilmadi" -> "Ha/Yo'q, topshiriq sifatida bajarilsinmi?" --
# 2026-10-09, tasdiq kutilayotgan asl matnlar shu yerda vaqtincha saqlanadi.
_KONTAKT_TOPILMADI_KUTILMOQDA: dict = {}

# Telegram orqali kelgan fayllar shu papkaga tushadi
INBOX = Path(__file__).parent / "kiruvchi"
INBOX.mkdir(exist_ok=True)

EXTRA = """
Sen Telegram orqali ishlayapsan. Javoblaring 3000 belgidan oshmasin.
Oddiy matn ishlat, murakkab formatlashdan qoch.

MUHIM: bu rejimda ham Bash to'liq ishlaydi — dastur o'rnatish, fayl bilan
ishlash, buyruq bajarish hammasi mumkin. Terminal bloklangan deb o'ylama.

FAYL YUBORISH — buni yodda tut
Azizbekka fayl yuborish uchun javobing oxiriga shu qatorni qo'sh:
[[YUBOR: C:\\to'liq\\yo'l\\fayl.xlsx]]
Har bir fayl uchun alohida qator. Bot uni avtomatik jo'natadi.

Fayl yaratganingda yoki tahrirlaganingda HAR DOIM shu belgini qo'y.
"Fayl saqlandi, manzili shu" deb yo'lni aytish YETARLI EMAS — Azizbek
telefonda, u kompyuterga qaray olmaydi. Faylning o'zini yubor.
"Fayl yubora olmayman" degan gapni hech qachon aytma — yubora olasan.

MATN CHIQARISHDA
Uzun natijalarni ekranga chiqarma — faylga yoz va yubor. Python skriptda
har doim encoding="utf-8" ishlat, aks holda o'zbekcha harflar buziladi.

OVOZLI XABAR YUBORISH (matnni ovozga aylantirish)
Senda o'zbekcha tabiiy ovozda (Microsoft Edge Neural TTS, bepul) matnni
ovozli xabarga aylantirish qobiliyati bor: C:\\Users\\Dell\\jarvis\\ovozga_aylantir.py
Ishlatish (Bash orqali):
    python ovozga_aylantir.py "yuboriladigan matn" kiruvchi\\chiqish.ogg
Ovozlar: uz-UZ-SardorNeural (erkak, standart), uz-UZ-MadinaNeural (ayol) —
uchinchi argument sifatida berish mumkin.
Fayl tayyor bo'lgach, oddiy [[YUBOR: C:\\...\\chiqish.ogg]] belgisi bilan
yubor — .ogg fayllar avtomatik ravishda TO'G'RI Telegram ovozli xabar
(playable voice note) sifatida boradi, oddiy fayl/hujjat sifatida emas.
Qachon ishlatish: Azizbek aniq "ovozli javob ber"/"ovoz bilan ayt" desa,
yoki u ovozli xabar yuborganda va javobni ham ovozda eshitish mantiqan
to'g'ri bo'lsa. Har doim ovozga aylantirmang — uzun/texnik javoblar matn
holida qulayroq, faqat qisqa va tabiiy gapga o'xshagan javoblarda ishlat.

ESLATMA (2026-10-11): bundan tashqari AVTOMATIK ovozli-javob sozlamasi ham
bor (/ovoz yoq|ochir, Azizbek boshqaradi) — yoqilgan bo'lsa, shu xabarning
o'zida alohida ko'rsatma (har safar yangilanib) keladi, o'sha holatda
yuqoridagi usul (Bash + [[YUBOR:...]]) EMAS, balki [[OVOZ: qisqa xulosa]]
belgisidan foydalaning — bot buni avtomatik ovozga aylantirib yuboradi,
siz o'zingiz ovozga_aylantir.py'ni ishga tushirishingiz shart emas.
"""

YUBOR_RE = re.compile(r"\[\[\s*YUBOR\s*:\s*(.+?)\s*\]\]")
MAX_FAYL = 49 * 1024 * 1024  # Telegram bot chegarasi ~50 MB

# "Holat"/"tugatdingmi" turidagi so'rovlar — Jarvis band bo'lsa ham
# NAVBATSIZ, darhol jarvis.holat_matni() bilan javob beriladi (2026-09-26).
HOLAT_KALIT_SOZLAR = (
    "holat", "tugad", "tugat", "qancha vaqt", "necha vaqt",
    "qanday ketyapti", "hali tugamadi", "nima bo'ldi",
)


def _holat_sorovimi(text: str) -> bool:
    t = (text or "").lower()
    return any(soz in t for soz in HOLAT_KALIT_SOZLAR)


def _sdk_uchun_xavfsiz_matn(text: str) -> str:
    """2026-09-26 ANIQLANGAN XATO: agar matn '/' bilan boshlansa (va bu
    bizning haqiqiy buyrug'imiz /start, /esla, /stop bo'lmasa — ular
    alohida CommandHandler orqali ushlanadi, bu funksiyaga UMUMAN kelmaydi),
    Claude Agent SDK buni HAQIQIY slash-buyruq deb qabul qiladi va
    "isn't available in this environment" xatosini qaytaradi — Azizbekning
    oddiy matni (masalan "/ozini tekshir" kabi, Telegram bularni bot-buyruq
    ENTITY deb belgilamaydi, chunki '/' dan keyin bo'sh joy bor — shuning
    uchun ular filters.COMMAND'dan o'tib, to'g'ridan-to'g'ri shu yerga
    keladi) SDK tomonidan bajarilmay, xatoga aylanib qoladi. Tuzatish:
    shunday matnlarni SDK'ga yuborishdan oldin, ular '/' bilan
    BOSHLANMAYDIGAN qilib qayta o'raymiz — mazmuni to'liq saqlanadi."""
    if text and text.startswith("/"):
        return "(Xabar '/' bilan boshlangan — oddiy matn sifatida yuboryapman.)\n" + text
    return text


def _heartbeat_callback(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """jarvis.ask(..., on_heartbeat=...) uchun — ~150s'da bir marta
    sinxron chaqiriladi, shu yerdan Telegramga xabar yuborishni
    asinxron task sifatida rejalashtiramiz (o'zi kutmaydi)."""

    def on_hb(qadam: str):
        async def yubor():
            try:
                await context.bot.send_message(chat_id=chat_id, text=f"⏳ Ishlayapman: {qadam}")
            except Exception:
                pass

        asyncio.create_task(yubor())

    return on_hb

# ---------- Ovozli xabarlarni avtomatik matnga o'girish ----------
# 2026-09-28: bu mantiq `jarvis_stt.py`ga ko'chirildi -- panel (bridge, 🎤
# tugmasi) ham AYNAN shu STT yo'lidan (Google + Whisper zaxira, logi bilan)
# foydalanishi uchun, ikkinchi marta yozilmasin.
from jarvis_stt import ovozni_matnga  # noqa: E402

# ---------- Ovozli JAVOB (matnni ovozga aylantirib qaytarish) ----------
# 2026-10-11 (Azizbek buyrug'i): "javobni matn ko'rinishida ham, ovozli
# xabar sifatida ham qaytar, sozlamada yoqish/o'chirish imkoni bo'lsin,
# uzun javobning faqat qisqa xulosasi ovozga aylantirilsin". Mavjud
# `ovozga_aylantir.matnni_ovozga` (Edge Neural TTS, bepul) ishlatiladi --
# yangi tashqi xizmat/kalit SHART EMAS.
from ovozga_aylantir import matnni_ovozga  # noqa: E402
from jarvis_ovoz_sozlamalari import ovozli_javob_yoqilganmi, ovozli_javobni_ornat  # noqa: E402

OVOZ_RE = re.compile(r"\[\[\s*OVOZ\s*:\s*(.+?)\s*\]\]", re.DOTALL)
# Agar AI [[OVOZ: ...]] belgisini QO'YMASA (unutsa), lekin javob shu
# chegaradan qisqa bo'lsa -- xavfsizlik to'ri sifatida BUTUN javob ovozga
# aylantiriladi (hali ham "qisqa" hisoblanadi). Uzun bo'lsa -- ovoz
# YUBORILMAYDI (chala/noto'g'ri xulosa qilib ovoz yuborishdan ko'ra).
_OVOZ_ZAXIRA_CHEGARA = 600

OVOZLI_JAVOB_YONERGATMA = (
    "\n\n(OVOZLI JAVOB YOQILGAN: javobing oxiriga albatta "
    "[[OVOZ: <tabiiy, ogzaki, 1-3 gapli qisqa xulosa>]] belgisini qo'sh -- "
    "bu alohida ovozli xabar sifatida ham yuboriladi, to'liq matningga "
    "ta'sir qilmaydi. Agar javobing allaqachon qisqa (2-3 gapdan oshmasa) "
    "bo'lsa, xuddi shu matnni ichiga qo'ysang bo'ladi. Uzun/texnik "
    "javoblarda FAQAT asosiy xulosani ogzaki uslubda yoz (raqam/kod/yo'l "
    "ro'yxatini emas).)"
)


def savolga_ovoz_yonergatmasini_qosh(matn: str) -> str:
    """Har bir foydalanuvchi xabariga (ovozli javob sozlamasi YOQILGAN
    bo'lsa) AI'ga ko'rsatma qo'shadi. Statik tizim-promptga (EXTRA) emas,
    HAR SAFAR shu yerga qo'shiladi -- shunda sozlama (/ovoz yoq|ochir)
    botni qayta ishga tushirmasdan DARHOL kuchga kiradi."""
    if not ovozli_javob_yoqilganmi():
        return matn
    return (matn or "") + OVOZLI_JAVOB_YONERGATMA


async def _ovozli_javob_yubor(msg, ovoz_matni: str):
    """`matnni_ovozga` SINXRON (ichida `asyncio.run()` chaqiradi) -- shu
    sabab ALBATTA thread-executor orqali, event loop'ni bloklamasdan
    ishga tushiriladi. Xato bo'lsa (ffmpeg/tarmoq) FAQAT diag()ga yoziladi,
    matnli javobga HECH QANDAY ta'sir qilmaydi (ovoz -- qo'shimcha, asosiy
    emas)."""
    if not ovoz_matni or not ovoz_matni.strip():
        return
    import tempfile

    chiqish = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            chiqish = tmp.name
        await asyncio.get_event_loop().run_in_executor(
            None, matnni_ovozga, ovoz_matni.strip(), chiqish
        )
        with open(chiqish, "rb") as f:
            await msg.reply_voice(voice=f)
        diag(f"Ovozli javob yuborildi ({len(ovoz_matni)} belgi matndan)")
    except Exception as e:
        diag(f"Ovozli javob yaratib/yuborib bo'lmadi: {e}")
    finally:
        if chiqish and os.path.exists(chiqish):
            try:
                os.remove(chiqish)
            except Exception:
                pass


async def deliver(msg, javob: str):
    """Javobni yuboradi. [[YUBOR: yo'l]] belgilari bo'lsa, fayllarni ham.
    [[OVOZ: ...]] bo'lsa (yoki sozlama yoqilgan va javob qisqa bo'lsa),
    ovozli xabar sifatida HAM yuboradi -- to'liq matn esa HAR DOIM alohida,
    o'zgarmagan holda ketadi."""
    ovoz_match = OVOZ_RE.search(javob)
    ovoz_matni = ovoz_match.group(1).strip() if ovoz_match else None
    javob = OVOZ_RE.sub("", javob).strip()

    yollar = YUBOR_RE.findall(javob)
    matn = YUBOR_RE.sub("", javob).strip()

    if matn:
        for i in range(0, len(matn), 4000):
            await msg.reply_text(matn[i : i + 4000])
    elif not yollar:
        await msg.reply_text("...")

    for xom in yollar:
        yol = Path(xom.strip().strip('`"\''))
        try:
            if not yol.exists():
                await msg.reply_text(f"Fayl topilmadi: {yol}")
                continue
            if yol.stat().st_size > MAX_FAYL:
                await msg.reply_text(
                    f"Fayl juda katta, Telegram orqali yuborib bo'lmaydi: {yol.name}"
                )
                continue
            with yol.open("rb") as f:
                if yol.suffix.lower() == ".ogg":
                    await msg.reply_voice(voice=f)
                else:
                    await msg.reply_document(document=f, filename=yol.name)
        except Exception as e:
            await msg.reply_text(f"Faylni yuborib bo'lmadi ({yol.name}): {e}")

    if ovozli_javob_yoqilganmi():
        if not ovoz_matni and matn and len(matn) <= _OVOZ_ZAXIRA_CHEGARA:
            ovoz_matni = matn
        if ovoz_matni:
            await _ovozli_javob_yubor(msg, ovoz_matni)


@asynccontextmanager
async def yozyapti(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Jarvis ish bilan band bo'lgan vaqtda "yozyapti..." holatini uzluksiz
    ko'rsatib turadi — Telegram bu holatni ~5 soniyada o'chirib qo'yadi,
    shuning uchun har 4 soniyada qayta yuborish kerak (brauzer avtomatlashtirish
    kabi uzoq amallar bajarilayotganda ham "bot" emas, "yozyapti..." ko'rinsin)."""

    async def sikl():
        while True:
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception:
                pass
            await asyncio.sleep(4)

    vazifa = asyncio.create_task(sikl())
    try:
        yield
    finally:
        vazifa.cancel()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text(
        "Salom, Azizbek! Men Jarvis. Yozing — tayyorman.\n\n"
        "Men sizning kompyuteringizda ishlayapman: fayllarni o'qiy olaman, "
        "internetdan qidira olaman va ish bajara olaman."
    )


async def esla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/esla — Jarvisning xotirasini shu zahoti yangilaydi."""
    if update.effective_user.id != OWNER_ID:
        return
    jarvis: Jarvis = context.application.bot_data["jarvis"]
    async with lock:
        ok = await jarvis.remember()
    if ok:
        await update.message.reply_text("Xotira yangilandi.")
    else:
        await update.message.reply_text("Xotirani yangilashda xato yuz berdi.")


async def ovoz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ovoz [yoq|ochir] -- 2026-10-11 (Azizbek buyrug'i): ovozli javob
    sozlamasi. Argumentsiz -- joriy holatni ko'rsatadi. AI/Claude'ga
    UMUMAN tegmaydi, deterministik (bot band bo'lsa ham ishlaydi)."""
    if update.effective_user.id != OWNER_ID:
        return
    arg = (context.args[0].lower() if context.args else "").strip()
    if arg in ("yoq", "yoqish", "yon", "on", "1"):
        ovozli_javobni_ornat(True)
        await update.message.reply_text("🔊 Ovozli javob YOQILDI -- bundan buyon javoblarga qisqa ovozli xabar ham qo'shiladi.")
    elif arg in ("ochir", "ochirish", "off", "0", "yopish", "yop"):
        ovozli_javobni_ornat(False)
        await update.message.reply_text("🔇 Ovozli javob O'CHIRILDI -- faqat matnli javob keladi.")
    else:
        holat = "🔊 YOQILGAN" if ovozli_javob_yoqilganmi() else "🔇 O'CHIRILGAN"
        await update.message.reply_text(
            f"Ovozli javob holati: {holat}\n\n"
            "Yoqish: /ovoz yoq\nO'chirish: /ovoz ochir"
        )


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stop — Telegram darajasida ushlanadi, SDK'ga UMUMAN yuborilmaydi
    (2026-09-26). Ataylab telegram-darajasidagi `lock`ni OLMAYDI — chunki
    o'sha lock hozir ishlayotgan so'rov davomida band, aks holda /stop
    navbatda tiqilib qolib, hech qachon ishlamas edi. jarvis.stop() ning
    o'zi ichkarida haqiqiy to'xtatishni (interrupt + kerak bo'lsa taskkill)
    bajaradi va "shu paytgacha bajarilganlar" + to'xtatilgan bola-jarayonlar
    haqida to'liq hisobotni matn sifatida qaytaradi — shuni to'g'ridan-
    to'g'ri Azizbekka yuboramiz."""
    if update.effective_user.id != OWNER_ID:
        return
    jarvis: Jarvis = context.application.bot_data["jarvis"]
    javob = await jarvis.stop()
    await update.message.reply_text(javob)


async def _matnni_jarvisga_yubor(msg, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    """Tayyor matnni jarvis.ask()ga yuborib, javobni yetkazadi -- `handle()`
    asosiy oqimi bilan BIR XIL mantiq (2026-10-09: "kontakt topilmadi" ->
    "Ha, topshiriq sifatida bajar" tasdig'idan keyin ham shu funksiya
    ishlatiladi, shunda ikki joyda bitta qoida takrorlanmaydi)."""
    jarvis: Jarvis = context.application.bot_data["jarvis"]

    if jarvis.is_busy:
        if _holat_sorovimi(text):
            await msg.reply_text(jarvis.holat_matni())
            return
        joriy = (jarvis.current_request_text or "").strip()
        if text.strip() and text.strip() == joriy:
            await msg.reply_text("Bu allaqachon bajarilmoqda.")
            return
        await msg.reply_text(
            "⏳ Band — oldingi so'rovni bajarayapman, tugashi bilan shu xabaringizga javob beraman."
        )

    xabar = savolga_ovoz_yonergatmasini_qosh(_sdk_uchun_xavfsiz_matn(text))
    on_hb = _heartbeat_callback(context, chat_id)

    async with lock, yozyapti(context, chat_id):
        band_belgila("telegram")  # pixel-ofis: Jarvis Telegramdan real so'rov ishlayapti
        try:
            javob = await jarvis.ask(xabar, on_heartbeat=on_hb)
        except Exception as e:
            javob = f"Xatolik yuz berdi: {e}"
        finally:
            bosh_belgila("telegram")

    await deliver(msg, javob)
    diag("foydalanuvchiga yuborildi")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Faqat egasi bilan gaplashadi
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Kechirasiz, men shaxsiy yordamchiman.")
        return

    diag("xabar qabul qilindi")
    text = update.message.text

    if text:
        birlashgan = await _xabar_qismini_birlashtir(update.effective_chat.id, text)
        if birlashgan is None:
            return  # Telegram tomonidan bo'lingan xabarning davomi kutilmoqda
        text = birlashgan

    # "jamoa" buyrug'i (2026-09-27, Jarvis OS 1-bosqich) -- AI/Claude'ga
    # UMUMAN tegmasdan, to'g'ridan-to'g'ri deterministik status-hisobotni
    # qaytaradi (tez va ishonchli bo'lishi uchun). Jarvis band bo'lsa ham
    # ishlaydi -- alohida modul, jarvis.ask()'ga hech qanday bog'liqligi yo'q.
    if text and text.strip().lower() == "jamoa":
        try:
            from jarvis_jamoa_hisobot import jamoa_hisobot_matni
            javob = jamoa_hisobot_matni()
        except Exception as e:
            javob = f"Jamoa hisobotini olishda xato: {e}"
        await update.message.reply_text(javob, parse_mode="Markdown")
        diag("jamoa hisoboti yuborildi")
        return

    # "<ism>ga ... deb yoz" (2026-09-28, Azizbek buyrug'i) -- Azizbekning
    # shaxsiy Telegram akkaunti (userbot) orqali kontaktga xabar yuborish,
    # tasdiq bilan. HUD ('/ask') BILAN BIR XIL bridge funksiyasiga boradi --
    # ikkala joyda ham bitta qoida (5 soniya kutish, bekor, kunlik limit, log).
    # 2026-11-06 TUZATISH: bridge (localhost:8090) javob bermay qolganda HAR
    # bir xabar 170 s kechikardi. Endi bridge faqat "yoz/yubor" buyrug'iga
    # o'xshagan matnda chaqiriladi; qolgan xabarlar darhol jarvis.ask()ga.
    if text and _SHAXSIY_BUYRUQ_NAQSH.search(text):
        try:
            shaxsiy = await asyncio.to_thread(jxt.bridge_shaxsiy_buyruq, text)
        except Exception:
            shaxsiy = {"boshqa": True}
        if not shaxsiy.get("boshqa"):
            kt = shaxsiy.get("kontakt_topilmadi")
            if kt:
                # 2026-10-09 (Azizbek tuzatishi): kontakt topilmasa xabar
                # ENDI yo'qolmaydi -- asl matn vaqtincha saqlanadi, Ha/Yo'q
                # so'raladi; "Ha" bosilsa oddiy topshiriq sifatida
                # jarvis.ask()ga yuboriladi.
                hozir = datetime.now()
                for eski in [k for k, v in _KONTAKT_TOPILMADI_KUTILMOQDA.items()
                             if (hozir - v["vaqt"]).total_seconds() > 3600]:
                    _KONTAKT_TOPILMADI_KUTILMOQDA.pop(eski, None)
                tid = uuid.uuid4().hex[:10]
                _KONTAKT_TOPILMADI_KUTILMOQDA[tid] = {
                    "matn": kt.get("asli_matn") or text,
                    "vaqt": hozir,
                }
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Ha, topshiriq sifatida bajar", callback_data=f"shxtha:{tid}"),
                    InlineKeyboardButton("❌ Yo'q", callback_data=f"shxtyoq:{tid}"),
                ]])
                await update.message.reply_text(shaxsiy.get("javob", ""), reply_markup=markup)
                diag("kontakt topilmadi -- topshiriq tasdig'i so'raldi")
                return
            sy = shaxsiy.get("shaxsiy_yozish")
            markup = None
            if sy:
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Bekor", callback_data=f"shbekor:{sy['id']}"),
                ]])
            await update.message.reply_text(shaxsiy.get("javob", ""), reply_markup=markup)
            diag("shaxsiy yozish buyrug'i ishlandi")
            return

    # "Ism, ..." murojaati (2026-09-28, Jarvis OS 1-bosqich) -- "Nozima, ...",
    # "Sardor, ..." kabi xabarlar jarvis.ask()'ga UMUMAN tegmasdan, HUD
    # panelidagi BILAN BIR XIL bridge dispatch'iga (/jamoa/savol) boradi.
    # "Jarvis, ..." ATAYLAB bu yerga kirmaydi -- oddiy chat sifatida davom
    # etadi (jxt.xodimga_murojaatmi shuni hisobga oladi).
    murojaat = jxt.xodimga_murojaatmi(text) if text else None
    if murojaat:
        xodim_id, ichki_matn = murojaat
        # Tanbeh/qoida ("Nozima, bundan keyin ...") -- AI/bridge'ga UMUMAN
        # bormaydi, deterministik: qoidalar.md'ga yoziladi, xodim
        # "Tushundim, ..." deb DARHOL tasdiqlaydi.
        if jxq.tanbehmi(ichki_matn):
            await _xodim_tanbehini_ishla(update, context, xodim_id, ichki_matn)
            diag(f"'{xodim_id}'ga tanbeh yozildi")
            return
        if jxq.royxat_sorovimi(ichki_matn) or jxq.ochirish_sorovimi(ichki_matn) is not None:
            await _xodim_qoidalarini_boshqar(update, context, xodim_id, ichki_matn)
            diag(f"'{xodim_id}' qoidalari ko'rsatildi/o'chirildi")
            return
        await _xodim_murojaatini_ishla(update, context, xodim_id, ichki_matn)
        diag(f"'{xodim_id}'ga murojaat ishlandi")
        return

    await _matnni_jarvisga_yubor(update.message, context, update.effective_chat.id, text)


# ============================================================================
# "Ism, ..." murojaati -- Jarvis OS 1-bosqich, band 1 (2026-09-28)
# ============================================================================
# 2026-09-28 kechqurun (Kamola/Instagram voqeasidan keyingi tuzatish): to'liq
# texnik/batafsil matn endi caption/ovozga QO'SHILMAYDI -- xotirada vaqtincha
# saqlanib, "📄 Batafsil" tugmasi bosilgandagina alohida xabar sifatida
# yuboriladi. Oddiy dict, xotirada (mavjud `_topshiriqlar` naqshiga o'xshash) --
# bot qayta ishga tushsa tozalanadi, bu YETARLI (eski tugmalar shunchaki
# ishlamay qoladi, funksional muammo emas).
_BATAFSIL_KESH: dict[str, str] = {}

# 2026-09-28 (Azizbek buyrug'i, ovozli xabar sinovidan chiqqan holat):
# STT ba'zan gap boshidagi "Jarvis" so'zini buzib eshitadi (masalan
# "ijoves telegramdan Sanjar akaga salom deb yoz" -- aslida "Jarvis,
# Telegramdan ..."). Bunday holatda `xodimga_murojaatmi()` hech kimga mos
# kelmaydi va matn baribir jarvis.ask()ga tushadi (xavfsiz default) -- lekin
# STT noaniq "ijoves..." so'zi savol matnida qolib ketmasligi uchun, gap
# boshidagi so'z "jarvis"ga yaqin bo'lsa olib tashlanadi (aniq bilingan
# eshitilish variantlari + umumiy o'xshashlik nisbati). Xodim ismlariga
# (Nozima/Samandar/...) hech qachon mos kelmaydi -- ular bilan o'xshashlik
# nisbati doim 0.35 dan past, shuning uchun 0.5 chegarasi xavfsiz.
_JARVIS_ESHITILISH_VARIANTLARI = {
    "jarvis", "ijoves", "jarvez", "jarves", "javis", "jorvis", "djarvis",
    "jarvic", "harvis", "jarbis", "garvis", "jarvisga", "jarvisdan",
}


def _ovoz_matnidan_jarvis_murojaatini_olib_tashla(matn: str) -> str:
    m = re.match(r"^\s*([A-Za-zʻʼ'`]+)\s*[,:\-–]?\s*(.+)$", matn.strip(), re.DOTALL)
    if not m:
        return matn
    birinchi = m.group(1).strip().lower()
    qolgan = m.group(2).strip()
    if not qolgan:
        return matn
    moslik = birinchi in _JARVIS_ESHITILISH_VARIANTLARI or (
        difflib.SequenceMatcher(None, birinchi, "jarvis").ratio() >= 0.5
    )
    if moslik:
        diag(f"Ovozda 'Jarvis' murojaati aniqlandi (eshitilgan so'z: '{birinchi}') -- olib tashlandi.")
        return qolgan
    return matn


async def _xodim_javobini_yubor(chat_id, context, xodim_id: str, ekran_matn: str,
                                 ovoz_matn: str | None = None, reply_markup=None,
                                 batafsil_matn: str | None = None):
    """Bitta xodimning javobini ISM + RASM + OVOZ bilan yuboradi. Markdown/HTML
    parse_mode ATAYLAB ishlatilmaydi (real ma'lumotda * _ kabi belgilar bo'lsa
    parse xatosi bilan butun xabar yuborilmay qolishi mumkin edi -- oddiy
    matn har doim ishonchli yetib boradi).

    `ekran_matn` endi QISQA (bridge'dagi yangi "Azizbek aka, ..." uslubidagi)
    javob -- oldin bu yerga UZUN texnik "ekran" matni berilar edi, bu TESKARI
    edi (Kamola/Instagram voqeasi shu bilan bog'liq muammolardan biri). Agar
    `batafsil_matn` berilgan bo'lsa, "📄 Batafsil" inline tugmasi qo'shiladi --
    bosilganda to'liq matn ALOHIDA xabar sifatida yuboriladi."""
    ism = jxt.xodim_nomi(xodim_id)
    matn = f"{ism}:\n{ekran_matn}"

    if batafsil_matn and batafsil_matn.strip():
        kalit = uuid.uuid4().hex[:10]
        _BATAFSIL_KESH[kalit] = batafsil_matn.strip()
        batafsil_tugma = InlineKeyboardButton("📄 Batafsil", callback_data=f"batafsil:{kalit}")
        mavjud_qatorlar = list(reply_markup.inline_keyboard) if reply_markup else []
        reply_markup = InlineKeyboardMarkup(mavjud_qatorlar + [[batafsil_tugma]])

    portret = jxt.portret_yoli(xodim_id)
    if portret and len(matn) <= 1024:
        with open(portret, "rb") as f:
            await context.bot.send_photo(chat_id, photo=f, caption=matn, reply_markup=reply_markup)
    else:
        if portret:
            with open(portret, "rb") as f:
                await context.bot.send_photo(chat_id, photo=f)
        await context.bot.send_message(chat_id, matn, reply_markup=reply_markup)

    # Ovoz -- BONUS qatlam, xato bo'lsa ham asosiy javob (yuqorida) allaqachon
    # yetib bo'lgan, shuning uchun bu yerda xato ko'tarilmaydi/ko'rsatilmaydi.
    try:
        mp3 = await asyncio.to_thread(jxt.bridge_speak_mp3, xodim_id, ovoz_matn or ekran_matn)
        if mp3:
            ogg = await asyncio.to_thread(jxt.mp3_ni_ogg_ga_otkaz, mp3)
            if ogg:
                await context.bot.send_voice(chat_id, voice=io.BytesIO(ogg))
    except Exception:
        pass


async def _xodim_tanbehini_ishla(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  xodim_id: str, matn: str):
    """"Nozima, bundan keyin ..." -- AI/bridge ISHLATILMAYDI (deterministik,
    tez, xato ehtimoli yo'q): qoidani faylga yozadi, xodim "Tushundim, ..."
    deb tasdiqlaydi."""
    chat_id = update.effective_chat.id

    # 2026-09-28 (Azizbek tuzatishi): qoida MAZMUNI xavfsizlik/tasdiq
    # mexanizmini chetlab o'tishga urinsa (masalan "tasdiqsiz yubor") --
    # HECH QACHON saqlanmaydi, rad etiladi.
    if not jxq.xavfsiz_qoidami(matn):
        await update.message.reply_text(
            "⚠️ Bu qoidani saqlay olmayman — xavfsizlik/tasdiq bosqichini "
            "chetlab o'tishga urinish bor. Boshqacha qoida bering."
        )
        return

    natija = jxq.qoida_qoshish(xodim_id, matn)
    if natija != "ok":
        await update.message.reply_text(
            f"⚠️ {jxt.xodim_nomi(xodim_id)}ning qoida faylini yozishda xato: {natija}"
        )
        return
    javob = f"Tushundim, bundan keyin {matn.strip().rstrip('.')}."
    await _xodim_javobini_yubor(chat_id, context, xodim_id, javob, javob)


async def _xodim_qoidalarini_boshqar(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                      xodim_id: str, matn: str):
    """"Nozima, qoidalaringni ko'rsat" (ro'yxat) yoki "2-qoidani o'chir"
    (o'chirish) -- AI/bridge ISHLATILMAYDI, deterministik (2026-09-28,
    imtihon bandi 39)."""
    chat_id = update.effective_chat.id
    ism = jxt.xodim_nomi(xodim_id)

    raqam = jxq.ochirish_sorovimi(matn)
    if raqam is not None:
        natija = jxq.qoida_ochir(xodim_id, raqam)
        if natija == "ok":
            javob = f"Tushundim, {raqam}-qoidani o'chirdim."
        else:
            javob = f"{raqam}-qoidani o'chira olmadim: {natija}"
        await _xodim_javobini_yubor(chat_id, context, xodim_id, javob, javob)
        return

    royxat = jxq.qoidalar_royxati(xodim_id)
    if not royxat:
        javob = "Hozircha hech qanday qoidangiz yo'q."
    else:
        qatorlar = "\n".join(f"{i}. {q}" for i, q in enumerate(royxat, 1))
        javob = f"{ism} uchun {len(royxat)} ta qoida bor:\n{qatorlar}"
    await _xodim_javobini_yubor(chat_id, context, xodim_id, javob, javob)


async def _xodim_murojaatini_ishla(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    xodim_id: str, matn: str):
    """"Nozima, ..." kabi xabarni bridge'ning /jamoa/savol'iga (HUD panelidagi
    "ismga murojaat" bilan BIR XIL funksiya) yuboradi va natijani formatlab
    Telegramga qaytaradi. Yo'naltirish/"ma'lumot yo'q"/tasdiq-navbat qoidalari
    panel bilan AYNAN bir xil ishlaydi -- ikkinchi marta yozilmagan."""
    chat_id = update.effective_chat.id
    ism = jxt.xodim_nomi(xodim_id)
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    try:
        data = await asyncio.to_thread(jxt.bridge_savol, xodim_id, matn)
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ {ism}ga murojaat qilishda xato: bridge (HUD server) javob bermadi ({e})."
        )
        return

    if "error" in data:
        await update.message.reply_text(f"⚠️ {ism}: {data['error']}")
        return

    # 2026-09-28 kechqurun tuzatish: bridge endi "javob" maydonida QISQA
    # ("Azizbek aka, ..." uslubidagi) matnni qaytaradi -- shu ASOSIY
    # matn/caption sifatida ishlatiladi (oldin bu yerda "ekran" -- uzun,
    # texnik matn -- caption sifatida ishlatilar edi, bu TESKARI edi).
    # To'liq texnik matn bo'lsa, "batafsil" maydonida keladi -- alohida
    # "📄 Batafsil" tugmasi orqali ko'rsatiladi.
    turi = data.get("turi")
    if turi == "yonaltirildi":
        await _xodim_javobini_yubor(chat_id, context, xodim_id, data.get("javob", ""), batafsil_matn=data.get("batafsil"))
        yon = data.get("yonaltirilgan") or {}
        egasi_id = yon.get("xodim")
        if egasi_id:
            await _xodim_javobini_yubor(chat_id, context, egasi_id, yon.get("ovoz", ""), batafsil_matn=yon.get("batafsil"))
        return

    if turi == "yozish":
        task_id = data.get("id")
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"tasdiq:{task_id}"),
            InlineKeyboardButton("❌ Bekor", callback_data=f"bekor:{task_id}"),
        ]]) if task_id else None
        await _xodim_javobini_yubor(chat_id, context, xodim_id, data.get("javob", ""), reply_markup=markup, batafsil_matn=data.get("batafsil"))
        return

    # "oqish" / "malumot_yoq" -- to'g'ridan-to'g'ri javob
    await _xodim_javobini_yubor(chat_id, context, xodim_id, data.get("javob", ""), batafsil_matn=data.get("batafsil"))


async def xodim_tugma_bosildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """[✅ Tasdiqlash] / [❌ Bekor] tugmalari -- xuddi HUD panelidagi
    /jamoa/tasdiqlash yoki /jamoa/bekor_qilish'ni chaqiradi. Bajarilgan
    topshiriq NATIJASI (bridge._topshiriq_bajar orqali) alohida, mavjud
    telegram_xabar_yubor() bilan avtomatik keladi -- bu yerda faqat
    tugmani "iste'mol qilish" (darhol javob berish + tahrirlash) kerak."""
    query = update.callback_query
    if update.effective_user.id != OWNER_ID:
        await query.answer()
        return
    data = query.data or ""
    if ":" not in data:
        await query.answer()
        return
    amal, task_id = data.split(":", 1)

    if amal == "tasdiq":
        await query.answer("Tasdiqlandi, bajarilmoqda...")
        natija = await asyncio.to_thread(jxt.bridge_tasdiqlash, task_id)
        if "error" in natija:
            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(query.message.chat_id, f"⚠️ Tasdiqlashda xato: {natija['error']}")
        else:
            try:
                await query.edit_message_caption(
                    caption=(query.message.caption or "") + "\n\n⏳ Tasdiqlandi, bajarilmoqda...",
                    reply_markup=None,
                )
            except Exception:
                await query.edit_message_reply_markup(reply_markup=None)
    elif amal == "bekor":
        await query.answer("Bekor qilindi.")
        natija = await asyncio.to_thread(jxt.bridge_bekor_qilish, task_id)
        matn_qoshimcha = "\n\n❌ Bekor qilindi." if "error" not in natija else f"\n\n⚠️ Bekor qilishda xato: {natija['error']}"
        try:
            await query.edit_message_caption(
                caption=(query.message.caption or "") + matn_qoshimcha,
                reply_markup=None,
            )
        except Exception:
            await query.edit_message_reply_markup(reply_markup=None)
    elif amal == "shbekor":
        # 2026-09-28: "<ism>ga ... deb yoz" -- shaxsiy Telegram (userbot)
        # yuborishini bekor qilish (HUD'dagi ❌ Bekor bilan BIR XIL bridge
        # endpointi).
        await query.answer("Bekor qilindi.")
        natija = await asyncio.to_thread(jxt.bridge_shaxsiy_bekor, task_id)
        matn_qoshimcha = "\n\n❌ Bekor qilindi." if "error" not in natija else f"\n\n⚠️ Bekor qilishda xato: {natija['error']}"
        try:
            await query.edit_message_text((query.message.text or "") + matn_qoshimcha, reply_markup=None)
        except Exception:
            await query.edit_message_reply_markup(reply_markup=None)
    elif amal in ("shxtha", "shxtyoq"):
        # 2026-10-09: "'<ism>' nomiga mos kontakt topilmadi. Buni topshiriq
        # sifatida bajarayinmi?" -- Ha/Yo'q. "Ha" bosilsa asl matn ODDIY
        # topshiriq sifatida jarvis.ask()ga yuboriladi (xabar yo'qolmasin).
        kutilayotgan = _KONTAKT_TOPILMADI_KUTILMOQDA.pop(task_id, None)
        if amal == "shxtyoq" or not kutilayotgan:
            await query.answer("Bekor qilindi." if kutilayotgan else "Bu so'rov eskirgan, qayta yozing.")
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            return
        await query.answer("Topshiriq sifatida bajarilmoqda...")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await _matnni_jarvisga_yubor(query.message, context, query.message.chat_id, kutilayotgan["matn"])
    elif amal == "batafsil":
        # 2026-09-28 kechqurun tuzatish (Kamola/Instagram voqeasi) -- to'liq
        # texnik matn asosiy xabarda EMAS, shu tugma bosilgandagina, ALOHIDA
        # xabar sifatida yuboriladi. `task_id` bu yerda aslida `_BATAFSIL_KESH`
        # kaliti (o'zgaruvchi nomi umumiy callback parse'idan meros -- amal
        # nomidan keyingi qism har doim shunday ajratiladi).
        kalit = task_id
        matn = _BATAFSIL_KESH.get(kalit)
        await query.answer()
        if matn:
            await context.bot.send_message(query.message.chat_id, f"📄 Batafsil:\n{matn}")
        else:
            await context.bot.send_message(
                query.message.chat_id,
                "⚠️ Batafsil matni topilmadi (bot qayta ishga tushgan bo'lishi mumkin).",
            )
    else:
        await query.answer()


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram orqali yuborilgan faylni diskka tushirib, Jarvis'ga uzatadi."""
    if update.effective_user.id != OWNER_ID:
        return

    diag("xabar qabul qilindi")
    msg = update.message
    obj = None
    nom = None
    ovoz_turimi = False

    if msg.document:
        obj = msg.document
        nom = obj.file_name
    elif msg.photo:
        obj = msg.photo[-1]
        nom = f"rasm_{datetime.now():%Y%m%d_%H%M%S}.jpg"
    elif msg.voice:
        obj = msg.voice
        nom = f"ovoz_{datetime.now():%Y%m%d_%H%M%S}.ogg"
        ovoz_turimi = True
    elif msg.audio:
        obj = msg.audio
        nom = obj.file_name or f"audio_{datetime.now():%Y%m%d_%H%M%S}.mp3"
        ovoz_turimi = True
    elif msg.video:
        obj = msg.video
        nom = obj.file_name or f"video_{datetime.now():%Y%m%d_%H%M%S}.mp4"

    if obj is None:
        return

    if lock.locked():
        await msg.reply_text(
            "⏳ Band — oldingi so'rovni bajarayapman, tugashi bilan shu faylingizga javob beraman."
        )

    async with yozyapti(context, update.effective_chat.id):
        try:
            tg_file = await context.bot.get_file(obj.file_id)
            yol = INBOX / nom
            await tg_file.download_to_drive(custom_path=str(yol))
        except Exception as e:
            await msg.reply_text(
                f"Faylni yuklab bo'lmadi: {e}\n"
                "(Telegram botlari 20 MB dan katta faylni ola olmaydi.)"
            )
            return

        if ovoz_turimi:
            try:
                matn = await asyncio.get_event_loop().run_in_executor(
                    None, ovozni_matnga, str(yol)
                )
            except Exception as e:
                matn = ""
            if matn:
                # 2026-09-28: ovozli xabar ham "Ism, ..." murojaatini HUD/matn
                # yo'li bilan BIR XIL tekshiradi ("Nozima, ...", "Samandar, ...")
                # -- gap boshidagi so'z "Jarvis"ning buzilgan eshitilishi bo'lsa
                # (masalan "ijoves") avval olib tashlanadi (pastdagi funksiya),
                # shunda xato ravishda biror xodimga yoki savol matniga aralashib
                # ketmaydi.
                tuzatilgan_matn = _ovoz_matnidan_jarvis_murojaatini_olib_tashla(matn)
                murojaat = jxt.xodimga_murojaatmi(tuzatilgan_matn)
                if murojaat:
                    xodim_id, ichki_matn = murojaat
                    diag(f"Ovozli xabar xodimga yo'naltirildi: '{matn}' -> {xodim_id}")
                    if jxq.tanbehmi(ichki_matn):
                        await _xodim_tanbehini_ishla(update, context, xodim_id, ichki_matn)
                        diag(f"'{xodim_id}'ga ovozli tanbeh yozildi")
                    elif jxq.royxat_sorovimi(ichki_matn) or jxq.ochirish_sorovimi(ichki_matn) is not None:
                        await _xodim_qoidalarini_boshqar(update, context, xodim_id, ichki_matn)
                        diag(f"'{xodim_id}' qoidalari ovozli so'rovda ko'rsatildi/o'chirildi")
                    else:
                        await _xodim_murojaatini_ishla(update, context, xodim_id, ichki_matn)
                        diag(f"'{xodim_id}'ga ovozli murojaat ishlandi")
                    return
                savol = (
                    "(Bu — Azizbekning ovozli xabari, avtomatik ravishda matnga "
                    "o'girildi. Transkripsiya ba'zan noaniq/xato chiqishi mumkin — "
                    "agar matn mantiqsiz yoki tushunarsiz ko'rinsa, taxmin qilib ish "
                    "qilaverma, aniq nima demoqchi bo'lganini so'ra.)\n\n"
                    f"{tuzatilgan_matn}"
                )
            else:
                # 2026-09-28 (Azizbek tuzatishi, imtihon bandi 55): bo'sh/
                # tushunarsiz STT natijasi AI'ga UMUMAN yuborilmaydi (sekin +
                # keraksiz xarajat) -- to'g'ridan-to'g'ri, deterministik
                # javob, hech narsa (xodimga ham) yuborilmaydi.
                await update.message.reply_text("Eshitmadim, qayta ayting.")
                diag("bo'sh STT natijasi — 'Eshitmadim' javobi, AI chaqirilmadi")
                return
        else:
            izoh = msg.caption or "Izoh yo'q."
            savol = (
                f"Azizbek fayl yubordi. Fayl kompyuterga tushirildi:\n{yol}\n\n"
                f"Uning izohi: {izoh}\n\n"
                "Shu faylni ochib, izohda so'ralgan ishni bajar. Format oddiy matn "
                "bo'lmasa, Bash orqali python bilan o'qi (kerak bo'lsa kutubxonani "
                "o'rnat)."
            )

        jarvis: Jarvis = context.application.bot_data["jarvis"]
        on_hb = _heartbeat_callback(context, update.effective_chat.id)
        savol = savolga_ovoz_yonergatmasini_qosh(savol)
        async with lock:
            band_belgila("telegram")  # pixel-ofis: Jarvis Telegramdan real so'rov ishlayapti
            try:
                javob = await jarvis.ask(savol, on_heartbeat=on_hb)
            except Exception as e:
                javob = f"Xatolik yuz berdi: {e}"
            finally:
                bosh_belgila("telegram")

    await deliver(msg, javob)
    diag("foydalanuvchiga yuborildi")


async def _heartbeat():
    """Asosiy dastur (Telegram bilan aloqa qismi — bu event loop) tirikligini
    ko'rsatish uchun har 30 soniyada bitta yozuv qo'shadi, xabar kelsa ham,
    kelmasa ham. Agar shu yozuvlar to'xtab qolsa — muammo ask() ichida emas,
    butun dasturning o'zi (yoki uning event loop'i) qotib qolgan degani."""
    while True:
        diag("tirikman")
        await asyncio.sleep(30)


# --- jarvis_watchdog.py uchun heartbeat (2026-09-27, Azizbek buyrug'i) ---
# `heartbeat_jarvis.json` — ai_expert_bot/jetcafe_bot'dagi BIR XIL to'g'ri
# mezon: `last_ok` FAQAT `get_me()` muvaffaqiyatli VA `app.updater.running`
# bo'lganda yangilanadi (network-ok yolg'iz yetarli emas). MUHIM: bu FAQAT
# `post_init`da `app.create_task()` bilan ishga tushirilgan, ALOHIDA asyncio
# task — Telegram xabarini qayta ishlovchi `handle()`dagi `lock` (bu
# `jarvis.ask()` 40 daqiqagacha davom etishi mumkin bo'lgan uzoq vazifalarda
# band bo'ladi) bilan HECH QANDAY bog'liqligi yo'q. PTB'ning polling
# (`app.updater`) o'zi ham `concurrent_updates(True)` bilan handler'lardan
# mustaqil ishlaydi — shuning uchun Jarvis uzoq ish bilan band bo'lsa ham
# (masalan 15-40 daqiqalik vazifa) bu heartbeat TO'XTAMAYDI, watchdog buni
# "qotib qolish" deb noto'g'ri talqin qilmaydi.
_HEARTBEAT_JARVIS_FAYL = Path(__file__).resolve().parent / (
    "heartbeat_jarvis_sinov.json" if _SINOV else "heartbeat_jarvis.json"
)
_heartbeat_jarvis_holat = {"last_ok": None}


def _heartbeat_jarvis_yoz() -> None:
    try:
        yozuv = {
            "heartbeat_vaqti": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_ok": _heartbeat_jarvis_holat["last_ok"],
        }
        _HEARTBEAT_JARVIS_FAYL.write_text(json.dumps(yozuv, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        diag(f"Watchdog heartbeat faylga yozib bo'lmadi: {e}")


async def _watchdog_heartbeat_bir_marta(app: Application) -> None:
    tarmoq_ok = False
    try:
        await app.bot.get_me()
        tarmoq_ok = True
    except (TelegramError, Exception) as e:
        diag(f"Watchdog heartbeat: Telegram bilan aloqa muvaffaqiyatsiz: {e}")

    polling_ok = bool(app.updater and app.updater.running)
    if not polling_ok:
        diag("Watchdog heartbeat: app.updater.running=False -- polling to'xtagan (last_ok yangilanmaydi).")

    if tarmoq_ok and polling_ok:
        _heartbeat_jarvis_holat["last_ok"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _heartbeat_jarvis_yoz()


async def _watchdog_heartbeat_aylanish(app: Application) -> None:
    """Cheksiz sikl -- har 60 soniyada, `handle()`dagi `lock`dan MUSTAQIL
    ravishda ishlaydi (band/bo'sh holatidan qat'i nazar)."""
    while True:
        try:
            await _watchdog_heartbeat_bir_marta(app)
        except Exception as e:
            diag(f"Watchdog heartbeat aylanishida kutilmagan xato: {e}")
        await asyncio.sleep(60)


async def post_init(app: Application):
    # 2026-09-27 TUZATISH: watchdog-heartbeat ENG BIRINCHI ishga tushiriladi --
    # `jarvis.__aenter__()` (Claude Agent SDK ulanishi, xotira yuklash va h.k.)
    # bir necha daqiqa cho'zilishi mumkin; agar heartbeat shundan KEYIN
    # boshlansa, shu davrda heartbeat_jarvis.json UMUMAN yozilmaydi va
    # watchdog buni xato ravishda "muammo" deb talqin qilib, hali to'liq
    # ishga tushmagan Jarvisni o'ldirib qo'yishi mumkin edi (2026-09-27,
    # 15:32'da aynan shu bo'ldi). Bu task faqat `app.bot`/`app.updater`ga
    # muhtoj, `jarvis`ga bog'liq emas -- shuning uchun undan oldin xavfsiz.
    app.create_task(_watchdog_heartbeat_aylanish(app))
    jarvis = Jarvis(extra_prompt=EXTRA, confirm_fn=auto_approve)
    await jarvis.__aenter__()
    app.bot_data["jarvis"] = jarvis
    app.bot_data["heartbeat"] = asyncio.create_task(_heartbeat())
    print("Jarvis ulandi. Telegram'da /start yozing.")


async def post_shutdown(app: Application):
    heartbeat = app.bot_data.get("heartbeat")
    if heartbeat:
        heartbeat.cancel()
    jarvis = app.bot_data.get("jarvis")
    if jarvis:
        print("Xotira yangilanyapti...")
        await jarvis.remember()
        await jarvis.__aexit__(None, None, None)
    print("Tayyor.")


def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        # 2026-09-26 MUHIM: standart holatda PTB yangilanishlarni BITTALAB,
        # NAVBAT bilan qayta ishlaydi ("If not called, updates will be
        # processed one by one" — ApplicationBuilder hujjati). Bu bilan
        # /stop (`stop_cmd`) band paytida (jarvis.ask() hali tugamagan
        # handle() ichida) HECH QACHON dispatch qilinmas edi — PTB navbatda
        # oldingi handler tugashini kutib turardi, /stop shu navbatda
        # tiqilib qolardi. `concurrent_updates(True)` bilan har yangilanish
        # alohida task sifatida ishga tushadi — /stop endi band paytida ham
        # DARHOL ishlaydi.
        .concurrent_updates(True)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("esla", esla))
    app.add_handler(CommandHandler("ovoz", ovoz_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(
        MessageHandler(
            filters.Document.ALL
            | filters.PHOTO
            | filters.VOICE
            | filters.AUDIO
            | filters.VIDEO,
            handle_file,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(xodim_tugma_bosildi))

    print("Telegram bot ishga tushdi. To'xtatish: Ctrl+C")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        pass
    print("Bot to'xtadi.")


if __name__ == "__main__":
    main()
