"""
Ovozni matnga o'giruvchi umumiy modul (2026-09-28, "ovozli buyruq" bandi
uchun `jarvis_telegram.py`dan ALOHIDA modulga ko'chirildi -- shunda
`jarvis_hud_bridge.py` (panel 🎤 tugmasi) ham AYNAN shu STT mantig'idan
foydalanadi, ikkinchi marta yozilmaydi).

Asosiy yo'l: Google STT (bepul web API) — tez (~2 soniya) va sezilarli aniqroq.
Zaxira yo'l: mahalliy Whisper "small" — internet yo'q yoki Google xato bersa
ishga tushadi, sekinroq va kamroq aniq, lekin hech bo'lmaganda tezroq javob
beradi ("medium" model sinalgan edi — 5 daqiqa ketib ustiga NOTO'G'RI natija
berdi, shuning uchun zaxira sifatida ham ishlatilmaydi, 2026-09-05).

2026-10-11 (Azizbek buyrug'i, "ovozli xabar -- o'zbek, rus, ingliz tillari"):
avval til HAR DOIM "uz" ga qattiq yozilgan edi (2026-09-05dagi tuzatish --
avtomatik til aniqlash ba'zan noto'g'ri tilni, masalan fors, tanlardi).
Endi: har ovozli xabar uchun AVVAL faqat TIL aniqlanadi (Whisper'ning tez,
to'liq-transkripsiyasiz usuli bilan -- bitta mel-spektrogramma, ~0.3-1s),
FAQAT shu 3 tildan (uz/ru/en) biriga ishonch yetarli (>=0.5) bo'lsa o'sha
til ishlatiladi, aks holda (boshqa til yoki past ishonch) xavfsiz
standart -- "uz" ga qaytiladi (eski xulq saqlanadi).

Qaysi tizim ishlatilgani, necha soniya ketgani va xato bo'lsa aniq matni
`jarvis_core.diag()` orqali logga yoziladi (jim try/except: pass YO'Q --
botlar ham shu umumiy Claude limitidan foydalangani uchun shaffoflik kerak).
"""

import subprocess
import time
from pathlib import Path

from jarvis_core import diag

BASE = Path(__file__).parent

# Modellar bir marta yuklanadi (birinchi ovozli xabarda), keyin xotirada
# qoladi — har safar qayta yuklanmaydi, shuning uchun 2-xabardan boshlab
# tez ishlaydi. IKKI xil model ataylab: "tiny" -- FAQAT til aniqlash uchun
# (2026-10-11, sinovda: "small" bilan til aniqlash ~5-6s, "tiny" bilan
# ~0.3-0.8s -- 10 baravar tezroq, aniqlik farqi til-aniqlash vazifasi uchun
# amalda sezilmaydi), "small" -- haqiqiy transkripsiya (Google zaxirasi)
# uchun, aniqligi yuqoriroq saqlanadi.
_whisper_model = None
_whisper_til_model = None


def _whisper_yukla():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        modellar_dir = BASE / "transkripsiya" / "modellar"
        _whisper_model = WhisperModel(
            "small", device="cpu", compute_type="int8", download_root=str(modellar_dir)
        )
    return _whisper_model


def _whisper_til_yukla():
    global _whisper_til_model
    if _whisper_til_model is None:
        from faster_whisper import WhisperModel

        modellar_dir = BASE / "transkripsiya" / "modellar"
        _whisper_til_model = WhisperModel(
            "tiny", device="cpu", compute_type="int8", download_root=str(modellar_dir)
        )
    return _whisper_til_model


_QOLLAB_TILLAR = ("uz", "ru", "en")
_GOOGLE_TIL_KODI = {"uz": "uz-UZ", "ru": "ru-RU", "en": "en-US"}


def _tilni_aniqla(fayl_yoli: str) -> str:
    """Faqat TIL aniqlaydi, to'liq transkripsiya QILMAYDI -- "tiny" model +
    `detect_language()` bilan tez (~0.3-0.8s). Faqat uz/ru/en'ga ishonch
    >=0.5 bo'lsa shu til, aks holda xavfsiz standart "uz" (2026-09-05dagi
    "fors/turk/ozarbayjon tiliga adashish" bugidan himoya -- Whisper o'zbek
    nutqini ko'pincha past ishonch bilan shu qardosh tillardan biriga
    chiqaradi, shu mezon saqlanib qoldi, faqat endi 3 ta tilga
    kengaytirildi, sinovda real namunalar bilan tasdiqlangan: ruscha ->
    ru 1.0, inglizcha -> en 0.95, o'zbekcha -> past ishonch -> "uz")."""
    from faster_whisper import decode_audio

    model = _whisper_til_yukla()
    audio = decode_audio(fayl_yoli)
    til, ishonch, _barcha = model.detect_language(audio=audio, language_detection_segments=1)
    if til in _QOLLAB_TILLAR and ishonch >= 0.5:
        return til
    return "uz"


def _whisper_bilan(fayl_yoli: str, til: str = "uz") -> str:
    model = _whisper_yukla()
    segments, _info = model.transcribe(fayl_yoli, language=til, beam_size=5)
    return " ".join(s.text.strip() for s in segments).strip()


def _google_bilan(fayl_yoli: str, til: str = "uz") -> str:
    """Kiruvchi ovoz faylni (OGG/WebM/MP3 -- ffmpeg o'qiy oladigan har qanday
    format) ffmpeg orqali 16kHz mono WAV'ga o'girib, Google'ning bepul
    Speech-to-Text web API'siga yuboradi. Internet talab qiladi, ~2 soniyada
    javob beradi."""
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
        return r.recognize_google(audio, language=_GOOGLE_TIL_KODI.get(til, "uz-UZ")).strip()
    finally:
        Path(wav_yol).unlink(missing_ok=True)


def ovozni_matnga(fayl_yoli: str) -> str:
    """Ovoz faylini matnga o'giradi (o'zbek/rus/ingliz -- avval til aniqlanadi).
    Avval Google STT (tez, aniq), ishlamasa (internet yo'q, timeout, ffmpeg
    xatosi va h.k.) mahalliy Whisper "small" ga tushadi."""
    tl0 = time.monotonic()
    try:
        til = _tilni_aniqla(fayl_yoli)
        diag(f"STT: til aniqlandi -- '{til}' ({time.monotonic() - tl0:.1f}s)")
    except Exception as e:
        diag(f"STT: til aniqlashda xato -- {e} -- standart 'uz' bilan davom etyapman")
        til = "uz"

    t0 = time.monotonic()
    try:
        matn = _google_bilan(fayl_yoli, til)
    except Exception as e:
        diag(f"STT xato: google ({time.monotonic() - t0:.1f}s) -- {e} -- whisper zaxiraga o'tyapman")
    else:
        daq = time.monotonic() - t0
        if matn:
            diag(f"STT: google ishlatildi ({til}), {daq:.1f}s")
            return matn
        diag(f"STT: google bo'sh natija qaytardi ({daq:.1f}s) -- whisper zaxiraga o'tyapman")

    t1 = time.monotonic()
    try:
        matn = _whisper_bilan(fayl_yoli, til)
    except Exception as e:
        diag(f"STT xato: whisper HAM ({time.monotonic() - t1:.1f}s) -- {e}")
        raise
    diag(f"STT: whisper ishlatildi (zaxira, {til}), {time.monotonic() - t1:.1f}s")
    return matn
