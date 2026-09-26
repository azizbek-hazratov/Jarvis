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
import re
import subprocess
from datetime import datetime
from pathlib import Path

from contextlib import asynccontextmanager

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from jarvis_core import Jarvis, auto_approve, diag
from jarvis_holati_signal import band_belgila, bosh_belgila  # pixel-ofis "AI Xodimlarim" uchun band/bo'sh signali

try:
    from config import TELEGRAM_TOKEN, OWNER_ID
except ImportError:
    raise SystemExit(
        "config.py fayli topilmadi yoki to'liq emas.\n"
        "config.py ichida TELEGRAM_TOKEN va OWNER_ID bo'lishi kerak."
    )

lock = asyncio.Lock()

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
"""

YUBOR_RE = re.compile(r"\[\[\s*YUBOR\s*:\s*(.+?)\s*\]\]")
MAX_FAYL = 49 * 1024 * 1024  # Telegram bot chegarasi ~50 MB

# ---------- Ovozli xabarlarni avtomatik matnga o'girish ----------
# Asosiy yo'l: Google STT (bepul web API) — tez (~2 soniya) va sezilarli aniqroq.
# Zaxira yo'l: mahalliy Whisper "small" — internet yo'q yoki Google xato bersa
# ishga tushadi, sekinroq va kamroq aniq, lekin hech bo'lmaganda tezroq javob
# beradi ("medium" model sinalgan edi — 5 daqiqa ketib ustiga NOTO'G'RI natija
# berdi, shuning uchun zaxira sifatida ham ishlatilmaydi, 2026-09-05).
#
# Model bir marta yuklanadi (birinchi ovozli xabarda), keyin xotirada qoladi —
# har safar qayta yuklanmaydi, shuning uchun 2-xabardan boshlab tez ishlaydi.
_whisper_model = None


def _whisper_yukla():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        modellar_dir = Path(__file__).parent / "transkripsiya" / "modellar"
        _whisper_model = WhisperModel(
            "small", device="cpu", compute_type="int8", download_root=str(modellar_dir)
        )
    return _whisper_model


def _whisper_bilan(fayl_yoli: str) -> str:
    """Til ATAYLAB "uz" ga qattiq belgilangan — avtomatik til aniqlash ba'zan
    noto'g'ri tilni (masalan fors) tanlab, butunlay tushunarsiz natija
    berishi aniqlangan (2026-09-05)."""
    model = _whisper_yukla()
    segments, _info = model.transcribe(fayl_yoli, language="uz", beam_size=5)
    return " ".join(s.text.strip() for s in segments).strip()


def _google_bilan(fayl_yoli: str) -> str:
    """Telegram OGG/Opus faylni ffmpeg orqali 16kHz mono WAV'ga o'girib,
    Google'ning bepul Speech-to-Text web API'siga yuboradi. Internet talab
    qiladi, ~2 soniyada javob beradi."""
    import speech_recognition as sr

    wav_yol = str(Path(fayl_yoli).with_suffix(".wav"))
    subprocess.run(
        ["ffmpeg", "-y", "-i", fayl_yoli, "-ar", "16000", "-ac", "1", wav_yol],
        check=True,
        capture_output=True,
    )
    try:
        r = sr.Recognizer()
        with sr.AudioFile(wav_yol) as source:
            audio = r.record(source)
        return r.recognize_google(audio, language="uz-UZ").strip()
    finally:
        Path(wav_yol).unlink(missing_ok=True)


def ovozni_matnga(fayl_yoli: str) -> str:
    """Ovoz faylini o'zbekcha matnga o'giradi. Avval Google STT (tez, aniq),
    ishlamasa (internet yo'q, timeout, ffmpeg xatosi va h.k.) mahalliy Whisper
    "small" ga tushadi."""
    try:
        matn = _google_bilan(fayl_yoli)
        if matn:
            return matn
    except Exception:
        pass
    return _whisper_bilan(fayl_yoli)


async def deliver(msg, javob: str):
    """Javobni yuboradi. [[YUBOR: yo'l]] belgilari bo'lsa, fayllarni ham."""
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


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Faqat egasi bilan gaplashadi
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Kechirasiz, men shaxsiy yordamchiman.")
        return

    diag("xabar qabul qilindi")
    text = update.message.text
    jarvis: Jarvis = context.application.bot_data["jarvis"]

    if lock.locked():
        await update.message.reply_text(
            "⏳ Band — oldingi so'rovni bajarayapman, tugashi bilan shu xabaringizga javob beraman."
        )

    async with lock, yozyapti(context, update.effective_chat.id):
        band_belgila("telegram")  # pixel-ofis: Jarvis Telegramdan real so'rov ishlayapti
        try:
            javob = await jarvis.ask(text)
        except Exception as e:
            javob = f"Xatolik yuz berdi: {e}"
        finally:
            bosh_belgila("telegram")

    await deliver(update.message, javob)
    diag("foydalanuvchiga yuborildi")


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
                savol = (
                    "(Bu — Azizbekning ovozli xabari, avtomatik ravishda matnga "
                    "o'girildi. Transkripsiya ba'zan noaniq/xato chiqishi mumkin — "
                    "agar matn mantiqsiz yoki tushunarsiz ko'rinsa, taxmin qilib ish "
                    "qilaverma, aniq nima demoqchi bo'lganini so'ra.)\n\n"
                    f"{matn}"
                )
            else:
                savol = (
                    "Azizbek ovozli xabar yubordi, lekin avtomatik matnga o'girish "
                    "muvaffaqiyatsiz bo'ldi (bo'sh natija chiqdi — ehtimol ovoz juda "
                    "past yoki fayl buzilgan). Undan matn yozib yuborishni yoki "
                    "qayta gapirib ko'rishni so'ra."
                )
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
        async with lock:
            band_belgila("telegram")  # pixel-ofis: Jarvis Telegramdan real so'rov ishlayapti
            try:
                javob = await jarvis.ask(savol)
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


async def post_init(app: Application):
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
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("esla", esla))
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

    print("Telegram bot ishga tushdi. To'xtatish: Ctrl+C")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        pass
    print("Bot to'xtadi.")


if __name__ == "__main__":
    main()
