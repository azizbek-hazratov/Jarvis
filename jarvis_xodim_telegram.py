"""
JARVIS OS -- Telegramdan xodimlarga to'g'ridan-to'g'ri murojaat
(2026-09-28, Azizbek "AI xodimlar -- 1-bosqich" vazifasi, band 1).

G'OYA: "Nozima, ..." / "Sardor, ..." kabi Telegram xabarlari HUD panelidagi
"ismga murojaat" BILAN BIR XIL dispatch mantig'iga yo'naltiriladi -- mantiq
IKKI MARTA yozilmaydi, BITTA manba (bridge, port 8090, /jamoa/savol va
/jamoa/tasdiqlash/bekor_qilish) orqali ishlaydi. jarvis_telegram.py (asosiy
Jarvis jarayoni) faqat: (1) matnni aniqlaydi, (2) bridge'ga so'rov yuboradi,
(3) natijani ism+rasm+ovoz bilan Telegramga chiroyli formatlab yetkazadi.

XAVFSIZLIK: bu modul HECH QANDAY yozish/o'zgartirish qilmaydi -- faqat
bridge'ning MAVJUD, allaqachon sinalgan endpointlariga HTTP so'rov yuboradi.
Mijozga/ota-onaga haqiqiy xabar yuborish zanjiri BU YERDA HAM yoqilmagan --
"yozish" turidagi topshiriqlar bridge orqali tasdiqlangandan keyin ham
FAQAT Azizbekka natija qaytaradi (jarvis_hud_bridge._topshiriq_bajar), real
tashqi xabar yuborish qobiliyati tizimda umuman mavjud emas.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE / "jarvis_hud"))
from hud_token import HUD_TOKEN  # noqa: E402

import jarvis_jamoa_data as jjd  # noqa: E402

BRIDGE = "http://localhost:8090"
_HEADERS = {"Authorization": f"Bearer {HUD_TOKEN}"}
PORTRET_DIR = BASE / "jarvis_hud" / "portretlar"

# "yozish" turidagi topshiriqlarni tasdiqlash/bekor qilish so'rovi -- SAVOL
# yuborishdan tezroq javob kutiladi (odam kutib turibdi, tugma bosdi).
_TASDIQ_TIMEOUT_S = 15
# Savol/topshiriq javobi -- AI yo'liga tushsa 150s gacha cho'zilishi mumkin
# (bridge'dagi JAMOA_SAVOL_TIMEOUT_S bilan BIR XIL + kichik zaxira).
_SAVOL_TIMEOUT_S = 170


def xodimga_murojaatmi(text: str):
    """"Nozima, qarzdorlar ro'yxatini bergin" kabi xabarni aniqlaydi.
    Qaytaradi: (xodim_id, qolgan_matn) yoki None (bu xodimga murojaat emas).
    Jarvisning o'zi ATAYLAB bu ro'yxatga kiritilmagan -- "Jarvis, ..." oddiy
    chat sifatida ishlashda davom etadi (o'zgarishsiz).

    2026-09-28 (Azizbek imtihon-tuzatishi): avval bu yerda ANIQ, qat'iy
    ism+tinish belgisi talab qilinardi ("Nozima," aynan shu shaklda) --
    STT xatolari ("begzod", "nazima") yoki vergulsiz ovozli murojaat
    ("begzodbotlar ishlayaptimi") UMUMAN ishlamas edi. Endi HUD panel bilan
    BIR XIL, umumiy `jarvis_jamoa_data.xodim_ismini_top()` ishlatiladi."""
    if not text:
        return None
    return jjd.xodim_ismini_top(text)


def xodim_nomi(xodim_id: str) -> str:
    return jjd.XODIMLAR.get(xodim_id, {}).get("name", xodim_id)


def portret_yoli(xodim_id: str):
    p = PORTRET_DIR / f"{xodim_id}.jpg"
    return p if p.exists() else None


def bridge_savol(xodim_id: str, matn: str) -> dict:
    """HUD panelidagi '/jamoa/savol' BILAN BIR XIL -- yo'naltirish, "ma'lumot
    yo'q" va tasdiq-navbat qoidalari panel bilan AYNAN bir xil ishlaydi
    (ikkalasi ham bitta bridge funksiyasini chaqiradi)."""
    r = requests.post(
        f"{BRIDGE}/jamoa/savol", json={"xodim": xodim_id, "matn": matn},
        headers=_HEADERS, timeout=_SAVOL_TIMEOUT_S,
    )
    r.raise_for_status()
    return r.json()


def bridge_tasdiqlash(task_id: str) -> dict:
    r = requests.post(
        f"{BRIDGE}/jamoa/tasdiqlash", json={"id": task_id},
        headers=_HEADERS, timeout=_TASDIQ_TIMEOUT_S,
    )
    return r.json() if r.ok else {"error": r.text}


def bridge_bekor_qilish(task_id: str) -> dict:
    r = requests.post(
        f"{BRIDGE}/jamoa/bekor_qilish", json={"id": task_id},
        headers=_HEADERS, timeout=_TASDIQ_TIMEOUT_S,
    )
    return r.json() if r.ok else {"error": r.text}


# 2026-09-28 (Azizbek buyrug'i): "<ism>ga ... deb yoz" -- shaxsiy Telegram
# (userbot) orqali yuborish, HUD ('/ask') bilan BIR XIL markaziy
# `_shaxsiy_buyruq_ishla` funksiyasiga boradi (bridge tomonida).
def bridge_shaxsiy_buyruq(matn: str) -> dict:
    r = requests.post(
        f"{BRIDGE}/shaxsiy/buyruq", json={"matn": matn},
        headers=_HEADERS, timeout=_SAVOL_TIMEOUT_S,
    )
    r.raise_for_status()
    return r.json()


def bridge_shaxsiy_bekor(task_id: str) -> dict:
    r = requests.post(
        f"{BRIDGE}/shaxsiy/bekor", json={"id": task_id},
        headers=_HEADERS, timeout=_TASDIQ_TIMEOUT_S,
    )
    return r.json() if r.ok else {"error": r.text}


def bridge_speak_mp3(xodim_id: str, text: str, timeout: int = 30):
    """Xodimning o'z ovozida (edge-tts, panel bilan bir xil) mp3 bayt.
    Xato bo'lsa None (ovozsiz ham matn+rasm yuborilaveradi -- ovoz shart
    emas, "kutish sezilmasin" naqshi -- MUHIM narsa matn/tugma, ovoz bonus)."""
    try:
        r = requests.post(
            f"{BRIDGE}/jamoa/speak", json={"xodim": xodim_id, "text": text},
            headers=_HEADERS, timeout=timeout,
        )
        if not r.ok:
            return None
        return r.content
    except Exception:
        return None


def mp3_ni_ogg_ga_otkaz(mp3_bytes: bytes):
    """Telegram 'ovoz xabari' (voice bubble) uchun OGG/Opus kerak --
    `jarvis_ertalabki_yigilish.py`dagi BILAN BIR XIL ffmpeg buyrug'i.
    Muvaffaqiyatsiz bo'lsa None qaytaradi (chaqiruvchi shunda audio
    yubormasdan davom etadi, matn+rasm baribir yetib boradi)."""
    try:
        with tempfile.TemporaryDirectory() as td:
            mp3_yol = Path(td) / "in.mp3"
            ogg_yol = Path(td) / "out.ogg"
            mp3_yol.write_bytes(mp3_bytes)
            natija = subprocess.run(
                ["ffmpeg", "-y", "-i", str(mp3_yol), "-c:a", "libopus",
                 "-b:a", "48k", "-ar", "48000", "-ac", "1", str(ogg_yol)],
                capture_output=True, timeout=30,
            )
            if natija.returncode != 0 or not ogg_yol.exists():
                return None
            return ogg_yol.read_bytes()
    except Exception:
        return None
