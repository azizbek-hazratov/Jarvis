"""
JARVIS HUD — bridge server (E2-bosqich)

Bu fayl jarvis_hud/index.html'dagi "ESHITILGAN MATN -> Yuborish" tugmasini
asosiy Jarvis "miyasi"ga (jarvis_core.Jarvis) bog'laydi.

MUHIM — xavfsizlik/izolyatsiya:
- jarvis_core.py'ga BIRON O'ZGARTIRISH kiritilmagan, faqat undan Jarvis
  klassi import qilinadi.
- (E9-bosqich) Tezlik uchun server ishga tushganda BITTA Jarvis sessiyasi
  ochib qo'yiladi va barcha /ask so'rovlari shu sessiyaga yuboriladi (har
  safar qaytadan ulanish o'rnatilmaydi). Bu sessiya ishlab turgan Telegram
  botining (jarvis_telegram.py) obyektidan BUTUNLAY MUSTAQIL — chunki bu
  boshqa Python jarayoni (`python jarvis_hud_bridge.py` alohida process
  sifatida ishga tushadi), ular xotira/ulanish darajasida hech qanday
  bog'liqligi yo'q, bir-biriga ta'sir qilmaydi. Agar bu doimiy sessiya
  biron sababdan ochilmasa/xato bersa, avtomatik ravishda har bir so'rov
  uchun alohida, yangi Jarvis obyekti yaratadigan eski (sekinroq, lekin
  sinalgan) usulga qaytiladi.
- Bu server HUD sahifasi (8080-port, sinov_boshlash.bat) bilan bir xil
  portda emas — 8090-portda ishlaydi, to'qnashuv bo'lmaydi.

Ishga tushirish: `python jarvis_hud_bridge.py` yoki sinov_bridge_boshlash.bat
"""

import asyncio
import concurrent.futures
import json as _json
import os
import difflib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from flask import Flask, Response, jsonify, request

# jarvis_core.py bir papka yuqorida (C:\Users\Dell\jarvis\) joylashgan —
# uni import qilish uchun shu papkani Python yo'liga qo'shamiz.
BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from jarvis_core import Jarvis, auto_approve  # noqa: E402  (faqat import — fayl o'zgartirilmagan)
from hud_token import HUD_TOKEN  # noqa: E402  (roadmap #5 — token-asosli autentifikatsiya)
from claude_agent_sdk import PermissionResultDeny  # noqa: E402  (roadmap #7 — faqat natija turini aniqlash uchun, cheklov qo'shmaymiz)
import jarvis_bildirishnoma  # noqa: E402  (roadmap #9 MVP — bridge FAQAT o'qiydi, yozmaydi)
from jarvis_holati_signal import band_belgila, bosh_belgila, biror_joyda_bandmi, manba_bandmi  # noqa: E402  (pixel-ofis: Telegram+bridge umumiy band/bo'sh signali; manba_bandmi — 2026-09-22, AI Expert bosqichi, boshqa mustaqil botlar uchun ALOHIDA o'qish, asosiy Jarvis holatiga aralashmaydi)
import jarvis_jamoa_data  # noqa: E402  (5-bosqich, 2026-09-27 — "Jamoa" paneli, Telegram'dagi "jamoa" bilan BIR XIL umumiy modul)
import jarvis_majlis  # noqa: E402  (5-bosqich davomi, 2026-09-28 — "Majlis" + "ismga murojaat")
import jarvis_xodim_dispatch  # noqa: E402  (2026-09-28 kechasi — "har kim o'z sohasida" domen-yo'naltirish)
import jarvis_xodim_qoidalar  # noqa: E402  (2026-09-28, "1-bosqich" band 2 — har xodim uchun tanbeh/qoida xotirasi)
import jarvis_topshiriq_tarixi  # noqa: E402  (2026-09-28, "1-bosqich" band 3 — doimiy topshiriq-tarixi, kunlik hisobot uchun)
import time as _time  # noqa: E402  (band 3 — topshiriq davomiyligini o'lchash uchun, mavjud `time` bilan chalkashmasin)
from jarvis_proaktiv import telegram_xabar_yubor  # noqa: E402  (topshiriq natijasini Telegram'ga yuborish uchun, mavjud sinalgan funksiya)
# MUHIM (2026-09-13 topilgan xato): confirm_fn ko'rsatilmasa, jarvis_core.Jarvis
# ICHKI standart bo'yicha _confirm_deny'ni ishlatadi — ya'ni Bash VA Gmail/Drive/
# Calendar/Canva yozish amallarining BARCHASI rad etiladi ("Bu vositani ishlatish
# uchun ruxsat yo'q"). jarvis_telegram.py esa har doim confirm_fn=auto_approve
# beradi — shuning uchun HUD orqali so'ralganda Jarvis Telegram'dagidan ANCHA
# kambag'al ishlar edi (masalan email yubora olmas, fayl o'chira olmas, Bash
# ishlata olmas edi), garchi ikkalasi ham bir xil jarvis_core "miya"sini
# ishlatsa ham. Pastda ikkala Jarvis(...) chaqiruviga ham confirm_fn=auto_approve
# qo'shildi — endi HUD Telegram bilan BIR XIL to'liq imkoniyatga ega (xavfli
# buyruqlar baribir jarvis_core ichida bloklangan, o'zgarishsiz qoladi).

import edge_tts  # noqa: E402  (E3-bosqich: /speak endpoint uchun, ovozga_aylantir.py'dagi bilan bir xil kutubxona)

# E4-bosqich: /transcribe endpoint uchun — jarvis_telegram.py'da ovozli xabarlar uchun
# ishlatilgan bilan BIR XIL, sinalgan usul (Google STT asosiy, mahalliy Whisper zaxira).
# jarvis_telegram.py'ning o'ziga tegilmagan/import qilinmagan — bu yerda mustaqil nusxa,
# bridge boshqa jarayonlardan butunlay izolyatsiyalangan bo'lib qolishi uchun.
import speech_recognition as sr  # noqa: E402

# --- Tezkor buyruq-aniqlash qatlami (E8-bosqich) ---
# Demo paytida eng ko'p ishlatiladigan buyruqlar (brauzer ochish+qidirish,
# namoz vaqtlari) uchun jarvis_core'ning to'liq Claude Agent SDK aylanishini
# (bir necha soniya — ba'zan o'nlab soniya) BUTUNLAY chetlab o'tamiz va
# to'g'ridan-to'g'ri shu yerda, oddiy Python bilan bajaramiz. jarvis_core.py'ga
# HECH QANDAY tegilmaydi — bu faqat bridge ichidagi qo'shimcha "tezkor yo'l".
# Mos kelmagan har qanday boshqa so'rov o'zgarishsiz pastdagi sekin
# jarvis_core.ask() yo'liga tushadi.

_STT_TUZATISH = [
    (r"\bjariz\b", "jarvis"),
    (r"\bjarvic\b", "jarvis"),
    (r"\bjarvís\b", "jarvis"),
    (r"\bxromno\b", "chrome'ni"),
    (r"\bxromni\b", "chrome'ni"),
    (r"\bxrom\b", "chrome"),
    (r"\byutuqda\b", "youtube'da"),
    (r"\byutubda\b", "youtube'da"),
    (r"\byutub\b", "youtube"),
    (r"\bguglda\b", "google'da"),
]


def _sst_tuzat(matn: str) -> str:
    """Brauzer/Google/Whisper STT'dan kelgan matndagi tez-tez uchraydigan
    ingliz nomlarining (chrome, youtube, jarvis) o'zbekcha talaffuzdan kelib
    chiqqan buzilishlarini tuzatadi."""
    natija = matn
    for naqsh, oz in _STT_TUZATISH:
        natija = re.sub(naqsh, oz, natija, flags=re.IGNORECASE)
    return natija


_SALOM_NAQSH = re.compile(
    r"^(salom|assalomu\s*alaykum|alaykum\s*assalom|hey|hi|salomlar|"
    r"xayrli\s+(kun|tong|kech))"
    # "jarvis" so'zining o'zini ANIQ talab qilmaymiz — STT buni har safar
    # boshqacha buzadi (jariz, jarvic, jarroh va h.k., ro'yxati cheksiz).
    # Shuning uchun salomlashuv so'zidan keyin FAQAT bitta qisqa so'z kelsa
    # (bu STT "jarvis" deb aytishga urinishi ehtimoli katta), baribir oddiy
    # salomlashuv deb qabul qilinadi.
    r"([\s,!.]+[\w']{1,12})?[\s,!.]*$",
    re.IGNORECASE,
)

_OCHISH_KALIT = re.compile(r"\b(och|ochib|ochsang|ochib\s+ber\w*)\b", re.IGNORECASE)
_QIDIRISH_KALIT = re.compile(r"\b(qidir\w*|izla\w*|top\w*)\b", re.IGNORECASE)
# STT "youtube"/"google" so'zlarini ko'p xil tarzda buzadi (yutuqda, yutubda,
# yutubdan, utubda va h.k.) — shuning uchun to'liq so'z o'rniga faqat
# TANIYDIGAN BOSHLANG'ICH BO'LAKni (prefiks) tekshiramiz, davomi qanday
# buzilgan bo'lishidan qat'iy nazar.
_YOUTUBE_ISHORASI = re.compile(r"\b(yout\w*|yutu\w*|utub\w*|itub\w*)\b", re.IGNORECASE)
_GOOGLE_ISHORASI = re.compile(r"\b(googl\w*|gugl\w*)\b", re.IGNORECASE)
_SAYT_NOMLARI = {
    "youtube": "https://www.youtube.com/results?search_query={q}",
    "google": "https://www.google.com/search?q={q}",
}
# Qidiruv so'zidan tozalanadigan bo'laklar — "jarvisromni" kabi bir nechta
# so'z bir-biriga yopishib qolgan holatlarni ham qamrab olish uchun ANIQ
# so'z ("xromni") emas, balki BOSHLANG'ICH bo'lak + \w* ishlatiladi.
_TOZALASH_NAQSHLARI = [
    r"\bjarvis\w*", r"\bxrom\w*", r"\bchrom\w*",
    r"\byout\w*", r"\byutu\w*", r"\butub\w*", r"\bitub\w*",
    r"\bgoogl\w*", r"\bgugl\w*",
    r"\bbrauzer\w*", r"\bbrowser\w*",
    r"\bochib\s+ber\w*\b", r"\bochsang\b", r"\bochib\b", r"\boch\b",
    r"\bmenga\b", r"\bdeb\b",
]


def _qidiruv_tozala(q: str) -> str:
    """Qidiruv so'zidan sayt/ism/fe'l qoldiqlarini tozalaydi (masalan
    "chrome'ni ochib youtube'da medina deb qidir" dan faqat "medina" qoladi)."""
    q = q.replace("'", "").replace("’", "")
    for naqsh in _TOZALASH_NAQSHLARI:
        q = re.sub(naqsh, " ", q, flags=re.IGNORECASE)
    q = re.sub(r"[^\w\s]", " ", q, flags=re.UNICODE)
    return re.sub(r"\s+", " ", q).strip()

_CHROME_YOLLARI = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _brauzer_ochish(url: str):
    """Chrome'ni (yoki topilmasa tizimning standart brauzerini) berilgan
    URL bilan ochadi. Jarvis watchdog/bot LogonTrigger+InteractiveToken
    orqali foydalanuvchining haqiqiy ish stoli sessiyasida ishlagani uchun
    (jarvis_watchdog_task.xml), bu yerda ochilgan oyna ekranda ko'rinadi."""
    for yol in _CHROME_YOLLARI:
        if os.path.exists(yol):
            subprocess.Popen([yol, url])
            return
    yoli = shutil.which("chrome")
    if yoli:
        subprocess.Popen([yoli, url])
        return
    webbrowser.open(url)


def _namoz_vaqtlari(shahar: str) -> str:
    url = "http://api.aladhan.com/v1/timingsByCity?city=" + urllib.parse.quote(shahar) + "&country=Uzbekistan&method=2"
    if shahar.lower() in ("medina", "makkah", "mekka", "makka"):
        url = "http://api.aladhan.com/v1/timingsByCity?city=" + urllib.parse.quote(shahar) + "&country=Saudi Arabia&method=4"
    with urllib.request.urlopen(url, timeout=6) as resp:
        data = _json.loads(resp.read().decode("utf-8"))
    t = data["data"]["timings"]
    return (
        f"{shahar.title()} uchun bugungi namoz vaqtlari — "
        f"Bomdod: {t['Fajr']}, Peshin: {t['Dhuhr']}, Asr: {t['Asr']}, "
        f"Shom: {t['Maghrib']}, Xufton: {t['Isha']}."
    )


def _tezkor_buyruq(matn: str):
    """Matnda tezkor bajariladigan buyruq (brauzer ochish+qidirish yoki namoz
    vaqtlari) bor-yo'qligini tekshiradi. Topilsa — darhol bajaradi va
    (True, javob_matni) qaytaradi. Topilmasa — (False, None), chaqiruvchi
    tomon oddiy jarvis_core yo'liga o'tadi."""
    m = matn.lower()
    if _SALOM_NAQSH.match(matn.strip()):
        # Oddiy salomlashuv ("salom jarvis" va h.k.) — jarvis_core'ga umuman
        # murojaat qilmasdan darhol javob beramiz, bu eng ko'p uchraydigan
        # ochilish so'zi bo'lgani uchun sinovda tez javob berish muhim edi.
        return True, "Salom! Xizmatingizga tayyorman — nima qilib beray?"

    ochish_bor = bool(_OCHISH_KALIT.search(m)) or "brauzer" in m or "chrome" in m
    qidirish_bor = bool(_QIDIRISH_KALIT.search(m))
    youtube_bor = bool(_YOUTUBE_ISHORASI.search(m))
    google_bor = bool(_GOOGLE_ISHORASI.search(m))

    # MUHIM: "chrome"/"youtube" so'zlarining o'zini TOPISHGA majburiy tayanmaymiz —
    # STT bularni ko'pincha butunlay tanib bo'lmas darajada buzadi (masalan
    # "jarvisromni" = "jarvis"+"xromni" bir so'zga yopishib ketgan holat sinovda
    # kuzatildi). Shuning uchun "ochish" va/yoki "qidirish" niyati aniq bo'lsa,
    # sayt nomi tanilmasa ham amalni BAJARAMIZ (aniqlanmasa — standart Google).
    if qidirish_bor and (ochish_bor or youtube_bor or google_bor):
        qidiruv = None
        qm2 = re.search(r"(.+?)\s+deb\s+(?:qidir\w*|izla\w*|top\w*)", m)
        if qm2:
            qidiruv = qm2.group(1)
        if not qidiruv:
            # "... qidirib ber(ing)" — ob'ekt fe'ldan OLDIN keladigan, "deb"siz shakl
            qm4 = re.search(r"^(.*?)\s*(?:qidir\w*|izla\w*|top\w*)\s+ber\w*\s*$", m)
            if qm4 and qm4.group(1).strip():
                qidiruv = qm4.group(1)
        if not qidiruv:
            # "qidir X" — ob'ekt fe'ldan KEYIN keladigan shakl
            qm = re.search(r"(?:qidir\w*|izla\w*|top\w*)\s*[:\-]?\s*(.+)$", m)
            if qm and qm.group(1).strip():
                qidiruv = qm.group(1)
        if not qidiruv:
            # "X qidir" — ob'ekt fe'ldan OLDIN, gap oxirida "qidir" bilan tugaydi
            qm3 = re.search(r"^(.*?)\s*(?:qidir\w*|izla\w*|top\w*)\s*$", m)
            if qm3 and qm3.group(1).strip():
                qidiruv = qm3.group(1)

        if qidiruv:
            qidiruv = _qidiruv_tozala(qidiruv)

        sayt_url = _SAYT_NOMLARI["youtube"] if youtube_bor else _SAYT_NOMLARI["google"]

        if qidiruv:
            url = sayt_url.format(q=urllib.parse.quote(qidiruv))
            _brauzer_ochish(url)
            return True, f"{qidiruv!r} bo'yicha qidirdim, natijalarni ochdim."
        else:
            _brauzer_ochish("https://www.google.com")
            return True, "Brauzerni ochdim."
    if "namoz" in m and ("vaqt" in m or "5 vaqt" in m or "besh vaqt" in m):
        shahar_m = re.search(r"(toshkent|samarqand|buxoro|andijon|namangan|farg'ona|fargona|nukus|qarshi|termiz|jizzax|guliston|navoiy|xiva|urganch|medina|makkah?|mekka)", m)
        shahar = shahar_m.group(1) if shahar_m else "Toshkent"
        try:
            return True, _namoz_vaqtlari(shahar)
        except Exception:
            return False, None
    return False, None


# --- Doimiy (persistent) Jarvis sessiyasi (E9-bosqich) ---
# Muammo: har bir /ask so'rovida YANGI Jarvis obyekti (demak, yangi Claude
# Agent SDK ulanishi) yaratish — hatto oddiy erkin savol uchun ham — bir necha
# soniyadan o'nlab soniyagacha vaqt olishi mumkin, chunki ulanishning o'zini
# o'rnatish sekin. Video-namunalardagi tezlikka yaqinlashish uchun server
# ishga tushganda BITTA Jarvis sessiyasi ochiladi va OCHIQ saqlanadi — har bir
# so'rov shu tayyor sessiyaga yuboriladi (faqat javob kutiladi, ulanish qayta
# o'rnatilmaydi). Bu jarvis_telegram.py'dan MUSTAQIL — alohida jarayon,
# alohida sessiya, faqat bitta marta ochilib ko'p marta ishlatiladi, xolos.
# Agar bu sessiya biron sababdan ochilmasa yoki xato bersa, _ask_jarvis_doimiy
# xato ko'taradi va chaqiruvchi (ask_route) avtomatik ravishda eski, har safar
# yangi obyekt yaratadigan usulga qaytadi — HUD hech qachon butunlay ishlamay
# qolmaydi.
_doimiy_loop = None
_doimiy_sessiya = None
_doimiy_xato = None
_doimiy_tayyor = threading.Event()


def _doimiy_oqim():
    global _doimiy_loop, _doimiy_sessiya, _doimiy_xato
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _doimiy_loop = loop

    async def _boot():
        global _doimiy_sessiya
        # roadmap #7: auto_approve O'RNIGA uning kuzatuvchi-o'ralgan versiyasi
        # (xatti-harakat bir xil, faqat sezgir amallar jurnalga qo'shiladi)
        ctx = Jarvis(log=True, confirm_fn=xavfsizlik_jurnali_bilan_auto_approve)
        _doimiy_sessiya = await ctx.__aenter__()

    try:
        loop.run_until_complete(_boot())
    except Exception as e:
        _doimiy_xato = e

    if _doimiy_sessiya is not None:
        _doimiy_tayyor.set()
        loop.run_forever()
    else:
        _doimiy_tayyor.set()


def _doimiy_sessiyani_boshlash():
    """Fon oqimida doimiy Jarvis sessiyasini ochadi. Bloklamaydi — server
    darhol ishga tushishda davom etadi, sessiya orqada tayyorlanadi (tayyor
    bo'lguncha so'rovlar avtomatik eski, sekinroq usulga tushib turadi)."""
    t = threading.Thread(target=_doimiy_oqim, daemon=True, name="jarvis-doimiy-sessiya")
    t.start()


def _ask_jarvis_doimiy(text: str, timeout_s: float) -> str:
    """Doimiy sessiya orqali so'rov yuboradi. Sessiya hali tayyor bo'lmasa
    yoki ishlamasa, xato ko'taradi — chaqiruvchi shunda eski (har safar yangi
    Jarvis obyekti yaratadigan) usulga qaytishi kerak."""
    if _doimiy_sessiya is None or _doimiy_loop is None:
        raise RuntimeError("doimiy Jarvis sessiyasi hali tayyor emas")
    fut = asyncio.run_coroutine_threadsafe(_doimiy_sessiya.ask(text), _doimiy_loop)
    return fut.result(timeout=timeout_s)


# ==== 2026-09-28 kechqurun — "Kamola/Instagram" voqeasidan keyingi tuzatish ====
# Voqea: panelda Kamolaga "instagramda ahvol qanday tekshir" deb yozilganda,
# panelda javob kelmadi, o'rniga uning Telegramiga uzun TEXNIK hisobot keldi.
# Sabab: bu savol jarvis_xodim_dispatch'ning HECH bir mavzusiga mos kelmagani
# uchun to'liq Bash huquqiga ega "doimiy" Jarvis sessiyasiga (jarvis_core.Jarvis)
# yuborilgan edi -- unga "hech kimga xabar yuborma" degan ANIQ TAQIQ berilmagan
# edi, shuning uchun AI "yordam berish" niyatida jarvis_bildirishnoma/Telegram
# Bot API kabi mavjud vositalardan foydalanib o'zi Azizbekka xabar yuborgan.
# Bundan tashqari javob USLUBI ham nazorat qilinmagan edi (uzun, texnik).
# jarvis_core.py'ning O'ZIGA HECH QANDAY tegilmaydi (loyiha an'anasi) -- tuzatish
# FAQAT shu yerdagi, AI'ga yuboriladigan PROMPT matniga qo'shiladi.
_AI_XAVFSIZLIK_VA_FORMAT = (
    "\n\nQAT'IY QOIDALAR (buzilsa jiddiy xato hisoblanadi):\n"
    "1) HECH QANDAY tashqi xabar/bildirishnoma YUBORMA -- Telegram, email yoki "
    "boshqa kanal orqali hech kimga (shu jumladan Azizbekning o'ziga ham) xabar "
    "yubormasin, hech qanday bildirishnoma/xabar skriptini ishga tushirma "
    "(masalan jarvis_bildirishnoma, telegram_xabar_yubor, Telegram Bot API, "
    "notify_owner va h.k.). Ma'lumot yig'ish uchun (masalan real holatni "
    "tekshirish) Bash/skript ishlatishing MUMKIN, lekin natijani hech kimga "
    "yubormasdan, faqat o'zing o'qib, shu javobning matni orqali qaytar.\n"
    "2) Javob QISQA bo'lsin: 1-shaxsda, \"Azizbek aka\" bilan boshlansin, "
    "3-5 gapdan oshmasin, texnik so'z (API, token, Buffer, status, log, fayl "
    "nomi) ishlatma -- muammo bo'lsa oddiy tilda ayt. Oxiri tabiiy taklif/"
    "keyingi qadam bilan tugasin.\n"
    "3) Agar qo'shimcha texnik/batafsil ma'lumot bermoqchi bo'lsang, uni "
    "YUQORIDAGI qisqa javobdan KEYIN, yangi qatorda ANIQ \"BATAFSIL:\" so'zi "
    "bilan boshlab yoz. Batafsil kerak bo'lmasa bu qismni UMUMAN yozma."
)

_BATAFSIL_BELGISI = re.compile(r"\n?\s*BATAFSIL\s*:\s*", re.IGNORECASE)


def _javobni_ajrat(raw: str):
    """AI javobidan QISQA qismni va (bo'lsa) 'BATAFSIL:' belgisidan keyingi
    qismini ajratadi. Qaytaradi: (qisqa_javob, batafsil_yoki_None)."""
    if not raw:
        return raw, None
    m = _BATAFSIL_BELGISI.search(raw)
    if not m:
        return raw.strip(), None
    qisqa = raw[:m.start()].strip()
    batafsil = raw[m.end():].strip()
    return (qisqa or raw.strip()), (batafsil or None)


# HUD orqali yuborilgan bitta so'rov shuncha soniyadan ortiq davom etsa,
# bekor qilinadi — HUD sahifasi abadiy "O'ylayapman..." holatida qolib
# ketmasin. (jarvis_core.Jarvis.ask()'ning o'zida ham 600s ichki timeout
# bor, lekin HUD uchun bu juda uzun.) Endi tezkor buyruqlar yuqoridagi
# qatlamda darhol bajarilgani uchun, bu yo'lga faqat murakkab/erkin
# so'rovlar tushadi — ularga ilgarigidan (75s) ko'ra ko'proq vaqt beramiz.
BRIDGE_TIMEOUT_S = 180

# E3-bosqich: /speak (Sardor, edge-tts) uchun ichki timeout. /ask'dan ancha
# qisqaroq — bu shunchaki ovoz o'qish, agar Microsoft'ning edge-tts xizmati
# sekinlashsa yoki javob bermasa, HUD abadiy kutib qolmasdan tezda mahalliy
# (brauzer) ovoziga qaytishi kerak.
SPEAK_TIMEOUT_S = 18
SPEAK_VOICE = "uz-UZ-SardorNeural"
# 2026-09-28: edge-tts vaqti-vaqti bilan 18s'da ham javob bermay qoladi (o'lchovda
# 4 tadan 2 tasi timeout bo'lgan). Endi 1 marta QISQAROQ matn + qisqaroq timeout
# bilan zaxira urinish qilinadi -- foydalanuvchi 2x to'liq timeout kutmasin.
SPEAK_RETRY_TIMEOUT_S = 8
SPEAK_QISQARTIRISH_BELGI = 80

# E4-bosqich: /transcribe (ovozni matnga aylantirish — Google STT + mahalliy Whisper zaxira)
# uchun ichki timeout. Butun oqim (ffmpeg konvertatsiya + Google so'rov + kerak bo'lsa Whisper)
# shu vaqt ichida tugashi kerak, aks holda HUD abadiy "aniqlanmoqda..." holatida qolib
# ketmasdan, brauzerning o'z (Web Speech API) natijasiga tezda qaytadi.
LISTEN_TIMEOUT_S = 25  # Whisper'ning sovuq start (birinchi chaqiruvda model yuklanishi)i ~18s'gacha
                       # cho'zilishi kuzatildi (sinovda) — Google STT ishlamay qolib Whisper'ga
                       # tushgan taqdirda ham yetarli vaqt qolishi uchun biroz kengroq qilindi.
WHISPER_MODEL_SIZE = "small"  # jarvis_telegram.py bilan bir xil — "medium" sinalgan, natija sekin va notog'ri chiqqan (2026-09-05)
WHISPER_MODELS_DIR = PARENT_DIR / "transkripsiya" / "modellar"  # jarvis_telegram.py bilan bir xil, allaqachon yuklab olingan modellar qayta ishlatiladi

PORT = 8090
# roadmap #5 (xavfsizlik): HUD frontend FAQAT shu manzilda ishlaydi
# (hud_frontend_server.py, 8080-port, 127.0.0.1) — CORS endi "*" emas,
# FAQAT shu origin'ga ruxsat beriladi.
FRONTEND_ORIGIN = "http://localhost:8080"

app = Flask(__name__)


# ==== roadmap #5 (2026-09-21) — token-asosli autentifikatsiya ====
# Har bir so'rov (OPTIONS preflight'dan tashqari — brauzer CORS preflight'da
# maxsus header yubormaydi, shuning uchun uni bloklasak asl so'rov HECH QACHON
# yuborilmaydi) "Authorization: Bearer <HUD_TOKEN>" header'iga ega bo'lishi
# SHART, aks holda 401 bilan rad etiladi. `index.html` (8080-portda ishlaydigan
# frontend) har bir fetch()ga shu header'ni AVTOMATIK qo'shadi (bir xil
# HUD_TOKEN, `hud_token.py`dan olingan). Boshqa hech qanday manba (masalan
# tarmoqdagi boshqa qurilma, yoki tokenni bilmagan skript) so'rov yubora
# olmaydi.
@app.before_request
def _token_tekshir():
    if request.method == "OPTIONS":
        return None  # CORS preflight — browser custom header yubormaydi, bloklamaymiz
    auth = request.headers.get("Authorization", "")
    berilgan = auth[7:] if auth.startswith("Bearer ") else ""
    if berilgan != HUD_TOKEN:
        return jsonify({"error": "Ruxsat yo'q — noto'g'ri yoki yo'q token."}), 401

# ==== "OXIRGI AMALLAR" paneli uchun — haqiqiy /ask so'rov-javoblar tarixi ====
# Oldin HUD'da 4 ta qattiq yozilgan (statik, hech qachon o'zgarmaydigan) qator
# bor edi. Endi har bir HAQIQIY /ask so'rovi shu ro'yxatga yoziladi (faqat
# xotirada — bridge qayta ishga tushsa tozalanadi, bu yetarli), frontend
# GET /amallar orqali oxirgi 15 tasini oladi.
import collections
import threading as _threading
from datetime import datetime as _datetime, timedelta as _timedelta

_AMALLAR_MAX = 15
_amallar_ro_yxati = collections.deque(maxlen=_AMALLAR_MAX)
_amallar_lock = _threading.Lock()


# 2026-09-28 (Azizbek buyrug'i, "HUD sekin/xato" shikoyati): har bir
# so'rovning HAR BOSQICHI (STT tizimi+soniya, Claude javob soniyasi, TTS
# soniyasi, natija) shu faylga yoziladi -- oldin bunday o'lchov UMUMAN
# yo'q edi, "sekin" degan taxmin bilan emas, ANIQ raqam bilan tekshirish
# uchun. Uch bosqich (transcribe/ask/speak) uchta ALOHIDA HTTP so'rovi --
# bitta umumiy jadvalga vaqt yaqinligiga qarab birlashtiriladi.
HUD_OLCHOV_FAYLI = BASE_DIR / "hud_olchov.jsonl"


def _hud_olchov_yoz(bosqich: str, **maydonlar) -> None:
    try:
        yozuv = {
            "vaqt": _datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bosqich": bosqich,
            **maydonlar,
        }
        with open(HUD_OLCHOV_FAYLI, "a", encoding="utf-8") as f:
            f.write(_json.dumps(yozuv, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _amal_qoshish(matn: str, status: str = "ok"):
    """So'rov matnini (qisqartirib) va statusini oxirgi-amallar ro'yxatiga qo'shadi."""
    qisqa = (matn or "").strip().replace("\n", " ")
    if len(qisqa) > 70:
        qisqa = qisqa[:67] + "..."
    yozuv = {
        "vaqt": _datetime.now().strftime("%H:%M"),
        "matn": qisqa or "(bo'sh so'rov)",
        "status": status,  # "ok" | "xato" | "timeout"
    }
    with _amallar_lock:
        _amallar_ro_yxati.appendleft(yozuv)


@app.route("/amallar", methods=["GET"])
def amallar_route():
    with _amallar_lock:
        return jsonify(list(_amallar_ro_yxati))


# ==== Pixel-ofis ("AI Xodimlarim"): Jarvis belgisi uchun REAL band/bo'sh ====
# 2026-09-22, ikkinchi bosqich: endi FAQAT shu bridge'ning o'z lock'i emas —
# `jarvis_holati_signal.py` orqali TELEGRAM BOTI bilan UMUMIY fayl-asosidagi
# signaldan o'qiydi (xuddi jarvis_bildirishnoma.py'dagi naqsh kabi — umumiy
# xotira/qulf emas, har bir jarayon o'ziga tegishli kichik faylga yozadi).
# `jarvis_telegram.py` (`handle`/`handle_file`) va shu bridge (pastda /ask
# ichida) har biri o'z so'rovi boshlanganda/tugaganda
# `band_belgila("telegram"|"bridge")` / `bosh_belgila(...)` chaqiradi —
# `biror_joyda_bandmi()` ikkalasidan istalgani band bo'lsa "band" qaytaradi.
# jarvis_core.py'ga HECH QANDAY o'zgartirish kiritilmagan (bu fayl xulosasi
# yuqorida ta'kidlangan invariantga mos — faqat chaqiruvchi fayllar
# o'zgartirilgan).
@app.route("/jarvis_holati", methods=["GET"])
def jarvis_holati_route():
    band = biror_joyda_bandmi()
    return jsonify({"holat": "band" if band else "bosh", "sessiya_tayyor": _doimiy_sessiya is not None})


# ==== Pixel-ofis — "AI Expert" belgisi uchun REAL band/bo'sh (2026-09-22) ====
# Jarvis'dagi bilan BIR XIL naqsh (yuqoridagi /jarvis_holati), lekin ATAYLAB
# ALOHIDA manba ("ai_expert") va ALOHIDA o'qish funksiyasi (`manba_bandmi`,
# `biror_joyda_bandmi` EMAS) — mijozlar/ai_expert_bot/bot.py o'z holatini
# jarvis_holati_signal.band_belgila("ai_expert")/bosh_belgila("ai_expert")
# bilan yozadi (fire-and-forget, botning asosiy ishiga ta'sir qilmaydi).
# Bu yangi manba asosiy Jarvis ("telegram"/"bridge") holatiga HECH QANDAY
# ta'sir qilmaydi — MA_LUM_MANBALAR ro'yxatiga qo'shilmagan.
@app.route("/ai_expert_holati", methods=["GET"])
def ai_expert_holati_route():
    band = manba_bandmi("ai_expert")
    return jsonify({"holat": "band" if band else "bosh"})


# ==== "TIZIM HOLATI" paneli uchun — haqiqiy CPU/Xotira (psutil) ====
# Oldin CPU/Xotira Math.random() bilan HAR 2.2s da to'qib chiqarilardi (kod
# ichida "hali haqiqiy tizim ma'lumoti emas" deb ochiq yozilgan edi). Endi
# psutil orqali WINDOWS'NING O'ZI (Task Manager bilan bir xil manba) haqiqiy
# qiymatini o'qiymiz.
import psutil

# psutil.cpu_percent()ning BIRINCHI chaqiruvi har doim 0.0 qaytaradi (solishtirish
# uchun boshlang'ich nuqta kerak) — server ishga tushganda bir marta "isitib"
# qo'yamiz, shunda HUD ochilgan ZAHOTI birinchi so'rov ham to'g'ri qiymat oladi.
psutil.cpu_percent(interval=None)


@app.route("/tizim", methods=["GET"])
def tizim_route():
    # interval=0.15 — qisqa (150ms) haqiqiy o'lchov oralig'i, Task Manager'dagi
    # "oxirgi bir necha soniya" o'rtachasiga yaqinroq to'g'ri natija beradi
    # (interval=None bo'lsa oldingi chaqiruvdan beri o'tgan random vaqtga bog'liq
    # bo'lib, notekis/chalkash qiymat chiqarishi mumkin edi).
    cpu = psutil.cpu_percent(interval=0.15)
    xotira = psutil.virtual_memory().percent
    return jsonify({"cpu": round(cpu, 1), "xotira": round(xotira, 1)})


# ==== "VAZIFALAR VA JADVAL" paneli uchun — haqiqiy xotira/vazifalar.md ====
# Oldin 4 ta qattiq yozilgan namunaviy qator bor edi ("Mijoz bilan uchrashuv"
# va h.k., hech qachon o'zgarmaydigan). Endi Jarvisning haqiqiy operatsion
# xotira faylidagi ("## Ochiq (faol) vazifalar" bo'limi, "- [ ]" bilan
# belgilangan, hali "- [x]" qilinmagan qatorlar) ro'yxat o'qiladi.
VAZIFALAR_FAYL = PARENT_DIR / "xotira" / "vazifalar.md"


def _vazifalarni_oqi(maks=8):
    """xotira/vazifalar.md dagi 'Ochiq (faol) vazifalar' bo'limidan hali
    bajarilmagan ('- [ ]') qatorlarni o'qib, har birining qisqa sarlavhasini
    (bold **...** qismi bo'lsa o'sha, aks holda qatorning o'zi qisqartirilib)
    ro'yxat qilib qaytaradi."""
    try:
        matn = VAZIFALAR_FAYL.read_text(encoding="utf-8")
    except Exception:
        return []

    qatorlar = matn.splitlines()
    boshlandimi = False
    natija = []
    for qator in qatorlar:
        if qator.strip().startswith("## "):
            # Faqat "Ochiq (faol) vazifalar" bo'limini o'qiymiz, undan keyingi
            # ("Texnik qarz", "Yaqinda yakunlangan" va h.k.) bo'limlarga tegmaymiz.
            boshlandimi = "Ochiq" in qator and "vazifalar" in qator
            continue
        if not boshlandimi:
            continue
        m = re.match(r"^-\s*\[\s\]\s*(.+)$", qator.strip())
        if not m:
            continue
        ichki = m.group(1)
        bold = re.search(r"\*\*(.+?)\*\*", ichki)
        if bold:
            sarlavha = bold.group(1)
        else:
            # Bold yo'q — "→" (loyiha havolasi) yoki qavs ochilishidan oldingi
            # qismini olamiz, bo'lmasa butun qatorni qisqartiramiz.
            sarlavha = ichki.split("→")[0].strip()
        sarlavha = sarlavha.strip(" :—-")
        if len(sarlavha) > 80:
            sarlavha = sarlavha[:77] + "..."
        if sarlavha:
            natija.append(sarlavha)
        if len(natija) >= maks:
            break
    return natija


@app.route("/vazifalar", methods=["GET"])
def vazifalar_route():
    return jsonify(_vazifalarni_oqi())


# ==== "XAVFSIZLIK JURNALI" paneli (roadmap #7, 2026-09-21) ====
# #1 ("OXIRGI AMALLAR")dan farqi: bu yerda HAR BIR /ask so'rov emas, faqat
# SEZGIR (yozish/o'zgartirish/o'chirish turidagi) vosita chaqiruvlari
# yoziladi — Gmail/Drive/Calendar/Canva'da YOZISH amallari, xavfli/
# o'zgartiruvchi Bash buyruqlari. Oddiy O'QISH (list/get/search/read) va
# xavfsiz Bash bu jurnalga umuman tushmaydi.
#
# MUHIM (arxitektura): `jarvis_core.py`ga HECH QANDAY o'zgartirish
# kiritilmagan. `Jarvis(confirm_fn=...)` allaqachon HAR bir vosita
# chaqiruvini shu funksiya orqali o'tkazadi (`jarvis_core.py:676`) — biz
# shunchaki `auto_approve`ni O'RAB OLAMIZ: avval sezgir-mi tekshiramiz,
# keyin AYNAN `auto_approve`ning o'zini chaqiramiz (xatti-harakat bir xil
# qoladi — xavfli Bash baribir `auto_approve` ICHIDA bloklanadi, biz faqat
# natijani KUZATAMIZ), natija (ruxsat/rad) bilan birga jurnalga yozamiz.
_XAVFSIZLIK_MAX = 30
_xavfsizlik_jurnali = collections.deque(maxlen=_XAVFSIZLIK_MAX)
_xavfsizlik_lock = _threading.Lock()

_GMAIL_YOZISH = {
    "send_message", "reply", "forward", "create_draft", "update_draft", "delete_draft",
    "label_message", "unlabel_message", "label_thread", "unlabel_thread",
    "mark_message_spam", "unmark_message_spam", "mark_thread_spam", "unmark_thread_spam",
    "trash_message", "trash_thread", "untrash_message", "untrash_thread",
    "update_message_labels", "apply_sensitive_message_label", "apply_sensitive_thread_label",
    "create_label", "delete_label", "update_label",
}
_DRIVE_YOZISH = {"create_file", "update_file", "copy_file", "share_file", "trash_file"}
_CALENDAR_YOZISH = {"create_event", "update_event", "delete_event", "respond_to_event"}
# Canva'da O'QISH turlari OZCHILIK — shuning uchun "aksincha" ro'yxat:
# shu ro'yxatda YO'Q har qanday Canva vositasi sezgir (yozuvchi) deb olinadi.
_CANVA_OQISH = {
    "search-designs", "search-folders", "search-brand-templates", "get-assets",
    "get-brand-template-dataset", "get-design-candidates", "get-design-dataset",
    "get-design-pages", "get-design-thumbnails", "get-export-formats", "list-brand-kits",
    "list-comments", "list-folder-items", "list-replies", "read-design", "help",
    "resolve-shortlink", "request-outline-review",
}
# Bash uchun XAVFLI_BUYRUQLAR (jarvis_core.py) bilan CHALKASHTIRMASLIK kerak —
# o'shalar to'liq BLOKLANADI (bajarilmaydi), shu sabab ularni "sezgir amal
# BAJARILDI" deb jurnalga yozish chalkash bo'lar edi (aslida rad etiladi —
# buni ham "holat" maydonida alohida ko'rsatamiz, quyida). Bu yerdagi naqsh
# — BAJARILISHI MUMKIN bo'lgan, lekin diqqat talab qiladigan (fayl/jarayon/
# tarmoq/registrni o'zgartiruvchi) buyruqlar uchun, kengroq.
_BASH_SEZGIR_NAQSH = re.compile(
    r"\b(rm|del|taskkill|Stop-Process|Remove-Item|git\s+push|git\s+reset|reg\s+\w+|"
    r"schtasks|icacls|chmod|netsh|shutdown|format|net\s+user|New-ScheduledTask|"
    r"DROP\s+|DELETE\s+FROM)\b",
    re.IGNORECASE,
)


def _sezgir_amalmi(tool_name: str, input_data: dict) -> str | None:
    """Vosita chaqiruvi SEZGIR (auditlanadigan) toifaga tushsa qisqa izoh
    qaytaradi, aks holda None. Faqat YOZISH/O'ZGARTIRISH/O'CHIRISH turidagi
    amallar — oddiy o'qish (list/get/search/read) sezgir EMAS."""
    if tool_name.startswith("mcp__claude_ai_Gmail__"):
        amal = tool_name.split("__")[-1]
        return f"Gmail: {amal}" if amal in _GMAIL_YOZISH else None
    if tool_name.startswith("mcp__claude_ai_Google_Drive__"):
        amal = tool_name.split("__")[-1]
        return f"Drive: {amal}" if amal in _DRIVE_YOZISH else None
    if tool_name.startswith("mcp__claude_ai_Google_Calendar__"):
        amal = tool_name.split("__")[-1]
        return f"Calendar: {amal}" if amal in _CALENDAR_YOZISH else None
    if tool_name.startswith("mcp__claude_ai_Canva__"):
        amal = tool_name.split("__")[-1]
        return None if amal in _CANVA_OQISH else f"Canva: {amal}"
    if tool_name == "Bash":
        cmd = (input_data or {}).get("command", "")
        m = _BASH_SEZGIR_NAQSH.search(cmd)
        return f"Bash ({m.group(1)}): {cmd[:70]}" if m else None
    return None


def _xavfsizlik_qoshish(izoh: str, holat: str):
    yozuv = {
        "vaqt": _datetime.now().strftime("%H:%M:%S"),
        "izoh": izoh,
        "holat": holat,  # "ruxsat_berildi" | "rad_etildi"
    }
    with _xavfsizlik_lock:
        _xavfsizlik_jurnali.appendleft(yozuv)


async def xavfsizlik_jurnali_bilan_auto_approve(tool_name, input_data, context):
    """`auto_approve`ning o'rab olingan versiyasi — bridge'dagi ikkala
    `Jarvis(confirm_fn=...)` chaqiruviga ham (`_boot()` va `_ask_jarvis()`)
    `auto_approve` O'RNIGA shu funksiya beriladi. Xatti-harakat bir xil
    qoladi (natijani o'zgartirmaydi, faqat kuzatib, sezgir bo'lsa jurnalga
    yozadi)."""
    izoh = _sezgir_amalmi(tool_name, input_data or {})
    natija = await auto_approve(tool_name, input_data, context)
    if izoh:
        holat = "rad_etildi" if isinstance(natija, PermissionResultDeny) else "ruxsat_berildi"
        _xavfsizlik_qoshish(izoh, holat)
    return natija


@app.route("/xavfsizlik", methods=["GET"])
def xavfsizlik_route():
    with _xavfsizlik_lock:
        return jsonify(list(_xavfsizlik_jurnali))


# ==== "BILDIRISHNOMA MARKAZI" (roadmap #9 MVP, 2026-09-21) ====
# Fon skriptlar (hozircha faqat `jarvis_proaktiv.py`) `jarvis_bildirishnoma.
# bildirishnoma_yoz()` orqali umumiy faylga yozadi — bridge BU YERDA FAQAT
# O'QIYDI (`bildirishnomalarni_oqi()`, o'zi hech qachon yozmaydi). Frontend
# oxirgi ko'rgan sonini (localStorage/JS xotirasida) solishtirib, FAQAT
# yangi yozuvlarni toast sifatida ko'rsatadi.
@app.route("/bildirishnomalar", methods=["GET"])
def bildirishnomalar_route():
    return jsonify(jarvis_bildirishnoma.bildirishnomalarni_oqi())


# ==== "JARAYONLAR HOLATI" paneli uchun — fon xizmatlarning REAL onlayn/o'chiq
# holati (psutil bilan jarayon ro'yxatidan qidirish + mahalliy portlarga ulanib
# ko'rish, xuddi bugun Get-CimInstance/netstat bilan qo'lda qilinganidek, lekin
# endi avtomatik va HUD'da ko'rinadigan qilib). ====
import socket as _socket


def _port_ochiqmi(port, host="127.0.0.1", timeout=0.3):
    try:
        with _socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _jarayon_cmdlinelari():
    """Barcha jarayonlarning cmdline satrlarini (kichik harfda, bitta satrga
    birlashtirilgan) BIR MARTA yig'ib qaytaradi — har bir xizmat uchun
    process_iter()ni qayta-qayta chaqirmaslik uchun (tezroq)."""
    natija = []
    try:
        for p in psutil.process_iter(["cmdline"]):
            try:
                cmdline = p.info.get("cmdline") or []
                natija.append(" ".join(cmdline).lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return natija


# Har bir xizmat: "jarayon" turi -- cmdline'da shu matn bo'lsa ONLAYN;
# "port" turi -- shu portga mahalliy ulanish o'rnatilsa ONLAYN;
# "log_yangi" turi -- shu log fayli oxirgi N soniya ichida yangilangan
# bo'lsa ONLAYN (Task Scheduler orqali PERIODIK ishlaydigan, doimiy
# jarayon BO'LMAGAN xizmatlar uchun -- masalan watchdog har ~5 daqiqada
# bir marta ishga tushib tugaydi, shuning uchun "jarayon" qidiruvi doim
# OFFLAYN ko'rsatardi).
JARAYONLAR_RO_YXATI = [
    {"nom": "Jarvis (asosiy bot)", "turi": "jarayon", "qidiruv": "jarvis_fon.py"},
    # 2026-09-28: haqiqiy watchdog `jarvis_watchdog.py` (Task Scheduler "Jarvis
    # Watchdog", ~5 daqiqada bir ishlaydi) -- eski "watchdog_fon.py" jarayon-
    # qidiruvi DOIM O'CHIQ ko'rsatardi, chunki bunday fayl umuman mavjud emas edi.
    {"nom": "Jarvis Watchdog", "turi": "log_yangi",
     "fayl": str(BASE_DIR.parent / "watchdog_jarvis.log"), "max_soniya": 900},
    {"nom": "AI Javob Bridge", "turi": "jarayon", "qidiruv": "ai_javob_bridge.py"},
    # 2026-09-28 (Azizbek buyrug'i): Azizbekning shaxsiy Telegram akkaunti
    # (userbot, Telethon) orqali kiruvchi DM'larni kuzatuvchi jarayon --
    # "jarayon" turi bo'lsa ham bo'lardi (userbot_fon.py), lekin heartbeat
    # fayli "tirik-lekin-o'lik" holatni ham qamrab oladi (masalan 2026-09-28
    # ertalab: jarayon ishlagan, lekin Telegram bilan aloqa uzilgan edi).
    {"nom": "Userbot Monitor (shaxsiy Telegram)", "turi": "log_yangi",
     "fayl": str(BASE_DIR.parent / "userbot" / "heartbeat_userbot.json"), "max_soniya": 900},
    {"nom": "HUD Bridge", "turi": "shu_bridge"},  # javob berayotgani = onlayn ekanining o'zi
    {"nom": "HUD Frontend (8080)", "turi": "port", "port": 8080},
    {"nom": "Oquv Markaz Server", "turi": "port", "port": 6070},
    {"nom": "JetCafe Restoran Server", "turi": "port", "port": 4000},
]


def _log_yaqinda_yangilanganmi(fayl: str, max_soniya: int) -> bool:
    try:
        p = Path(fayl)
        if not p.exists():
            return False
        return (_time.time() - p.stat().st_mtime) <= max_soniya
    except Exception:
        return False


@app.route("/jarayonlar", methods=["GET"])
def jarayonlar_route():
    cmdlinelari = None  # kerak bo'lgandagina (kamida bitta "jarayon" turi bo'lsa) yig'iladi
    natija = []
    for j in JARAYONLAR_RO_YXATI:
        if j["turi"] == "shu_bridge":
            onlayn = True
        elif j["turi"] == "port":
            onlayn = _port_ochiqmi(j["port"])
        elif j["turi"] == "log_yangi":
            onlayn = _log_yaqinda_yangilanganmi(j["fayl"], j["max_soniya"])
        else:
            if cmdlinelari is None:
                cmdlinelari = _jarayon_cmdlinelari()
            onlayn = any(j["qidiruv"] in c for c in cmdlinelari)
        natija.append({"nom": j["nom"], "onlayn": onlayn})
    return jsonify(natija)


# roadmap #5 (2026-09-21) + pixel-ofis Jarvis-holati (2026-09-22): ruxsat
# etilgan originlar RO'YXATI. "null" — brauzer file:// orqali ochilgan
# sahifalar uchun Origin sifatida yuboradigan qiymat (masalan
# kiruvchi/ai_ofis_pixel.html, u hech qachon HTTP server orqali emas,
# to'g'ridan-to'g'ri fayl sifatida ochiladi). Bu asosiy xavfsizlik chegarasi
# EMAS — asosiy himoya HUD_TOKEN (Authorization: Bearer) va 127.0.0.1 bind —
# CORS faqat "boshqa REMOTE sayt brauzeringiz orqali bu API'ga sezmasdan
# so'rov yubormasin" degan qo'shimcha qatlam. "null" qo'shish bu tahdidni
# OCHMAYDI: uzoqdagi zararli sayt hech qachon Origin:null bilan kelmaydi,
# faqat sizning kompyuteringizdagi lokal fayl shunday keladi.
_RUXSAT_ETILGAN_ORIGINLAR = {FRONTEND_ORIGIN, "null"}


@app.after_request
def add_cors_headers(resp):
    kelgan_origin = request.headers.get("Origin", "")
    if kelgan_origin in _RUXSAT_ETILGAN_ORIGINLAR:
        resp.headers["Access-Control-Allow-Origin"] = kelgan_origin
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


async def _ask_jarvis(text: str) -> str:
    """Yangi, alohida Jarvis obyekti yaratadi, javob oladi, yopadi."""
    # roadmap #7: shu yerda ham kuzatuvchi-o'ralgan versiya (izchillik uchun —
    # bu zaxira yo'l, doimiy sessiya ishlamay qolganda ishlatiladi).
    async with Jarvis(log=True, confirm_fn=xavfsizlik_jurnali_bilan_auto_approve) as j:
        return await j.ask(text)


@app.route("/ask", methods=["POST", "OPTIONS"])
def ask_route():
    if request.method == "OPTIONS":
        # CORS preflight so'rovi — hech narsa bajarmasdan bo'sh javob qaytaramiz
        return ("", 204)

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text maydoni bo'sh bo'lishi mumkin emas"}), 400

    # STT talaffuz xatolarini tuzatamiz (jariz->jarvis, xromno->chrome'ni va h.k.)
    text = _sst_tuzat(text)

    # "X ga ... deb yoz" -- shaxsiy Telegram (userbot) orqali yuborish,
    # tasdiq bilan (2026-09-28). AI/Bash'ga UMUMAN bormaydi -- alohida,
    # nazorat qilinadigan yo'l (5 soniya kutish + bekor + kunlik limit + log).
    try:
        shaxsiy_natija = _shaxsiy_buyruq_ishla(text)
    except Exception:
        shaxsiy_natija = {"boshqa": True}
    if not shaxsiy_natija.get("boshqa"):
        _amal_qoshish(text, "ok")
        javob = {"answer": shaxsiy_natija.get("javob", "")}
        if shaxsiy_natija.get("shaxsiy_yozish"):
            javob["shaxsiy_yozish"] = shaxsiy_natija["shaxsiy_yozish"]
        return jsonify(javob)

    # Tezkor buyruq qatlami — mos kelsa, jarvis_core'ga umuman murojaat qilmasdan
    # darhol bajaramiz va javob qaytaramiz (demo tezligi uchun kritik).
    try:
        bajarildimi, tez_javob = _tezkor_buyruq(text)
    except Exception:
        bajarildimi, tez_javob = False, None
    if bajarildimi:
        _amal_qoshish(text, "ok")
        return jsonify({"answer": tez_javob})

    band_belgila("bridge")  # pixel-ofis: shu bridge orqali real so'rov ishlay boshladi
    _t_boshi = _time.monotonic()
    try:
        try:
            # Avval tezroq yo'l — doimiy, allaqachon ochiq Jarvis sessiyasi.
            answer = _ask_jarvis_doimiy(text, BRIDGE_TIMEOUT_S)
            _yol = "doimiy"
        except concurrent.futures.TimeoutError:
            _amal_qoshish(text, "timeout")
            _hud_olchov_yoz("claude", matn=text, soniya=round(_time.monotonic() - _t_boshi, 1), yol="doimiy", natija="timeout")
            return jsonify({
                "answer": f"Kechirasiz, {BRIDGE_TIMEOUT_S} soniyada javob kelmadi — bekor qildim. "
                          "Iltimos savolni qisqaroq qilib qayta yuboring."
            }), 504
        except Exception as e1:
            # Doimiy sessiya hali tayyor emas yoki xato berdi — eski, har safar
            # yangi Jarvis obyekti yaratadigan (sekinroq, lekin sinalgan) usulga
            # qaytamiz, HUD hech qachon butunlay ishlamay qolmasin.
            _hud_olchov_yoz("claude_doimiy_xato", matn=text, xato=str(e1))
            try:
                answer = asyncio.run(asyncio.wait_for(_ask_jarvis(text), timeout=BRIDGE_TIMEOUT_S))
                _yol = "eski"
            except asyncio.TimeoutError:
                _amal_qoshish(text, "timeout")
                _hud_olchov_yoz("claude", matn=text, soniya=round(_time.monotonic() - _t_boshi, 1), yol="eski", natija="timeout")
                return jsonify({
                    "answer": f"Kechirasiz, {BRIDGE_TIMEOUT_S} soniyada javob kelmadi — bekor qildim. "
                              "Iltimos savolni qisqaroq qilib qayta yuboring."
                }), 504
            except Exception as e2:
                # Kutilmagan xato bo'lsa ham HUD sahifasi hech qachon abadiy kutib qolmasin —
                # aniq xato matni bilan javob qaytaramiz.
                _amal_qoshish(text, "xato")
                _hud_olchov_yoz("claude", matn=text, soniya=round(_time.monotonic() - _t_boshi, 1), yol="eski", natija="xato", xato=str(e2))
                return jsonify({"error": f"Ichki xato: {e2}"}), 500
    finally:
        bosh_belgila("bridge")

    _amal_qoshish(text, "ok")
    _hud_olchov_yoz("claude", matn=text, soniya=round(_time.monotonic() - _t_boshi, 1), yol=_yol, natija="ok")
    return jsonify({"answer": answer})


# ==== E3-bosqich: /speak — matnni Sardor (edge-tts) ovoziga aylantiradi ====
# ovozga_aylantir.py'dagi bilan bir xil kutubxona/ovoz ishlatiladi, lekin bu
# yerda Telegram uchun kerak bo'ladigan OGG/ffmpeg konvertatsiyasi yo'q —
# to'g'ridan-to'g'ri edge-tts'ning o'zi beradigan MP3 audio qaytariladi,
# chunki brauzer MP3'ni to'g'ridan-to'g'ri ijro eta oladi.
def _tts_qisqartir(text: str, max_belgi: int = SPEAK_QISQARTIRISH_BELGI) -> str:
    """Timeout bo'lgach qayta urinish uchun matnni qisqartiradi -- so'z
    o'rtasida kesmaslikka harakat qiladi."""
    text = (text or "").strip()
    if len(text) <= max_belgi:
        return text
    qisqa = text[:max_belgi]
    oxirgi_bosh = qisqa.rfind(" ")
    if oxirgi_bosh > max_belgi * 0.5:
        qisqa = qisqa[:oxirgi_bosh]
    return qisqa.rstrip(" ,.;:") + "..."


async def _tts_mp3_bytes(text: str) -> bytes:
    """Berilgan matnni edge-tts orqali MP3 baytlarga aylantiradi (vaqtinchalik faylga yozib, o'qib, o'chiradi)."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_yol = tmp.name
    try:
        communicate = edge_tts.Communicate(text, SPEAK_VOICE)
        await communicate.save(mp3_yol)
        with open(mp3_yol, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(mp3_yol):
            os.remove(mp3_yol)


@app.route("/speak", methods=["POST", "OPTIONS"])
def speak_route():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text maydoni bo'sh bo'lishi mumkin emas"}), 400

    _t_boshi = _time.monotonic()
    try:
        audio_bytes = asyncio.run(asyncio.wait_for(_tts_mp3_bytes(text), timeout=SPEAK_TIMEOUT_S))
    except asyncio.TimeoutError:
        # 2026-09-28: birinchi urinish (to'liq matn, 18s) timeout bo'ldi --
        # 1 marta QISQAROQ matn + qisqaroq timeout bilan zaxira urinish.
        qisqa_matn = _tts_qisqartir(text)
        try:
            audio_bytes = asyncio.run(asyncio.wait_for(_tts_mp3_bytes(qisqa_matn), timeout=SPEAK_RETRY_TIMEOUT_S))
            _hud_olchov_yoz(
                "tts", uzunlik=len(text), soniya=round(_time.monotonic() - _t_boshi, 1),
                natija="ok_qayta_urinishda", qisqartirildi=len(text) != len(qisqa_matn),
            )
            return Response(audio_bytes, mimetype="audio/mpeg")
        except asyncio.TimeoutError:
            _hud_olchov_yoz(
                "tts", uzunlik=len(text), soniya=round(_time.monotonic() - _t_boshi, 1),
                natija="timeout_ikkala_urinish", xato=f"{SPEAK_TIMEOUT_S}s (to'liq) + {SPEAK_RETRY_TIMEOUT_S}s (qisqartirilgan) ikkalasi ham timeout",
            )
            return jsonify({"error": f"{SPEAK_TIMEOUT_S}+{SPEAK_RETRY_TIMEOUT_S} soniyada ovoz tayyor bo'lmadi (2 urinish)"}), 504
        except Exception as e2:
            _hud_olchov_yoz(
                "tts", uzunlik=len(text), soniya=round(_time.monotonic() - _t_boshi, 1),
                natija="xato_qayta_urinishda", xato=str(e2),
            )
            return jsonify({"error": f"Ovoz yasashda xato (qayta urinishda): {e2}"}), 500
    except Exception as e:
        # HUD'ning JS tomoni bu xatoni ko'rib, mahalliy (brauzer) ovoziga avtomatik qaytadi —
        # shuning uchun bu yerda batafsil xato qaytarsak ham HUD buzilmaydi.
        _hud_olchov_yoz("tts", uzunlik=len(text), soniya=round(_time.monotonic() - _t_boshi, 1), natija="xato", xato=str(e))
        return jsonify({"error": f"Ovoz yasashda xato: {e}"}), 500

    if not audio_bytes:
        _hud_olchov_yoz("tts", uzunlik=len(text), soniya=round(_time.monotonic() - _t_boshi, 1), natija="bosh")
        return jsonify({"error": "Ovoz yaratilmadi (bo'sh natija)"}), 500

    _hud_olchov_yoz("tts", uzunlik=len(text), soniya=round(_time.monotonic() - _t_boshi, 1), natija="ok")
    return Response(audio_bytes, mimetype="audio/mpeg")


# ==== E4-bosqich: /transcribe — brauzerdan yozib olingan audioni aniqroq matnga aylantiradi ====
# Sabab: brauzerning o'z SpeechRecognition'i (index.html'dagi jonli/interim matn uchun
# ishlatiladi) o'zbekcha nutqni ko'p hollarda chalkash/noto'g'ri tanib olayotgani kuzatildi
# (masalan Azizbek yuborgan skrinshotda: "Hop jarvis qara menga chad ipini brauzer
# brauzerdan ochib berdi" — asl gap butunlay boshqa bo'lgan). Shuning uchun mikrofon
# o'chirilganda to'liq yozilgan audio shu yerga yuborilib, jarvis_telegram.py'da ovozli
# xabarlar uchun ALLAQACHON SINALGAN va yaxshi ishlagan usul bilan qayta tanib olinadi:
# 1) Google STT (bepul, tez, ~2s, internet talab qiladi) — asosiy yo'l
# 2) topilmasa/xato bo'lsa — mahalliy Whisper "small" (internetsiz ham ishlaydi, sekinroq)
_whisper_model = None


def _whisper_yukla():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE, device="cpu", compute_type="int8",
            download_root=str(WHISPER_MODELS_DIR),
        )
    return _whisper_model


def _whisper_bilan(audio_yol: str) -> str:
    """Til ATAYLAB 'uz'ga qattiq belgilangan — avtomatik til aniqlash ba'zan noto'g'ri
    tilni tanlab, butunlay tushunarsiz natija berishi mumkin (jarvis_telegram.py'dagi
    bilan bir xil sabab/qaror)."""
    model = _whisper_yukla()
    segments, _info = model.transcribe(audio_yol, language="uz", beam_size=5)
    return " ".join(s.text.strip() for s in segments).strip()


def _google_bilan(wav_yol: str) -> str:
    r = sr.Recognizer()
    with sr.AudioFile(wav_yol) as source:
        audio = r.record(source)
    return r.recognize_google(audio, language="uz-UZ").strip()


def _audio_dan_matn(kirish_yol: str, wav_yol: str) -> str:
    """Brauzerdan kelgan audio (odatda webm/opus) faylni matnga aylantiradi."""
    matn, _tizim, _s = _audio_dan_matn_olchov_bilan(kirish_yol, wav_yol)
    return matn


def _audio_dan_matn_olchov_bilan(kirish_yol: str, wav_yol: str):
    """`_audio_dan_matn` bilan BIR XIL, lekin qaysi tizim (google/whisper/
    xato) ishlatilgani va necha soniya ketganini ham qaytaradi -- 2026-09-28,
    "HUD sekin/xato" o'lchovi uchun."""
    # 1) ffmpeg orqali 16kHz mono WAV'ga o'giramiz (Google STT uchun kerak)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", kirish_yol, "-ar", "16000", "-ac", "1", wav_yol],
            check=True, capture_output=True,
        )
    except Exception:
        wav_yol = None  # konvertatsiya muvaffaqiyatsiz bo'lsa, Whisper asl faylni sinab ko'radi

    # 2) Google STT — asosiy yo'l
    if wav_yol:
        _t0 = _time.monotonic()
        try:
            matn = _google_bilan(wav_yol)
            if matn:
                return matn, "google", round(_time.monotonic() - _t0, 1)
        except Exception:
            pass

    # 3) Whisper — zaxira yo'l
    _t1 = _time.monotonic()
    try:
        matn = _whisper_bilan(wav_yol or kirish_yol)
        return matn, "whisper", round(_time.monotonic() - _t1, 1)
    except Exception as e:
        return "", f"xato: {e}", round(_time.monotonic() - _t1, 1)


@app.route("/transcribe", methods=["POST", "OPTIONS"])
def transcribe_route():
    if request.method == "OPTIONS":
        return ("", 204)

    audio_bytes = request.get_data()
    if not audio_bytes:
        return jsonify({"error": "audio ma'lumoti bo'sh"}), 400

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        kirish_yol = tmp.name
        tmp.write(audio_bytes)
    wav_yol = kirish_yol + ".wav"

    _t_boshi = _time.monotonic()
    try:
        matn, tizim, tizim_s = asyncio.run(asyncio.wait_for(
            asyncio.to_thread(_audio_dan_matn_olchov_bilan, kirish_yol, wav_yol),
            timeout=LISTEN_TIMEOUT_S,
        ))
    except asyncio.TimeoutError:
        _hud_olchov_yoz("stt", tizim="timeout", soniya=round(_time.monotonic() - _t_boshi, 1), matn=None, xato=f"{LISTEN_TIMEOUT_S}s timeout")
        return jsonify({"error": f"{LISTEN_TIMEOUT_S} soniyada ovoz aniqlanmadi"}), 504
    except Exception as e:
        # HUD'ning JS tomoni bu xatoni ko'rib, brauzerning o'z (Web Speech API) natijasiga
        # avtomatik qaytadi — shuning uchun bu yerda batafsil xato qaytarsak ham HUD buzilmaydi.
        _hud_olchov_yoz("stt", tizim="xato", soniya=round(_time.monotonic() - _t_boshi, 1), matn=None, xato=str(e))
        return jsonify({"error": f"Ovozni aniqlashda xato: {e}"}), 500
    finally:
        for p in (kirish_yol, wav_yol):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    matn = _sst_tuzat(matn)
    _hud_olchov_yoz("stt", tizim=tizim, soniya=tizim_s, matn=matn)
    return jsonify({"text": matn})


# ==== "JAMOA" paneli (Jarvis OS 5-bosqich, 2026-09-27) ====
# GET /jamoa — har bir "AI xodim"ning real holati (jarvis_jamoa_data.py orqali,
# Telegram'dagi "jamoa" buyrug'i bilan BIR XIL umumiy funksiyalar) + "bugun
# nima qilindi" lentasi. Bu yerga QO'SHIMCHA — bridge o'zining topshiriq
# navbatidagi band/kutmoqda holatini ham har bir kartaga ustiga qo'yadi.
import uuid as _uuid

_JAMOA_AMALLAR_MAX = 20
_jamoa_amallar = collections.deque(maxlen=_JAMOA_AMALLAR_MAX)
_jamoa_amallar_lock = _threading.Lock()


def _jamoa_amal_qoshish(agent_id: str, matn: str):
    with _jamoa_amallar_lock:
        _jamoa_amallar.appendleft({
            "vaqt": _datetime.now().strftime("%H:%M"),
            "agent": agent_id,
            "matn": matn[:120],
        })


# Topshiriqlar navbati — xotirada saqlanadi (bridge qayta ishga tushsa
# tozalanadi, bu yetarli — tarix Telegram'da va HUD lentasida qoladi).
_topshiriqlar: dict[str, dict] = {}
_topshiriqlar_lock = _threading.Lock()
JAMOA_TASK_TIMEOUT_S = 180
JAMOA_SAVOL_TIMEOUT_S = 150  # "ismga murojaat" erkin savoli — AI yo'liga tushsa
JAMOA_MAJLIS_TIMEOUT_S = 150  # jonli "Majlis" — AI bitta so'rovda butun majlisni yozadi

# Klassifikatsiya: matnda YOZISH/O'ZGARTIRISH/YUBORISH fe'llari bo'lsa —
# xavfsizlik uchun HAR DOIM tasdiq talab qilinadi (O'QISH so'zlari bo'lsa ham).
# Faqat aniq O'QISH/TEKSHIRISH so'zlari (va YOZISH so'zi YO'Q) bo'lsagina
# avtomatik bajariladi. Noaniq holatda — xavfsiz tomonga (tasdiq talab qilinadi).
_YOZISH_KALIT = re.compile(
    r"\b(yoz\w*|yubor\w*|jo'nat\w*|o'zgart\w*|yangila\w*|yarat\w*|qo'sh\w*|"
    r"o'chir\w*|tahrir\w*|tuzat\w*|sozla\w*|push\w*|deploy\w*|commit\w*|"
    r"reply\w*|joyla\w*|email\w*|to'la\w*|buyurtma\w*|sotib\s*ol\w*|"
    r"restart\w*|o'rnat\w*|ulash\w*|bekor\s*qil\w*)\b",
    re.IGNORECASE,
)
_OQISH_KALIT = re.compile(
    r"\b(ko'rsat\w*|tekshir\w*|hisobla\w*|hisobot\w*|ro'yxat\w*|qancha\w*|"
    r"nechta\w*|holat\w*|qanday\w*|top\w*|qidir\w*|o'qi\w*|aniqla\w*|"
    r"solishtir\w*|tahlil\w*|kim\w*)\b",
    re.IGNORECASE,
)
# 2026-09-29 (Azizbek xato-tuzatishi, band 2b): savol-belgisi/so'roq so'zlari --
# YOZISH fe'li YO'Q bo'lsa bular "oqish" (darhol javob, tasdiqsiz) deb
# hisoblanadi. Masalan: "...qanaqa g'oya bera olasan" -- YOZISH fe'li yo'q,
# shuning uchun savol.
_SAVOL_KALIT = re.compile(
    r"\?|-mi\b|mikan\b|"
    r"\bqanaqa\w*|\bqanday\w*|\bqaysi\w*|\bnima\w*|\bnega\w*|\bqancha\w*|"
    r"g'oya\w*|maslahat\w*|fikr\w*|"
    r"bera\s*olasan\w*|aytib\s*ber\w*|tushuntir\w*",
    re.IGNORECASE,
)
# 2026-09-29 (Azizbek xato-tuzatishi, band 2a): o'zbekcha matnlarda apostrof
# ko'p xil belgi bilan yoziladi (klaviatura/STT/qo'lda terish farqi) --
# regex tekshiruvidan OLDIN barchasini oddiy ' ga normallashtiramiz, aks
# holda "bo`yicha"/"o'zgartir" kabi so'zlar YOZISH/OQISH regexlariga
# tushmay qolardi.
_APOSTROF_XARITASI = str.maketrans({
    "‘": "'",  # ‘
    "’": "'",  # ’
    "ʻ": "'",  # ʻ
    "ʼ": "'",  # ʼ
    "`": "'",
})


def _apostrof_normallashtir(matn: str) -> str:
    return (matn or "").translate(_APOSTROF_XARITASI)


def _topshiriq_turi(matn: str) -> str:
    matn = _apostrof_normallashtir(matn)
    if _YOZISH_KALIT.search(matn):
        return "yozish"
    if _SAVOL_KALIT.search(matn) or _OQISH_KALIT.search(matn):
        return "oqish"
    return "yozish"  # noaniq -- xavfsiz tomonga


def _topshiriq_bajar(task_id: str):
    with _topshiriqlar_lock:
        task = _topshiriqlar.get(task_id)
        if not task:
            return
        task["holat"] = "bajarilmoqda"
        xodim_id = task["xodim"]
        xodim_nomi = jarvis_jamoa_data.XODIMLAR.get(xodim_id, {}).get("name", xodim_id)
        matn = task["matn"]

    _jamoa_amal_qoshish(xodim_id, f"topshiriq bajarilmoqda: \"{matn[:70]}\"")
    _boshlandi = _time.monotonic()  # 2026-09-28, band 3 -- kunlik hisobot uchun davomiylik

    # 2026-09-28: avval domen-dispatch (tez, real ma'lumot, AI kerak emas) --
    # "har kim o'z sohasida" qoidasi topshiriqlar uchun ham amal qiladi.
    javob = None
    batafsil = None
    xato = None
    manba = "ai"
    try:
        mos = jarvis_xodim_dispatch.aniqla(matn)
        if mos:
            _egasi_id, handler = mos
            natija = handler(matn)
            # 2026-09-28 tuzatish: "natija" ustunida endi QISQA (ovoz uslubidagi)
            # javob ko'rinadi, to'liq texnik matn (ekran) "Batafsil" ichida qoladi
            # -- oldin bu yerda to'g'ridan-to'g'ri natija["ekran"] (uzun, texnik)
            # ishlatilar edi.
            javob = natija["ovoz"]
            if natija.get("ekran") and natija["ekran"] != javob:
                batafsil = natija["ekran"]
            manba = "xato-tayyor" if natija.get("xato") else "tayyor"
        elif jarvis_xodim_dispatch.malumot_yoqmi(matn):
            javob = "Bu ma'lumot menda yo'q — hech qanday manbada topmadim."
            manba = "malumot_yoq"
        else:
            savol = (
                f"[{xodim_nomi} rolida, faqat REAL ma'lumotga asoslanib javob ber. "
                f"Aniq ma'lumot topolmasang \"bu ma'lumot menda yo'q\" de, hech narsa to'qima. "
                f"MUHIM: agar bu topshiriq birovga (Telegram/shaxsiy xabar, tashqi kontakt va h.k.) "
                f"XABAR YUBORISHNI so'rasa -- SEN buni O'ZING YUBORMAYSAN va HECH QACHON \"yubordim\"/"
                f"\"yuborildi\" DEMAYSIN. Buning o'rniga aniq shuni ayt: \"Bu haqiqiy yuborish zanjiri "
                f"orqali (\\\"/send <ism> <matn>\\\" yoki \\\"<ism>ga xabar: <matn>\\\") amalga oshirilishi kerak, men bevosita yubora "
                f"olmayman.\""
                f"{jarvis_xodim_qoidalar.ai_prompt_uchun_qoshimcha(xodim_id)}]"
                f"{_AI_XAVFSIZLIK_VA_FORMAT}\n\nTopshiriq: {matn}"
            )
            try:
                javob_xom = _ask_jarvis_doimiy(savol, JAMOA_TASK_TIMEOUT_S)
            except Exception:
                javob_xom = asyncio.run(asyncio.wait_for(_ask_jarvis(savol), timeout=JAMOA_TASK_TIMEOUT_S))
            javob, batafsil = _javobni_ajrat(javob_xom)
            # 2026-09-29 (Azizbek tuzatishi, band B): AI "yubordim"/"yuborildi"
            # desa-yu, HAQIQATDA hech narsa yuborilmagan bo'lsa (chunki bu
            # yo'l xabar yubormaydi, faqat matn qaytaradi) -- bu XAVFLI,
            # ADASHTIRUVCHI natija. Post-tekshiruv: agar shu so'zlar bo'lsa
            # VA `shaxsiy_yuborilganlar.jsonl`da so'nggi 10s ichida yangi
            # yozuv PAYDO BO'LMAGAN bo'lsa (ya'ni haqiqiy yuborish sodir
            # bo'lmagan), natija aniq "[TASDIQLANMAGAN]" bilan belgilanadi.
            if javob and re.search(r"\byubor(di|ildi|dim)\b", javob, re.IGNORECASE):
                if not _shaxsiy_yaqinda_yuborilganmi(soniya_ichida=10):
                    javob = "[TASDIQLANMAGAN -- haqiqiy yuborish sodir bo'lmagan bo'lishi mumkin] " + javob
    except Exception as e:
        xato = str(e)

    with _topshiriqlar_lock:
        task["holat"] = "xato" if xato else "tayyor"
        task["natija"] = xato or javob
        task["batafsil"] = None if xato else batafsil
        task["manba"] = manba

    _davomiyligi = _time.monotonic() - _boshlandi
    jarvis_topshiriq_tarixi.yozuv_qoshish(
        xodim=xodim_id, matn=matn, holat=("xato" if xato else "tayyor"),
        natija=(xato or javob), davomiyligi_s=_davomiyligi,
        sabab=xato, manba=manba,
    )

    # 2026-09-28 kechqurun tuzatish (Kamola/Instagram voqeasi): Azizbekning
    # ANIQ qoidasi -- "qayerda so'ralsa, o'sha yerda javob". Panel (bu funksiya)
    # orqali kelgan topshiriqning natijasi ENDI HAR DOIM Telegramga
    # yuborilmaydi -- panel /jamoa GET orqali natijani o'zi ko'rsatadi. Faqat
    # 2 daqiqadan UZOQ cho'zilgan topshiriqlar uchun (panel ochiq/yopiqligini
    # aniq bilib bo'lmagani uchun amaliy o'lchov) Telegramga BITTA QISQA xabar
    # yuboriladi -- aynan shu "har doim yuborish" xatti-harakati bugungi
    # voqeaga sabab bo'lgan edi. Xato holati xavfsizlik uchun HAR DOIM
    # xabar qilinadi (tezda muvaffaqiyatli tugagan javoblarni Telegramga
    # yubormaslik ASOSIY talab, xatolarni emas).
    _TELEGRAM_XABAR_CHEGARASI_S = 120
    if xato:
        _jamoa_amal_qoshish(xodim_id, f"topshiriq xato berdi: {xato[:80]}")
        telegram_xabar_yubor(f"⚠️ {xodim_nomi} — topshiriqda xato: {matn[:60]}\n\n{xato[:400]}")
    elif _davomiyligi > _TELEGRAM_XABAR_CHEGARASI_S:
        _jamoa_amal_qoshish(xodim_id, "bajarildi. Natija Telegram'ga yuborildi (uzoq cho'zilgani uchun)")
        telegram_xabar_yubor(f"{xodim_nomi}: {javob}")
    else:
        _jamoa_amal_qoshish(xodim_id, "bajarildi (tez tugagani uchun Telegramga yuborilmadi, panelda ko'rinadi)")


@app.route("/jamoa/topshiriq", methods=["POST", "OPTIONS"])
def jamoa_topshiriq_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    xodim = (data.get("xodim") or "").strip()
    matn = (data.get("matn") or "").strip()
    if xodim not in jarvis_jamoa_data.XODIMLAR or jarvis_jamoa_data.XODIMLAR[xodim].get("soon"):
        return jsonify({"error": "noto'g'ri yoki hali faol bo'lmagan xodim"}), 400
    if not matn:
        return jsonify({"error": "matn bo'sh bo'lishi mumkin emas"}), 400

    turi = _topshiriq_turi(matn)
    task_id = _uuid.uuid4().hex[:10]
    with _topshiriqlar_lock:
        _topshiriqlar[task_id] = {
            "id": task_id, "xodim": xodim, "matn": matn, "turi": turi,
            "holat": "kutmoqda_tasdiq" if turi == "yozish" else "navbatda",
            "natija": None, "vaqt": _datetime.now().strftime("%H:%M"),
        }

    if turi == "yozish":
        _jamoa_amal_qoshish(xodim, f"topshiriq qabul qilindi, tasdiq kutmoqda: \"{matn[:70]}\"")
    else:
        _jamoa_amal_qoshish(xodim, f"topshiriq qabul qilindi (o'qish): \"{matn[:70]}\"")
        _threading.Thread(target=_topshiriq_bajar, args=(task_id,), daemon=True).start()

    return jsonify({"id": task_id, "turi": turi, "holat": _topshiriqlar[task_id]["holat"]})


_XABAR_YUBORISH_KALIT = re.compile(r"\b(yubor\w*|jo'nat\w*|eslatma\w*|xabar\w*|sms|email)\b", re.IGNORECASE)
_XABAR_QABUL_KALIT = re.compile(r"ota-?ona\w*|mijoz\w*|o'quvchi\w*|sportchi\w*", re.IGNORECASE)


def _xabar_tasdiq_malumoti(matn: str) -> dict:
    """"Tasdiqlash" ikkinchi bosqichi (2026-09-28, Azizbek talabi) uchun: bu
    topshiriq odamlarga (mijoz/ota-ona) xabar yuborishmi, va shunday bo'lsa
    ANIQ nechta odamga ketishini REAL ma'lumotdan (SSH+jarvis_readonly,
    jarvis_xodim_dispatch bilan BIR XIL naqsh) hisoblaydi. Son hech qachon
    TO'QILMAYDI -- aniqlab bo'lmasa None qaytadi, frontend "aniq emas" deb
    ko'rsatadi."""
    matnl = matn or ""
    xabar_yuborish = bool(_XABAR_YUBORISH_KALIT.search(matnl)) and bool(_XABAR_QABUL_KALIT.search(matnl))
    if not xabar_yuborish:
        return {"xabar_yuborish": False, "soni": None}
    matnl_l = matnl.lower()
    soni = None
    try:
        oy = jarvis_xodim_dispatch._oy_str()
        if any(k in matnl_l for k in ("orzu", "azizedu", "aziz edu")):
            soni = len(jarvis_xodim_dispatch._azizedu_royxat(oy))
        elif "grampus" in matnl_l:
            soni = len(jarvis_xodim_dispatch._grampus_royxat(oy))
    except Exception:
        soni = None
    return {"xabar_yuborish": True, "soni": soni}


@app.route("/jamoa/topshiriq/<task_id>/tasdiq_malumoti", methods=["GET"])
def jamoa_tasdiq_malumoti_route(task_id):
    """Frontend 'Tasdiqlash' bosilganda BIRINCHI shu yerga so'rov yuboradi
    (hali /jamoa/tasdiqlash chaqirmaydi) -- ikkinchi tasdiq oynasi uchun
    kerakli matn+qabul qiluvchilar sonini oladi."""
    with _topshiriqlar_lock:
        task = _topshiriqlar.get(task_id)
        if not task:
            return jsonify({"error": "topshiriq topilmadi"}), 404
        matn = task["matn"]
    info = _xabar_tasdiq_malumoti(matn)
    info["matn"] = matn
    return jsonify(info)


@app.route("/jamoa/tasdiqlash", methods=["POST", "OPTIONS"])
def jamoa_tasdiqlash_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    task_id = (data.get("id") or "").strip()
    with _topshiriqlar_lock:
        task = _topshiriqlar.get(task_id)
        if not task:
            return jsonify({"error": "topshiriq topilmadi"}), 404
        if task["holat"] != "kutmoqda_tasdiq":
            return jsonify({"error": f"bu topshiriq allaqachon '{task['holat']}' holatida"}), 409
        task["holat"] = "navbatda"

    _threading.Thread(target=_topshiriq_bajar, args=(task_id,), daemon=True).start()
    return jsonify({"id": task_id, "holat": "navbatda"})


@app.route("/jamoa/bekor_qilish", methods=["POST", "OPTIONS"])
def jamoa_bekor_qilish_route():
    """2026-09-28, Telegram [❌ Bekor] tugmasi uchun -- HECH QANDAY bajarish
    yo'q, faqat holatni terminal 'bekor_qilindi'ga o'tkazadi (panelning
    'Tasdiqlash' bosilib "Yo'q" deyilgan holatidan farqli o'laroq, bu YOZUV
    o'zi ham tarixda "bekor qilindi" deb saqlanib qoladi -- Telegramdan
    xabar keladigan bo'lgani uchun keyinroq "nega bajarilmadi" degan
    savolga aniq javob bo'lsin)."""
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    task_id = (data.get("id") or "").strip()
    with _topshiriqlar_lock:
        task = _topshiriqlar.get(task_id)
        if not task:
            return jsonify({"error": "topshiriq topilmadi"}), 404
        if task["holat"] != "kutmoqda_tasdiq":
            return jsonify({"error": f"bu topshiriq allaqachon '{task['holat']}' holatida"}), 409
        task["holat"] = "bekor_qilindi"
        xodim_id = task["xodim"]
        matn = task["matn"]
    _jamoa_amal_qoshish(xodim_id, f"topshiriq BEKOR qilindi (Telegram): \"{matn[:70]}\"")
    jarvis_topshiriq_tarixi.yozuv_qoshish(
        xodim=xodim_id, matn=matn, holat="bekor_qilindi", natija=None,
        davomiyligi_s=None, sabab="Azizbek tomonidan bekor qilindi", manba=None,
    )
    return jsonify({"id": task_id, "holat": "bekor_qilindi"})


# ============================================================================
# "X ga ... deb yoz" -- Azizbekning shaxsiy Telegram akkaunti (userbot,
# Telethon) orqali kontaktlarga xabar yuborish, TASDIQ bilan (2026-09-28,
# Azizbek buyrug'i: "5 soniyada yuboriladi [X Bekor]" naqshi -- HUD ('/ask')
# va Telegram (jarvis_telegram.py, /shaxsiy/buyruq orqali) IKKALASI HAM shu
# BITTA funksiyani chaqiradi, shunda qoida IKKALA joyda ham bir xil bo'ladi).
#
# XAVFSIZLIK: haqiqiy yuborish FAQAT `userbot\kontakt.py yubor` orqali,
# FAQAT shu yerdagi 5 soniyalik kutish+bekor+kunlik-limit+log qatlamidan
# o'tgach sodir bo'ladi -- `userbot\yubor.py` va bir martalik `yubor_*.py`
# skriptlari ENDI shu oqim uchun ishlatilmaydi (ular qolgan, lekin yangi
# funksiyaga ulanmagan).
# ============================================================================
USERBOT_DIR = BASE_DIR.parent / "userbot"
_KONTAKT_PY = str(USERBOT_DIR / "kontakt.py")
_SHAXSIY_HOLAT_FAYL = USERBOT_DIR / "shaxsiy_holat.json"
_SHAXSIY_LOG_FAYL = USERBOT_DIR / "shaxsiy_yuborilganlar.jsonl"
SHAXSIY_KUTISH_S = 5
SHAXSIY_KUNLIK_LIMIT = 20

# 2026-09-28 (Azizbek buyrug'i, MAJBURIY xavfsizlik qoidasi): sinov qilish
# kerak bo'lsa, SINOV REJIMI yoqiladi -- shunda maqsad KIM topilishidan
# qat'i nazar MAJBURAN Azizbekning o'z "Saqlangan xabarlar"iga (OWNER_ID)
# yo'naltiriladi, haqiqiy uchinchi shaxsga HECH QACHON ketmaydi. Jarvis
# (AI agent) hech qachon o'zi /shaxsiy/buyruq, /shaxsiy/... yoki
# kontakt.py'ni chaqirmaydi -- yuborish FAQAT Azizbekning HUD/panel/
# Telegram buyrug'idan boshlanadi (qarang: vositalar.md).
#
# 2026-09-29 (Azizbek tuzatishi): avval bu ENV o'zgaruvchi edi (SINOV_REJIM=1)
# -- restart talab qilardi. Endi FAYLGA asoslangan (sinov_rejim.json),
# restartsiz o'zgaradi. Qoidalar:
#   - Fayl YO'Q -> oddiy (normal) rejim -- xavfsiz standart.
#   - Fayl BOR, to'g'ri o'qiladi -> "yoqilgan" qiymati amal qiladi.
#   - Fayl BOR, lekin BUZUQ/o'qib bo'lmaydi -> yuborish BLOKLANADI (xavfsiz
#     tomonga -- "buzuqda oddiy rejim" EMAS, chunki bu holatda haqiqiy
#     yuborilib qolish xavfi bor -- Azizbekning aniq talabi).
#   - Yoqish -- istalgan manbadan (AI/fon-agent ham) mumkin.
#   - O'chirish -- FAQAT HUD tugmasi orqali (`/sinov_rejim/ochir`, alohida
#     endpoint). Bu texnik jihatdan 100% majburlanmaydi (chunki bridge har
#     qanday to'g'ri token bilan kelgan so'rovni bir xil ko'radi), lekin:
#     (a) fon-agent/Jarvis promptlarida "hech qachon /sinov_rejim/ochir
#     chaqirma" qoidasi bor, (b) har yoqish/o'chirish DARHOL Telegram
#     xabari + log bilan Azizbekka ko'rinadi.
_SINOV_REJIM_FAYL = BASE_DIR / "sinov_rejim.json"
_SINOV_REJIM_LOCK = _threading.Lock()


def _sinov_rejim_holati() -> dict:
    """Har chaqiruvda faylni o'qiydi -- restart shart emas. Qaytaradi:
    {"yoqilgan": bool, "buzuq": bool, "xato": str|None, "vaqt": str|None, "manba": str|None}"""
    if not _SINOV_REJIM_FAYL.exists():
        return {"yoqilgan": False, "buzuq": False, "xato": None, "vaqt": None, "manba": None}
    try:
        matn = _SINOV_REJIM_FAYL.read_text(encoding="utf-8")
        data = _json.loads(matn)
        if not isinstance(data, dict) or not isinstance(data.get("yoqilgan"), bool):
            raise ValueError("kutilmagan format (\"yoqilgan\": true/false bo'lishi kerak)")
        return {
            "yoqilgan": data["yoqilgan"], "buzuq": False, "xato": None,
            "vaqt": data.get("vaqt"), "manba": data.get("manba"),
        }
    except Exception as e:
        return {"yoqilgan": False, "buzuq": True, "xato": str(e), "vaqt": None, "manba": None}


def _sinov_rejim_yoz(yoqilgan: bool, manba: str) -> dict:
    vaqt = _datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {"yoqilgan": yoqilgan, "vaqt": vaqt, "manba": manba}
    with _SINOV_REJIM_LOCK:
        _SINOV_REJIM_FAYL.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    holat_so_z = "YOQILDI" if yoqilgan else "O'CHIRILDI"
    telegram_xabar_yubor(f"⚠️ SINOV REJIMI {holat_so_z}\nManba: {manba}\nVaqt: {vaqt}")
    return data


try:
    from config import OWNER_ID as _SHAXSIY_OWNER_ID
except Exception:
    _SHAXSIY_OWNER_ID = None

#   - re.DOTALL ATAYLAB OLIB TASHLANDI (2026-10-09, Azizbek tuzatishi):
#     uzun, ko'p qatorli topshiriq xabari ichida tasodifan "...ga ... deb
#     yoz"/"...ga ... yubor:" shakliga o'xshab qolgan joy bo'lsa, DOTALL
#     bilan "." belgisi qator ko'chirish (\n) ni ham yutib, BUTUN ko'p
#     qatorli xabar shu naqshga "mos" bo'lib qolardi -- shu sabab Azizbekning
#     haqiqiy uzun topshirig'i yo'qolib, "kontakt topilmadi" javobi qaytgan
#     edi. Endi "." qator ichida qoladi.
#
#   - 2026-10-09 (Azizbek, IKKINCHI tuzatish, bir xil muammo yana chiqgani
#     uchun): yuqoridagi himoya ("." qator ichida qolishi) YETARLI emas edi
#     -- bitta QATORLI uzun topshiriq matni ham, agar ichida tasodifan
#     "<biror so'z>ga ... yubor" yoki "...ga ... deb yoz" ko'rinishiga
#     o'xshab TUGASA, ANIQ shu naqshga to'liq mos kelib qolishi mumkin edi
#     (masalan "...hisobotni tayyorlab menga yubor" kabi oddiy topshiriq
#     jumlasi). Erkin ("deb yoz"/"deb yubor"/"...ga yubor:") naqsh BUTUNLAY
#     OLIB TASHLANDI. Endi FAQAT ikki ANIQ, tasodifan paydo bo'lmaydigan
#     buyruq shakli ishga tushiradi:
#       1) "/send <Ism> <mazmun>"           -- xabar ANIQ "/send" bilan boshlansin
#       2) "<Ism>ga xabar: <mazmun>"        -- so'z "xabar" MAJBURIY (oldin ixtiyoriy edi)
#     Ikkisi ham matn BOSHIDA bo'lishi shart (re.match, ^...$) -- oddiy
#     topshiriq/xabar matni ichida/o'rtasida/oxirida tasodifan shu so'zlar
#     uchrab qolsa, ENDI UMUMAN ishga tushmaydi.
_SHAXSIY_YOZISH_NAQSH_SLASH = re.compile(
    r"^/send\s+(?P<ism>\S+)\s*[:,]?\s+(?P<mazmun>.+)$",
    re.IGNORECASE,
)
_SHAXSIY_YOZISH_NAQSH_XABAR = re.compile(
    r"^(?P<ism>.+?)\s*ga\s+xabar\s*[:\-]\s*(?P<mazmun>.+)$",
    re.IGNORECASE,
)


# 2026-09-28 (Azizbek buyrug'i, real xato: "Telegramdan Sanjar akaga ..."
# deyilganda "Telegram" so'zi ism qismiga aralashib, xabar Telegramning o'z
# xizmat chatiga ketgan edi) -- gap boshidagi kanal-ko'rsatuvchi so'zlar
# ism-ajratishdan OLDIN olib tashlanadi.
_KANAL_SOZLAR_NAQSH = re.compile(
    r"^\s*(?:telegram\s*orqali|telegramdan|telegramda|tg\s*orqali|tg\s*dan|"
    r"sms\s*orqali|sms\s*dan|smsda)\s*",
    re.IGNORECASE,
)

# Xizmat/rasmiy chatlar -- HECH QACHON qabul qiluvchi bo'lmasin (masalan
# Telegramning o'z "777000" xizmat xabarlar akkaunti).
_SHAXSIY_TAQIQLANGAN_CHAT_ID = {777000}

# 2026-09-28 (Azizbek imtihon-tuzatishi): shaxsiy xabar MAZMUNI (yoki "ism"
# maydoni -- masalan "kontaktlar ro'yxatidagi hammaga" kabi ommaviy-yuborish
# urinishi) xavfsiz emasmi tekshiradi.
_SHAXSIY_XAVFSIZ_EMAS_KALIT = re.compile(
    r"pul\s*so'ra|pul\s*kerak\s*deb|qarz\s*so'ra|"
    r"so'kin\w*|haqorat\w*|\bahmoq\w*|\bjinni\w*|\bkaltak\w*|"
    r"sinov_rejim\w*\s*(o'chir|off|yo'q\s*qil)|limitni\s*(chetlab|bypas|oshir)|"
    r"token\w*\s*(ayt|bo'l|ber)|parol\w*\s*(ayt|ber)|"
    r"hamma\w*\s*(ga|kontakt)\w*\s*(bir\s*xil|yubor)|ro'yxatdagi\s*hammaga",
    re.IGNORECASE,
)


_SHAXSIY_MAKS_UZUNLIK = 200  # Azizbek, 2026-10-09: bundan uzun xabar -- buyruq emas


def _shaxsiy_yozish_aniqla(matn: str):
    """"/send <Ism> <mazmun>" yoki "<Ism>ga xabar: <mazmun>" ANIQ buyruq
    shaklini aniqlaydi. Mos kelmasa None. Mos kelsa (ism, mazmun, kanal_aniq) --
    kanal_aniq=True agar "telegramdan/tg orqali/sms orqali" kabi aniq
    kanal-so'z ishlatilgan bo'lsa (2026-09-28: bu holatda ism xodim nomiga
    o'xshab qolsa ham AMBIGUITY tekshiruvi o'tkazib yuboriladi, chunki
    foydalanuvchi aniq "shaxsiy Telegram orqali" degan).

    2026-10-09 (Azizbek, ikkinchi tuzatish): endi FAQAT shu ikki ANIQ
    buyruq shakli ishga tushadi -- erkin "<ism>ga ... deb yoz/yubor" naqshi
    OLIB TASHLANDI, chunki oddiy uzun topshiriq matni tasodifan shu
    ko'rinishga o'xshab qolib, haqiqiy topshiriq yo'qolib ketgan edi.
    200 belgidan uzun xabar HAM, qo'shimcha himoya qatlami sifatida, HECH
    QACHON shaxsiy-kontakt buyrug'i deb hisoblanmaydi (/send va "ga xabar:"
    buyruqlari odatda qisqa bo'ladi -- bu chegara ularga xalaqit bermaydi)."""
    matn = (matn or "").strip()
    if len(matn) > _SHAXSIY_MAKS_UZUNLIK:
        return None
    kanal_aniq = bool(_KANAL_SOZLAR_NAQSH.match(matn))
    matn = _KANAL_SOZLAR_NAQSH.sub("", matn).strip()
    for naqsh in (_SHAXSIY_YOZISH_NAQSH_SLASH, _SHAXSIY_YOZISH_NAQSH_XABAR):
        m = naqsh.match(matn)
        if m:
            ism = m.group("ism").strip(" \t\"'")
            mazmun = m.group("mazmun").strip(" \t\"'")
            if ism and mazmun:
                return ism, mazmun, kanal_aniq
    return None


def _kontakt_qidir(ism: str, timeout: int = 20):
    try:
        natija = subprocess.run(
            [sys.executable, _KONTAKT_PY, "qidir", ism],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8",
        )
        data = _json.loads((natija.stdout or "").strip() or "[]")
        if isinstance(data, dict) and "xato" in data:
            return [], data["xato"]
        # Xizmat/rasmiy chatlar (masalan Telegram 777000) -- bridge
        # tomonida QO'SHIMCHA filtr (kontakt.py/monitor.py hali qayta
        # ishga tushirilmagan bo'lsa ham darhol amal qilishi uchun).
        data = [d for d in data if d.get("chat_id") not in _SHAXSIY_TAQIQLANGAN_CHAT_ID]
        return data, None
    except Exception as e:
        return [], str(e)


def _kontakt_yubor(chat_id, matn: str, timeout: int = 20):
    try:
        natija = subprocess.run(
            [sys.executable, _KONTAKT_PY, "yubor", str(chat_id), matn],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8",
        )
        data = _json.loads((natija.stdout or "").strip() or "{}")
        if isinstance(data, dict) and data.get("holat") == "yuborildi":
            return True, None
        return False, (data.get("xato") if isinstance(data, dict) else "noma'lum xato")
    except Exception as e:
        return False, str(e)


def _shaxsiy_holat_oqi() -> dict:
    try:
        d = _json.loads(_SHAXSIY_HOLAT_FAYL.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    if d.get("kun") != _datetime.now().strftime("%Y-%m-%d"):
        d = {"kun": _datetime.now().strftime("%Y-%m-%d"), "soni": 0}
    return d


def _shaxsiy_holat_yoz(holat: dict) -> None:
    try:
        _SHAXSIY_HOLAT_FAYL.write_text(_json.dumps(holat, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _shaxsiy_log_yoz(yozuv: dict) -> None:
    try:
        with open(_SHAXSIY_LOG_FAYL, "a", encoding="utf-8") as f:
            f.write(_json.dumps({"vaqt": _datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **yozuv}, ensure_ascii=False) + "\n")
    except Exception:
        pass


_SHAXSIY_QISQA_SOZ_CHEGARASI = 5


def _shaxsiy_matn_uslubda_tuz(ism: str, mazmun: str) -> str:
    """Qisqa, samimiy, Azizbekning odatiy Telegram uslubidagi xabar tuzadi
    ("Assalomu alaykum" bilan boshlanadi).

    2026-09-28 (Azizbek tuzatishi -- real sinovda AI matnni keragidan uzun
    qilib yuborgani aniqlandi): agar Azizbek ANIQ, tayyor qisqa ibora aytgan
    bo'lsa ("salom deb yoz", "rahmat deb yubor" -- <= 5 so'z), AI UMUMAN
    CHAQIRILMAYDI -- to'g'ridan-to'g'ri "Assalomu alaykum!" bilan o'raladi.
    Bu ham TEZROQ (AI so'rovisiz), ham ISHONCHLIROQ (AI hech qachon
    o'zidan gap qo'shib cho'zolmaydi). Faqat MAZMUNLI/uzunroq niyat
    tasvirlansa ("ertaga uchrasha olmasligimni ayt, band bo'lib qoldim"
    kabi) AI chaqiriladi -- lekin QATTIQ "hech narsa qo'shma" qoidasi
    bilan."""
    mazmun = mazmun.strip()

    if len(mazmun.split()) <= _SHAXSIY_QISQA_SOZ_CHEGARASI:
        oddiy = mazmun.rstrip(" .!").lower()
        if oddiy in ("salom", "assalomu alaykum", "salom ayt", "salom aytib qoy", "salom aytib qo'y"):
            return "Assalomu alaykum!"
        return f"Assalomu alaykum! {mazmun.rstrip('.')}."

    savol = (
        "Azizbek nomidan Telegramda tanishiga (do'st/tanish, ish sherigi) "
        "yozadigan xabarni SAMIMIY qilib teraman deb yordam ber. QATTIQ "
        "QOIDA: pastdagi mazmunga HECH QANDAY yangi mavzu, taklif, gap "
        "QO'SHMA -- faqat AYNAN shu fikrni tabiiy, QISQA (1-3 gap) "
        "jumla(lar)ga tuz, uzaytirma. \"Assalomu alaykum\" (yoki vaziyatga "
        "mos qisqaroq salomlashuv) bilan boshlansin. Rasmiy/sovuq/marketing "
        "ohangda BO'LMASIN. Faqat xabarning O'ZINI qaytar -- boshqa hech "
        "qanday izoh, tirnoq belgisi yoki \"Mana xabar:\" kabi kirish so'z "
        "YO'Q.\n\n"
        f"Aynan shu mazmunni yetkaz (bundan BOSHQA HECH NARSA qo'shma): {mazmun}"
    )
    try:
        try:
            matn = _ask_jarvis_doimiy(savol, 25)
        except Exception:
            matn = asyncio.run(asyncio.wait_for(_ask_jarvis(savol), timeout=25))
        matn = (matn or "").strip().strip('"').strip()
        if matn:
            return matn
    except Exception:
        pass
    return f"Assalomu alaykum! {mazmun.rstrip('.')}."


_shaxsiy_topshiriqlar: dict[str, dict] = {}
_shaxsiy_topshiriqlar_lock = _threading.Lock()


def _shaxsiy_auto_yuborish(task_id: str):
    _time.sleep(SHAXSIY_KUTISH_S)
    with _shaxsiy_topshiriqlar_lock:
        task = _shaxsiy_topshiriqlar.get(task_id)
        if not task or task["holat"] != "kutmoqda":
            return  # bekor qilingan yoki topilmadi
        task["holat"] = "yuborilmoqda"
        chat_id, matn, ism = task["chat_id"], task["matn"], task["ism"]
        sinov_rejimida = task.get("sinov_rejimida", False)

    ok, xato = _kontakt_yubor(chat_id, matn)
    with _shaxsiy_topshiriqlar_lock:
        task = _shaxsiy_topshiriqlar.get(task_id)
        if task:
            task["holat"] = "yuborildi" if ok else "xato"
            task["xato"] = xato

    if ok:
        holat = _shaxsiy_holat_oqi()
        holat["soni"] = holat.get("soni", 0) + 1
        _shaxsiy_holat_yoz(holat)
        _shaxsiy_log_yoz({
            "kimga": ism, "chat_id": chat_id, "matn": matn, "holat": "yuborildi",
            "sinov_rejim": sinov_rejimida,
        })
        belgi = " [SINOV REJIMI -- aslida Saqlangan xabarlaringizga ketdi]" if sinov_rejimida else ""
        telegram_xabar_yubor(f"✅ {ism}ga yuborildi:{belgi}\n\"{matn}\"")
    else:
        _shaxsiy_log_yoz({"kimga": ism, "chat_id": chat_id, "matn": matn, "holat": "xato", "xato": xato})
        telegram_xabar_yubor(f"❌ {ism}ga yuborishda xato: {xato}")


SHAXSIY_TAKROR_DAQIQA = 30


def _shaxsiy_yaqinda_yuborilganmi(soniya_ichida: float) -> bool:
    """2026-09-29 (Azizbek tuzatishi, band B): shaxsiy_yuborilganlar.jsonl
    oxirgi yozuvi so'nggi `soniya_ichida` soniya ichida bo'lsa True.
    AI "yubordim" deganda HAQIQATDA yuborilganmi tekshirish uchun."""
    try:
        satrlar = _SHAXSIY_LOG_FAYL.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    if not satrlar:
        return False
    try:
        oxirgi = _json.loads(satrlar[-1])
        vaqt = _datetime.strptime(oxirgi["vaqt"], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return False
    return (_datetime.now() - vaqt).total_seconds() <= soniya_ichida


def _shaxsiy_oxirgi_yuborilgan(chat_id):
    """Shu chat_id'ga oxirgi SHAXSIY_TAKROR_DAQIQA ichida muvaffaqiyatli
    yuborilgan xabar bo'lsa, (vaqt, matn) qaytaradi -- bo'lmasa None.
    2026-09-28 (Azizbek buyrug'i, takrorlash himoyasi) -- log fayli
    kichik (kunlik <=20 yozuv), oxiridan orqaga o'qish yetarli tez."""
    try:
        satrlar = _SHAXSIY_LOG_FAYL.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    chegara = _datetime.now() - _timedelta(minutes=SHAXSIY_TAKROR_DAQIQA)
    for satr in reversed(satrlar):
        try:
            yozuv = _json.loads(satr)
        except Exception:
            continue
        if yozuv.get("holat") != "yuborildi" or yozuv.get("chat_id") != chat_id:
            continue
        try:
            vaqt = _datetime.strptime(yozuv["vaqt"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if vaqt < chegara:
            break  # log vaqt bo'yicha o'suvchi -- bundan naridagilar ham eski
        return vaqt.strftime("%H:%M"), yozuv.get("matn", "")
    return None


def _shaxsiy_buyruq_ishla(matn: str) -> dict:
    """Markaziy funksiya -- HUD ('/ask' ichidan to'g'ridan-to'g'ri) VA
    Telegram (`/shaxsiy/buyruq` orqali, jarvis_xodim_telegram.py) IKKALASI
    HAM shu birgina joyni chaqiradi. Qaytaradi:
      {"boshqa": True}  -- bu naqsh emas, chaqiruvchi o'z odatdagi yo'liga davom etsin
      {"boshqa": False, "javob": "..."}  -- matn javob (topilmadi/ko'p mos/limit)
      {"boshqa": False, "shaxsiy_yozish": {...}}  -- 1 ta mos, tasdiq kutilmoqda
    """
    aniqlangan = _shaxsiy_yozish_aniqla(matn)
    if not aniqlangan:
        return {"boshqa": True}
    ism, mazmun, kanal_aniq = aniqlangan

    # 2026-09-28 (Azizbek imtihon-tuzatishi): xabar MAZMUNI xavfsiz emasmi
    # -- pul so'rash, haqorat, tizim/xavfsizlik sozlamalarini chetlab
    # o'tishga urinish, maxfiy ma'lumot (token/parol) so'rash. Bunday
    # xabar HECH QACHON tuzilmaydi/yuborilmaydi.
    if _SHAXSIY_XAVFSIZ_EMAS_KALIT.search(mazmun) or _SHAXSIY_XAVFSIZ_EMAS_KALIT.search(ism):
        _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="xavfsizlik_rad_etildi")
        return {"boshqa": False, "javob": "Bu xabarni yubora olmayman — mazmunida xavfsizlik muammosi bor (masalan pul so'rash, haqorat yoki tizim sozlamasini chetlab o'tish)."}

    # 2026-09-28 (Azizbek tuzatishi): agar ism BIR XODIM nomiga ham mos
    # kelsa (masalan "Malika" -- ham xodim, ham shaxsiy Telegram kontakti
    # bo'lishi mumkin) VA foydalanuvchi aniq kanal so'zi ("telegramdan" va
    # h.k.) ishlatmagan bo'lsa -- avtomatik xodimga EMAS, kontaktga ham
    # yubormasdan, aniqlashtirish so'raladi (xavfsizlik: noto'g'ri odamga
    # ketib qolishning oldini olish).
    if not kanal_aniq and _xodim_ismini_top(ism + " ."):
        _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="xodim_yoki_kontakt_noaniq")
        return {
            "boshqa": False,
            "javob": (
                f"\"{ism}\" xodim ismimi yoki shaxsiy Telegram kontaktingizmi? "
                f"Kontaktga yubormoqchi bo'lsangiz \"telegramdan {ism}ga xabar: ...\" deb aniqroq ayting."
            ),
        }

    holat = _shaxsiy_holat_oqi()
    if holat.get("soni", 0) >= SHAXSIY_KUNLIK_LIMIT:
        _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="limit_tugagan")
        return {"boshqa": False, "javob": f"Bugungi shaxsiy xabar limiti ({SHAXSIY_KUNLIK_LIMIT} ta) tugagan."}

    mos, xato = _kontakt_qidir(ism)
    if xato:
        _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="kontakt_endpoint_xato", xato=xato)
        return {"boshqa": False, "javob": f"Kontakt qidirishda xato: {xato}"}
    if not mos:
        _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="kontakt_topilmadi")
        # 2026-10-09 (Azizbek tuzatishi): kontakt topilmasa xabar ENDI
        # yo'qolmaydi -- asl matn chaqiruvchiga ("kontakt_topilmadi" kaliti
        # bilan) qaytariladi, u Ha/Yo'q so'raydi; "Ha" bosilsa shu asl matn
        # oddiy topshiriq sifatida jarvis.ask()ga yuboriladi.
        return {
            "boshqa": False,
            "javob": f"'{ism}' nomiga mos kontakt topilmadi. Buni topshiriq sifatida bajarayinmi?",
            "kontakt_topilmadi": {"asli_matn": matn},
        }
    if len(mos) > 1:
        royxat = "\n".join(
            f"  {i+1}) {m['ism']}" + (f" (@{m['username']})" if m.get("username") else "") for i, m in enumerate(mos[:6])
        )
        _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="ko_p_mos", soni=len(mos))
        return {"boshqa": False, "javob": f"'{ism}'ga bir nechta mos keldi, aniqrog'ini ayting:\n{royxat}"}

    kontakt = mos[0]
    xabar_matni = _shaxsiy_matn_uslubda_tuz(ism, mazmun)
    task_id = _uuid.uuid4().hex[:10]

    # 2026-09-29 (Azizbek tuzatishi): SINOV REJIMI endi faylga asoslangan --
    # maqsad KIM topilganidan qat'i nazar MAJBURAN Azizbekning o'z Saqlangan
    # xabarlariga yo'naltiriladi (real odamga HECH QACHON ketmaydi).
    # `nishon_chat_id` haqiqiy yuborishda ishlatiladi, `kontakt` ("ism"/
    # "username"/"oxirgi_xabar") esa HAR DOIM haqiqiy topilgan odamni
    # ko'rsatishda qoladi -- shunda sinovda ham "kimga borishi kerak edi"
    # aniq ko'rinadi. Fayl BUZUQ bo'lsa -- yuborish BUTUNLAY BLOKLANADI
    # (xavfsiz tomonga -- Azizbekning aniq talabi, "buzuqda oddiy rejim"
    # EMAS, chunki bu holatda haqiqiy uchinchi shaxsga ketib qolish xavfi bor).
    _sr = _sinov_rejim_holati()
    if _sr["buzuq"]:
        telegram_xabar_yubor(f"🛑 SINOV REJIMI fayli buzuq — yubormadim!\nXato: {_sr['xato']}\nIltimos sinov_rejim.json faylini tekshiring yoki o'chiring.")
        return {"boshqa": False, "javob": f"Yubormadim: sinov_rejim.json buzuq ({_sr['xato']}). Azizbekka xabar berdim."}

    nishon_chat_id = kontakt["chat_id"]
    sinov_belgisi = ""
    sinov_rejimida = _sr["yoqilgan"]
    if sinov_rejimida:
        if not _SHAXSIY_OWNER_ID:
            return {"boshqa": False, "javob": "SINOV REJIMI yoqilgan, lekin OWNER_ID topilmadi -- yubormadim."}
        nishon_chat_id = _SHAXSIY_OWNER_ID
        sinov_belgisi = " [SINOV REJIMI: haqiqiy o'rniga Saqlangan xabarlaringizga ketadi]"

    # 2026-09-28 (Azizbek buyrug'i, takrorlash himoyasi): shu odamga oxirgi
    # 30 daqiqada allaqachon xabar ketgan bo'lsa, AVTOMATIK 5-soniya-yuborish
    # O'RNIGA aniq Ha/Yo'q tasdiq so'raladi (SINOV_REJIM'da ham -- real
    # yuborilmasa ham, bu himoya HAR DOIM sinaladi/ko'rinadi).
    takror = _shaxsiy_oxirgi_yuborilgan(nishon_chat_id)

    with _shaxsiy_topshiriqlar_lock:
        _shaxsiy_topshiriqlar[task_id] = {
            "id": task_id, "chat_id": nishon_chat_id, "ism": kontakt["ism"],
            "username": kontakt.get("username"), "oxirgi_xabar": kontakt.get("oxirgi_xabar"),
            "matn": xabar_matni,
            "holat": "takror_tasdiq_kutmoqda" if takror else "kutmoqda",
            "sinov_rejimida": sinov_rejimida,
        }

    if takror:
        oldingi_vaqt, oldingi_matn = takror
        _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="takror_tasdiq_kutmoqda", kimga=kontakt["ism"], task_id=task_id)
        return {
            "boshqa": False,
            "javob": f"{kontakt['ism']}ga {oldingi_vaqt} da ham yozilgan edi (\"{oldingi_matn}\"). Yana yuboraymi?",
            "takror_tasdiq": {
                "id": task_id, "ism": kontakt["ism"], "username": kontakt.get("username"),
                "oldingi_vaqt": oldingi_vaqt, "oldingi_matn": oldingi_matn, "matn": xabar_matni,
            },
        }

    _threading.Thread(target=_shaxsiy_auto_yuborish, args=(task_id,), daemon=True).start()
    _hud_olchov_yoz("shaxsiy_buyruq", ism=ism, mazmun=mazmun, natija="topildi_kutmoqda", kimga=kontakt["ism"], task_id=task_id)

    return {
        "boshqa": False,
        "javob": f"{kontakt['ism']}ga: \"{xabar_matni}\" — {SHAXSIY_KUTISH_S} soniyada yuboriladi (bekor qilish mumkin).{sinov_belgisi}",
        "shaxsiy_yozish": {
            "id": task_id, "ism": kontakt["ism"], "username": kontakt.get("username"),
            "oxirgi_xabar": kontakt.get("oxirgi_xabar"), "matn": xabar_matni, "soniya": SHAXSIY_KUTISH_S,
        },
    }


@app.route("/shaxsiy/buyruq", methods=["POST", "OPTIONS"])
def shaxsiy_buyruq_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    matn = (data.get("matn") or "").strip()
    if not matn:
        return jsonify({"boshqa": True})
    return jsonify(_shaxsiy_buyruq_ishla(matn))


@app.route("/shaxsiy/bekor", methods=["POST", "OPTIONS"])
def shaxsiy_bekor_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    task_id = (data.get("id") or "").strip()
    with _shaxsiy_topshiriqlar_lock:
        task = _shaxsiy_topshiriqlar.get(task_id)
        if not task:
            return jsonify({"error": "topshiriq topilmadi"}), 404
        if task["holat"] != "kutmoqda":
            return jsonify({"error": f"allaqachon '{task['holat']}' holatida"}), 409
        task["holat"] = "bekor_qilindi"
        ism, matn = task["ism"], task["matn"]
    _shaxsiy_log_yoz({"kimga": ism, "matn": matn, "holat": "bekor_qilindi"})
    return jsonify({"id": task_id, "holat": "bekor_qilindi"})


@app.route("/shaxsiy/takror_ha", methods=["POST", "OPTIONS"])
def shaxsiy_takror_ha_route():
    """Takrorlash himoyasi -- "Ha, baribir yubor" bosilganda: holat
    "kutmoqda"ga o'tadi va ODATDAGI 5-soniya-taymer boshlanadi (xuddi
    takrorlash bo'lmagandagidek)."""
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    task_id = (data.get("id") or "").strip()
    with _shaxsiy_topshiriqlar_lock:
        task = _shaxsiy_topshiriqlar.get(task_id)
        if not task:
            return jsonify({"error": "topshiriq topilmadi"}), 404
        if task["holat"] != "takror_tasdiq_kutmoqda":
            return jsonify({"error": f"allaqachon '{task['holat']}' holatida"}), 409
        task["holat"] = "kutmoqda"
    _threading.Thread(target=_shaxsiy_auto_yuborish, args=(task_id,), daemon=True).start()
    return jsonify({"id": task_id, "holat": "kutmoqda", "soniya": SHAXSIY_KUTISH_S})


@app.route("/shaxsiy/takror_yoq", methods=["POST", "OPTIONS"])
def shaxsiy_takror_yoq_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    task_id = (data.get("id") or "").strip()
    with _shaxsiy_topshiriqlar_lock:
        task = _shaxsiy_topshiriqlar.get(task_id)
        if not task:
            return jsonify({"error": "topshiriq topilmadi"}), 404
        if task["holat"] != "takror_tasdiq_kutmoqda":
            return jsonify({"error": f"allaqachon '{task['holat']}' holatida"}), 409
        task["holat"] = "bekor_qilindi"
        ism, matn = task["ism"], task["matn"]
    _shaxsiy_log_yoz({"kimga": ism, "matn": matn, "holat": "bekor_qilindi", "sabab": "takrorlash_rad_etildi"})
    return jsonify({"id": task_id, "holat": "bekor_qilindi"})


@app.route("/shaxsiy/holat", methods=["GET"])
def shaxsiy_holat_route():
    task_id = (request.args.get("id") or "").strip()
    with _shaxsiy_topshiriqlar_lock:
        task = _shaxsiy_topshiriqlar.get(task_id)
        if not task:
            return jsonify({"error": "topshiriq topilmadi"}), 404
        return jsonify({"id": task_id, "holat": task["holat"]})


# 2026-09-29 (Azizbek tuzatishi, "bridge nusxalari himoyasi"): qaysi PID,
# qachondan beri va qaysi kod versiyasi (fayl oxirgi tahrir vaqti) ishlab
# turganini har doim ko'rish mumkin bo'lishi uchun.
@app.route("/status", methods=["GET", "OPTIONS"])
def bridge_status_route():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify({
        "pid": os.getpid(),
        "ishga_tushgan_vaqt": BRIDGE_ISHGA_TUSHGAN_VAQT,
        "kod_versiyasi": _bridge_kod_versiyasi(),
    })


# 2026-09-29 (Azizbek tuzatishi) -- SINOV REJIMI: faylga asoslangan, HUD/
# jamoa.html/qo'ng'iroq oynasi shu GET endpointdan holatni so'rab, sariq
# banner ko'rsatadi.
@app.route("/sinov_rejim", methods=["GET", "OPTIONS"])
def sinov_rejim_holati_route():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify(_sinov_rejim_holati())


# YOQISH -- istalgan manbadan (AI/fon-agent ham) ruxsat etiladi.
@app.route("/sinov_rejim/yoq", methods=["POST", "OPTIONS"])
def sinov_rejim_yoq_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    manba = (data.get("manba") or "noma'lum").strip()[:120]
    natija = _sinov_rejim_yoz(True, manba)
    return jsonify(natija)


# O'CHIRISH -- MAJBURIY qoida: FAQAT HUD (index.html'dagi tugma) orqali
# chaqirilishi kerak (qarang: D:\jarvis-os\vositalar.md -- Jarvis/fon-
# agentlarga "hech qachon /sinov_rejim/ochir chaqirma" qoidasi yozilgan).
# Texnik jihatdan bu 100% majburlanmaydi (bridge har to'g'ri-token so'rovni
# bir xil ko'radi), shuning uchun har chaqiruv -- kimdan bo'lishidan qat'i
# nazar -- DARHOL Telegram xabari + log bilan Azizbekka ko'rinadi (qoida
# buzilsa ham darhol bilinadi).
@app.route("/sinov_rejim/ochir", methods=["POST", "OPTIONS"])
def sinov_rejim_ochir_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    manba = (data.get("manba") or "HUD tugmasi").strip()[:120]
    natija = _sinov_rejim_yoz(False, manba)
    return jsonify(natija)


@app.route("/jamoa", methods=["GET"])
def jamoa_route():
    xodimlar = [dict(x) for x in jarvis_jamoa_data.barcha_xodimlar()]
    with _topshiriqlar_lock:
        faol_topshiriqlar = {
            t["xodim"]: t for t in sorted(_topshiriqlar.values(), key=lambda t: t["vaqt"])
            if t["holat"] in ("kutmoqda_tasdiq", "navbatda", "bajarilmoqda")
        }
    for x in xodimlar:
        t = faol_topshiriqlar.get(x["id"])
        if not t:
            x["topshiriq"] = None
            continue
        x["topshiriq"] = {"id": t["id"], "matn": t["matn"], "turi": t["turi"], "holat": t["holat"]}
        if t["holat"] == "kutmoqda_tasdiq":
            x["hozir"] = f"Tasdig'ingizni kutmoqda: {t['matn'][:90]}"
            x["status"] = "warn"
        else:
            x["hozir"] = f"Bajaryapti: {t['matn'][:90]}"
            x["status"] = "busy"

    lenta = jarvis_jamoa_data.bugungi_lenta(maks=10)
    with _jamoa_amallar_lock:
        lenta += list(_jamoa_amallar)
    lenta.sort(key=lambda y: y.get("vaqt", ""), reverse=True)

    # "Topshiriqlar" panel (2026-09-28) -- kimga/nima/holati/natijasi, BARCHA
    # (faol + tugagan) so'nggi topshiriqlar, eng yangisi birinchi.
    with _topshiriqlar_lock:
        tarix = sorted(_topshiriqlar.values(), key=lambda t: t["vaqt"], reverse=True)
        tarix = [
            {
                "id": t["id"], "xodim": t["xodim"], "matn": t["matn"], "turi": t["turi"],
                "holat": t["holat"], "natija": t.get("natija"), "batafsil": t.get("batafsil"),
                "manba": t.get("manba"), "vaqt": t["vaqt"], "mavzu": t.get("mavzu"),
            }
            for t in tarix[:25]
        ]

    return jsonify({"xodimlar": xodimlar, "lenta": lenta[:16], "topshiriqlar_tarixi": tarix})


@app.route("/jamoa/xulosa", methods=["GET"])
def jamoa_xulosa_route():
    """Ertalabki yig'ilish oxirida Jarvis aytadigan yakuniy xulosa (HUD
    frontend `standup()` oxirida chaqiradi, kunlik ovozli yig'ilish skripti
    (`jarvis_ertalabki_yigilish.py`) esa jarvis_jamoa_data.yakuniy_xulosa()ni
    to'g'ridan-to'g'ri, bridge'siz chaqiradi -- ikkalasi ham BIR XIL funksiya)."""
    xodimlar = jarvis_jamoa_data.barcha_xodimlar()
    return jsonify({"say": jarvis_jamoa_data.yakuniy_xulosa(xodimlar)})


# ==== "JAMOA" — har xodimning o'ziga xos ovozi (edge-tts, rate/pitch bilan) ====
# Mavjud /speak'dan FARQI: bu yerda ovoz/tezlik/balandlik xodimga qarab
# o'zgaradi (jarvis_jamoa_data.XODIMLAR), /speak esa o'zgarmas SPEAK_VOICE
# bilan ishlashda davom etadi (boshqa joyларda ishlatilgan, tegilmagan).
JAMOA_SPEAK_TIMEOUT_S = 25


async def _jamoa_tts_mp3_bytes(text: str, voice: str, rate: str, pitch: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_yol = tmp.name
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(mp3_yol)
        with open(mp3_yol, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(mp3_yol):
            os.remove(mp3_yol)


@app.route("/jamoa/speak", methods=["POST", "OPTIONS"])
def jamoa_speak_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    xodim = (data.get("xodim") or "").strip()
    text = (data.get("text") or "").strip()
    meta = jarvis_jamoa_data.XODIMLAR.get(xodim)
    if not meta:
        return jsonify({"error": "noto'g'ri xodim"}), 400
    if not text:
        return jsonify({"error": "text maydoni bo'sh bo'lishi mumkin emas"}), 400

    # 2026-09-27 (talaffuz): EKRANDA ko'ringan matn o'zgarmaydi, faqat ovoz
    # generatsiyasiga yuborilgandan OLDIN talaffuz.json + raqam->so'z orqali
    # o'tkaziladi (jarvis_ertalabki_yigilish.py bilan BIR XIL funksiya).
    ovoz_matni = jarvis_jamoa_data.ovoz_uchun_tayyorla(text)
    _t_boshi = _time.monotonic()
    try:
        audio_bytes = asyncio.run(asyncio.wait_for(
            _jamoa_tts_mp3_bytes(ovoz_matni, meta["voice"], meta["rate"], meta["pitch"]),
            timeout=JAMOA_SPEAK_TIMEOUT_S,
        ))
    except asyncio.TimeoutError:
        # 2026-09-28: /speak'dagi bilan bir xil zaxira -- qisqaroq matn, qisqaroq timeout.
        qisqa_matn = _tts_qisqartir(ovoz_matni)
        try:
            audio_bytes = asyncio.run(asyncio.wait_for(
                _jamoa_tts_mp3_bytes(qisqa_matn, meta["voice"], meta["rate"], meta["pitch"]),
                timeout=SPEAK_RETRY_TIMEOUT_S,
            ))
            _hud_olchov_yoz(
                "jamoa_tts", xodim=xodim, uzunlik=len(ovoz_matni), soniya=round(_time.monotonic() - _t_boshi, 1),
                natija="ok_qayta_urinishda",
            )
            return Response(audio_bytes, mimetype="audio/mpeg")
        except asyncio.TimeoutError:
            _hud_olchov_yoz(
                "jamoa_tts", xodim=xodim, uzunlik=len(ovoz_matni), soniya=round(_time.monotonic() - _t_boshi, 1),
                natija="timeout_ikkala_urinish",
            )
            return jsonify({"error": f"{JAMOA_SPEAK_TIMEOUT_S}+{SPEAK_RETRY_TIMEOUT_S} soniyada ovoz tayyor bo'lmadi (2 urinish)"}), 504
        except Exception as e2:
            _hud_olchov_yoz(
                "jamoa_tts", xodim=xodim, uzunlik=len(ovoz_matni), soniya=round(_time.monotonic() - _t_boshi, 1),
                natija="xato_qayta_urinishda", xato=str(e2),
            )
            return jsonify({"error": f"Ovoz yasashda xato (qayta urinishda): {e2}"}), 500
    except Exception as e:
        _hud_olchov_yoz(
            "jamoa_tts", xodim=xodim, uzunlik=len(ovoz_matni), soniya=round(_time.monotonic() - _t_boshi, 1),
            natija="xato", xato=str(e),
        )
        return jsonify({"error": f"Ovoz yasashda xato: {e}"}), 500

    if not audio_bytes:
        _hud_olchov_yoz(
            "jamoa_tts", xodim=xodim, uzunlik=len(ovoz_matni), soniya=round(_time.monotonic() - _t_boshi, 1),
            natija="bosh",
        )
        return jsonify({"error": "Ovoz yaratilmadi (bo'sh natija)"}), 500
    _hud_olchov_yoz(
        "jamoa_tts", xodim=xodim, uzunlik=len(ovoz_matni), soniya=round(_time.monotonic() - _t_boshi, 1),
        natija="ok",
    )
    return Response(audio_bytes, mimetype="audio/mpeg")


# ==== Xodim ismini matndan topish -- MARKAZIY funksiya (2026-09-28, Azizbek
# buyrug'i: panel 🎤'da "Bekzod, ..." -> STT "begzodbotlar va..." deb eshitib,
# vergul yo'q + ismga keyingi so'z yopishib ketgani uchun "Ism aniqlanmadi"
# xatosi chiqqan). BITTA joy -- jamoa.html HAM, (keyingi asosiy restartdan
# keyin) Telegram ovozli yo'li HAM shu yerga murojaat qiladi, ikki marta
# yozilmaydi. ====
# 2026-09-28: mantiq jarvis_jamoa_data.xodim_ismini_top()ga ko'chirildi --
# endi jarvis_xodim_telegram.py (Telegram ovozli/matnli yo'l) HAM AYNAN
# shu funksiyadan foydalanadi (avval Telegram alohida, qat'iy/vergul talab
# qiladigan mantiqqa ega edi -- "begzod"/"nazima"/vergulsiz ishlamas edi).
_xodim_ismini_top = jarvis_jamoa_data.xodim_ismini_top


@app.route("/jamoa/ism_aniqla", methods=["POST", "OPTIONS"])
def jamoa_ism_aniqla_route():
    """jamoa.html shu yerga xom matnni yuboradi (yozma HAM, 🎤 orqali HAM) --
    vergul/aniq format talab qilinmaydi. Mos kelsa {"xodim","savol"},
    kelmasa {"aniqlanmadi": true} (frontend shunda 6 ta xodim tugmasini
    ko'rsatadi, qizil xato o'rniga)."""
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    matn = (data.get("matn") or "").strip()
    if not matn:
        return jsonify({"aniqlanmadi": True})
    mos = _xodim_ismini_top(matn)
    if not mos:
        return jsonify({"aniqlanmadi": True})
    xid, savol = mos
    return jsonify({"xodim": xid, "savol": savol})


# ==== "Ismga murojaat" — pastdagi savol maydoni (5-bosqich davomi, 2026-09-28) ====
# 2026-09-28 (Azizbek qoidasi "HAR KIM O'Z SOHASIDA"): mavzu jarvis_xodim_dispatch
# orqali aniqlanadi (kim so'ralganidan qat'i nazar), keyin mavzuning HAQIQIY
# EGASI javob beradi -- boshqa xodimga so'ralgan bo'lsa, o'sha xodim
# YO'NALTIRADI ("bu <egasi>ning ishi") va egasi o'z ovozida javob beradi.
# Mavzu HECH birga mos kelmasa -- "bu ma'lumot menda yo'q" (AI chaqirilmaydi,
# raqam to'qilmaydi). Faqat haqiqiy "domen"siz erkin savollar AI'ga boradi.
@app.route("/jamoa/savol", methods=["POST", "OPTIONS"])
def jamoa_savol_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    xodim = (data.get("xodim") or "").strip()
    # 2026-09-29 (Azizbek xato-tuzatishi, band 2a): regex tekshiruvidan OLDIN
    # apostroflarni normallashtiramiz -- "bo`yicha"/"o'zgartir" kabi so'zlar
    # endi to'g'ri tutiladi.
    matn = _apostrof_normallashtir((data.get("matn") or "").strip())
    # 2026-09-29 (Azizbek xato-tuzatishi, band 1): frontend (qo'ng'iroq oynasi)
    # SHU qo'ng'iroqning oxirgi almashuvlarini (<=6 ta) shu yerga yuborishi
    # mumkin -- boshqa xodim/qo'ng'iroq bilan ARALASHMASLIGI uchun.
    tarix = data.get("tarix") or []
    if xodim not in jarvis_jamoa_data.XODIMLAR or jarvis_jamoa_data.XODIMLAR[xodim].get("soon"):
        return jsonify({"error": "noto'g'ri yoki hali faol bo'lmagan xodim"}), 400
    if not matn:
        return jsonify({"error": "savol bo'sh bo'lishi mumkin emas"}), 400

    ism = jarvis_jamoa_data.XODIMLAR[xodim]["name"]

    # 2026-09-29 (Azizbek tuzatishi, band A): "X ga ... deb yoz/yubor" endi
    # qo'ng'iroq oynasi ("/jamoa/savol") orqali ham ishlaydi -- YANGI yuborish
    # yo'li YOZILMADI, balki asosiy HUD/Telegram bilan BIR XIL, mavjud
    # `_shaxsiy_buyruq_ishla()` zanjiriga (kontakt qidiruv, 5s+Bekor, kunlik
    # limit, 30-daqiqa takror-himoya, SINOV REJIMI) to'g'ridan-to'g'ri
    # ulandi. Domen-aniqlashdan OLDIN tekshiriladi -- bu naqsh ("<ism>ga ...
    # deb yoz") juda o'ziga xos, boshqa domenlar bilan konflikt qilmaydi.
    _shaxsiy = _shaxsiy_buyruq_ishla(matn)
    if not _shaxsiy.get("boshqa", True):
        _jamoa_amal_qoshish(xodim, f"shaxsiy xabar so'rovini qabul qildi: \"{matn[:60]}\"")
        if "shaxsiy_yozish" in _shaxsiy:
            return jsonify({
                "turi": "shaxsiy_yozish", "javob": _shaxsiy["javob"], "ekran": _shaxsiy["javob"],
                "shaxsiy_yozish": _shaxsiy["shaxsiy_yozish"],
            })
        if "takror_tasdiq" in _shaxsiy:
            return jsonify({
                "turi": "shaxsiy_takror_tasdiq", "javob": _shaxsiy["javob"], "ekran": _shaxsiy["javob"],
                "takror_tasdiq": _shaxsiy["takror_tasdiq"],
            })
        return jsonify({"turi": "shaxsiy_javob", "javob": _shaxsiy["javob"], "ekran": _shaxsiy["javob"]})

    mos = jarvis_xodim_dispatch.aniqla(matn)
    if mos:
        egasi_id, handler = mos
        _boshlandi_h = _time.monotonic()
        try:
            natija = handler(matn)
        except Exception as e:
            natija = {"ekran": f"Xato: {e}", "ovoz": f"Kechirasiz, xato yuz berdi: {e}", "xato": True}
        _davomiyligi_h = _time.monotonic() - _boshlandi_h
        egasi_ism = jarvis_jamoa_data.XODIMLAR[egasi_id]["name"]
        jarvis_topshiriq_tarixi.yozuv_qoshish(
            xodim=egasi_id, matn=matn, holat=("xato" if natija.get("xato") else "tayyor"),
            natija=natija.get("ovoz"), davomiyligi_s=_davomiyligi_h, manba="domen",
        )
        # 2026-09-28 tuzatish: "ekran" endi to'liq texnik matn bo'lib qolaveradi,
        # lekin panel/Telegram ENDI uni subtitr/asosiy matn sifatida EMAS,
        # alohida "Batafsil" blokida ko'rsatadi -- shuning uchun bu yerda ham
        # aniq "batafsil" maydonini qo'shamiz (ekran ovozdan farq qilsagina).
        if egasi_id != xodim:
            yonaltiruvchi = f"Bu {egasi_ism}ning ishi, hoziroq unga beraman."
            _jamoa_amal_qoshish(xodim, f"savolni {egasi_ism}ga yo'naltirdi: \"{matn[:60]}\"")
            _jamoa_amal_qoshish(egasi_id, f"savolga javob berdi: \"{matn[:60]}\"")
            yon_batafsil = natija["ekran"] if natija.get("ekran") and natija["ekran"] != natija["ovoz"] else None
            return jsonify({
                "turi": "yonaltirildi", "javob": yonaltiruvchi, "ekran": yonaltiruvchi, "batafsil": None,
                "yonaltirilgan": {"xodim": egasi_id, "ovoz": natija["ovoz"], "ekran": natija["ekran"], "batafsil": yon_batafsil},
                "manba": "xato" if natija.get("xato") else "tayyor",
            })
        _jamoa_amal_qoshish(xodim, f"savolga darhol javob berdi: \"{matn[:60]}\"")
        batafsil = natija["ekran"] if natija.get("ekran") and natija["ekran"] != natija["ovoz"] else None
        return jsonify({"turi": "oqish", "javob": natija["ovoz"], "ekran": natija["ekran"], "batafsil": batafsil, "manba": "xato" if natija.get("xato") else "tayyor"})

    if jarvis_xodim_dispatch.malumot_yoqmi(matn):
        javob = f"Men {ism}. Kechirasiz, bu ma'lumot menda yo'q."
        _jamoa_amal_qoshish(xodim, f"\"ma'lumot yo'q\" javob berdi: \"{matn[:60]}\"")
        jarvis_topshiriq_tarixi.yozuv_qoshish(
            xodim=xodim, matn=matn, holat="tayyor", natija=javob, davomiyligi_s=0.0, manba="malumot_yoq",
        )
        return jsonify({"turi": "malumot_yoq", "javob": javob, "ekran": javob, "manba": "malumot_yoq"})

    turi = _topshiriq_turi(matn)
    if turi == "yozish":
        task_id = _uuid.uuid4().hex[:10]
        with _topshiriqlar_lock:
            _topshiriqlar[task_id] = {
                "id": task_id, "xodim": xodim, "matn": matn, "turi": turi,
                "holat": "kutmoqda_tasdiq", "natija": None, "manba": None,
                "vaqt": _datetime.now().strftime("%H:%M"),
            }
        _jamoa_amal_qoshish(xodim, f"savol yozuvchi amal talab qiladi, tasdiq kutmoqda: \"{matn[:70]}\"")
        javob = f"Men {ism}, bu so'rov yozuvchi amal talab qiladi — kartochkamda \"Tasdiqlash\" tugmasini bosing."
        return jsonify({"turi": "yozish", "id": task_id, "javob": javob, "ekran": javob})

    # 2026-09-29 (Azizbek xato-tuzatishi, band 1 -- ENG MUHIM): oldin bu yerda
    # "_ask_jarvis_doimiy" (BITTA umumiy, doimiy ochiq Claude sessiya, hamma
    # xodim/qo'ng'iroq uchun BIR XIL) ishlatilardi -- natijada masalan Nozimaga
    # berilgan savolga, bir necha daqiqa oldin Kamolaga berilgan savol asosida
    # javob berilib qolardi (xotira aralashuvi, real sinovda topilgan xato).
    # Endi HAR safar YANGI, mustaqil Jarvis sessiyasi ishlatiladi (_ask_jarvis,
    # "async with" -- ochiladi, javob beradi, yopiladi) -- "_ask_jarvis_doimiy"
    # shu yo'lda UMUMAN chaqirilmaydi, shuning uchun xotira aralashuvi FIZIK
    # jihatdan mumkin emas (har chaqiruv butunlay yangi, bo'sh kontekst bilan
    # boshlanadi). Buning o'rniga, agar frontend "tarix" (shu qo'ng'iroqning
    # oxirgi <=6 almashuvi) yuborgan bo'lsa, shuni promptga qo'shib beramiz --
    # shunda xodim "xotira"ga ega bo'ladi, lekin FAQAT shu qo'ng'iroq doirasida.
    tarix_matni = ""
    if isinstance(tarix, list) and tarix:
        qatorlar = []
        for t in tarix[-6:]:
            if isinstance(t, dict) and (t.get("savol") or t.get("javob")):
                qatorlar.append(f"- Savol: {t.get('savol', '')}\n  Javob: {t.get('javob', '')}")
        if qatorlar:
            tarix_matni = (
                "\n\nSHU QO'NG'IROQNING oldingi almashuvlari (FAQAT shu suhbat "
                "uchun -- boshqa xodim yoki boshqa odam bilan HECH QANDAY "
                "aloqasi yo'q, ularni ESLATMA):\n" + "\n".join(qatorlar) + "\n"
            )

    savol = (
        f"[{ism} rolida, faqat REAL ma'lumotga asoslanib javob ber. "
        f"Aniq son/ma'lumot topolmasang, hech narsa to'qib chiqarma — shunchaki "
        f"\"bu ma'lumot menda yo'q\" de. Hech narsa yozma/o'zgartirma, faqat o'qi. "
        f"MUHIM: bu butunlay YANGI, MUSTAQIL savol — bundan oldin senga berilgan "
        f"boshqa hech qanday xodim/foydalanuvchi/suhbat konteksti bu yerga "
        f"aloqador EMAS, ularni umuman hisobga olma yoki eslatma. Faqat pastdagi "
        f"(agar bo'lsa) shu qo'ng'iroq tarixi va joriy savolga tayan."
        f"{jarvis_xodim_qoidalar.ai_prompt_uchun_qoshimcha(xodim)}]"
        f"{_AI_XAVFSIZLIK_VA_FORMAT}{tarix_matni}\n\nSavol: {matn}"
    )
    batafsil = None
    xato_sababi = None
    _boshlandi_ai = _time.monotonic()
    try:
        javob_xom = asyncio.run(asyncio.wait_for(_ask_jarvis(savol), timeout=JAMOA_SAVOL_TIMEOUT_S))
        javob, batafsil = _javobni_ajrat(javob_xom)
    except Exception as e:
        xato_sababi = str(e)
        javob = f"Kechirasiz, hozir javob bera olmadim ({xato_sababi}). Birozdan keyin qayta so'rang."
    _davomiyligi_ai = _time.monotonic() - _boshlandi_ai

    jarvis_topshiriq_tarixi.yozuv_qoshish(
        xodim=xodim, matn=matn, holat=("xato" if xato_sababi else "tayyor"),
        natija=(xato_sababi or javob), davomiyligi_s=_davomiyligi_ai,
        sabab=xato_sababi, manba="ai",
    )
    _jamoa_amal_qoshish(xodim, f"savolga javob berdi: \"{matn[:60]}\"")
    return jsonify({"turi": "oqish", "javob": javob, "ekran": javob, "batafsil": batafsil, "manba": "ai"})


# ==== "Majlis" — ko'p-xodimli muhokama (5-bosqich davomi, 2026-09-28) ====
@app.route("/jamoa/majlis/boshlash", methods=["POST", "OPTIONS"])
def jamoa_majlis_boshlash_route():
    """Jonli (ixtiyoriy mavzu) majlis — AI'dan BITTA so'rovda butun majlis
    matnini so'raydi (real ko'rsatkichlar promptga oldindan berilgan).
    AI ishlamasa/vaqt tugasa/JSON buzuq bo'lsa — HECH QACHON butunlay
    muvaffaqiyatsiz bo'lmaydi, deterministik zaxira ishlatiladi."""
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    mavzu = (data.get("mavzu") or "").strip()
    if not mavzu:
        return jsonify({"error": "mavzu bo'sh bo'lishi mumkin emas"}), 400

    prompt = jarvis_majlis.live_ai_prompt(mavzu)
    natija = None
    manba = "ai"
    try:
        try:
            raw = _ask_jarvis_doimiy(prompt, JAMOA_MAJLIS_TIMEOUT_S)
        except Exception:
            raw = asyncio.run(asyncio.wait_for(_ask_jarvis(prompt), timeout=JAMOA_MAJLIS_TIMEOUT_S))
        natija = jarvis_majlis.parse_ai_majlis_javobi(raw)
    except Exception:
        natija = None

    if natija is None:
        natija = jarvis_majlis.live_fallback_majlis(mavzu)
        manba = "zaxira"

    natija["mavzu"] = mavzu
    natija["manba"] = manba
    _jamoa_amal_qoshish("jarvis", f"Majlis boshlandi: \"{mavzu[:70]}\" (manba: {manba})")
    return jsonify(natija)


@app.route("/jamoa/majlis/oxirgi", methods=["GET"])
def jamoa_majlis_oxirgi_route():
    """Bugun kechasi saqlangan DEMO majlis (Orzu Akademy) — butunlay
    diskdan, AI/internet/edge-tts kerak emas (offline ishlaydi)."""
    data = jarvis_majlis.demo_saqlanganini_oqi()
    if not data:
        return jsonify({"error": "hali saqlangan majlis yo'q"}), 404
    return jsonify(data)


@app.route("/jamoa/majlis/audio/<path:fayl_nomi>", methods=["GET"])
def jamoa_majlis_audio_route(fayl_nomi):
    if "/" in fayl_nomi or "\\" in fayl_nomi or ".." in fayl_nomi:
        return jsonify({"error": "noto'g'ri fayl nomi"}), 400
    yol = jarvis_majlis.MAJLIS_DIR / "oxirgi_audio" / fayl_nomi
    if not yol.exists():
        return jsonify({"error": "fayl topilmadi"}), 404
    return Response(yol.read_bytes(), mimetype="audio/mpeg")


@app.route("/jamoa/majlis/topshiriq", methods=["POST", "OPTIONS"])
def jamoa_majlis_topshiriq_route():
    """"✅ Topshiriq qilish" — DARHOL, AI'siz xotira/vazifalar.md'ga yozadi
    (deterministik, o'zgarmas) VA 2026-09-28'dan buyon bir vaqtda haqiqiy
    topshiriq (task) ham yaratadi -- shu orqali g'oya "Topshiriqlar"
    panelida yangi->bajarilmoqda->bajarildi/tasdiq-kutish zanjiridan
    o'tadi, xuddi panel/majlisdan tashqari berilgan topshiriq kabi."""
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    matn = (data.get("matn") or "").strip()
    xodim = (data.get("xodim") or "").strip()
    muddat = (data.get("muddat") or "").strip()
    mavzu = (data.get("mavzu") or "").strip()
    if not (matn and xodim and muddat):
        return jsonify({"error": "matn/xodim/muddat bo'sh bo'lishi mumkin emas"}), 400
    qator = jarvis_majlis.vazifa_yoz(matn, xodim, muddat, mavzu)
    _jamoa_amal_qoshish(xodim, f"majlis g'oyasi vazifalar.md'ga yozildi: \"{matn[:60]}\"")
    telegram_xabar_yubor(f"📋 Majlisdan yangi topshiriq: {qator}")

    task_id = _uuid.uuid4().hex[:10]
    turi = _topshiriq_turi(matn) if xodim in jarvis_jamoa_data.XODIMLAR and not jarvis_jamoa_data.XODIMLAR[xodim].get("soon") else "yozish"
    with _topshiriqlar_lock:
        _topshiriqlar[task_id] = {
            "id": task_id, "xodim": xodim, "matn": matn, "turi": turi,
            "holat": "kutmoqda_tasdiq" if turi == "yozish" else "navbatda",
            "natija": None, "manba": None, "mavzu": mavzu,
            "vaqt": _datetime.now().strftime("%H:%M"),
        }
    if turi == "yozish":
        _jamoa_amal_qoshish(xodim, f"majlis g'oyasi yozuvchi amal, tasdiq kutmoqda: \"{matn[:60]}\"")
    else:
        _jamoa_amal_qoshish(xodim, f"majlis g'oyasi topshiriq sifatida qabul qilindi: \"{matn[:60]}\"")
        _threading.Thread(target=_topshiriq_bajar, args=(task_id,), daemon=True).start()

    return jsonify({"ok": True, "qator": qator, "task_id": task_id, "turi": turi})


# 2026-09-29 (video-majlis UI, Azizbek spetsifikatsiyasi, band 3) — YANGI,
# QO'SHIMCHA endpoint: jonli majlis (/jamoa/majlis/boshlash) natijasini
# .md formatiga o'girib SAQLAYDI. 2026-09-29 tuzatish (Azizbek): D:\jarvis-os
# EMAS -- MAVJUD `jarvis_majlis.MAJLIS_DIR` (jarvis_hud/majlislar/, o'sha
# yerda allaqachon oxirgi.json bor) ishlatiladi, yangi papka ochilmaydi.
# Mavjud majlis/topshiriq/boshlash mantig'iga TEGILMAYDI — faqat frontend
# allaqachon olgan natija JSON'ini (tur1/tur2/gtoyalar/xulosa/mavzu/manba)
# formatlab yozadi.
MAJLIS_MD_DIR = jarvis_majlis.MAJLIS_DIR


def _majlis_md_matni(data: dict) -> tuple[str, str]:
    sana_vaqt = _datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    satrlar = [
        f"# Majlis — {data.get('mavzu', '')}",
        "",
        f"Sana/vaqt: {sana_vaqt}",
        f"Manba: {data.get('manba', 'ai')}",
        "",
        "## 1-tur",
    ]
    for g in data.get("tur1", []) or []:
        ism = jarvis_jamoa_data.XODIMLAR.get(g.get("xodim"), {}).get("name", g.get("xodim"))
        satrlar.append(f"- **{ism}**: {g.get('matn', '')}")
    satrlar += ["", "## 2-tur — javoblar"]
    for g in data.get("tur2", []) or []:
        ism = jarvis_jamoa_data.XODIMLAR.get(g.get("xodim"), {}).get("name", g.get("xodim"))
        satrlar.append(f"- **{ism}**: {g.get('matn', '')}")
    satrlar += ["", "## Qarorlar (kim — nima — qachongacha)"]
    for g in data.get("gtoyalar", []) or []:
        ism = jarvis_jamoa_data.XODIMLAR.get(g.get("xodim"), {}).get("name", g.get("xodim"))
        satrlar.append(f"- {g.get('matn', '')} — mas'ul: {ism}, muddat: {g.get('muddat', '')}")
    satrlar += ["", "## Xulosa", data.get("xulosa", "")]
    return "\n".join(satrlar) + "\n", sana_vaqt


@app.route("/jamoa/majlis/saqla_md", methods=["POST", "OPTIONS"])
def jamoa_majlis_saqla_md_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    if not data.get("mavzu"):
        return jsonify({"ok": False, "xato": "mavzu bo'sh"}), 400
    try:
        MAJLIS_MD_DIR.mkdir(parents=True, exist_ok=True)
        matn, sana_vaqt = _majlis_md_matni(data)
        yol = MAJLIS_MD_DIR / f"{sana_vaqt}.md"
        yol.write_text(matn, encoding="utf-8")
        return jsonify({"ok": True, "yol": str(yol)})
    except Exception as e:
        return jsonify({"ok": False, "xato": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "xabar": "Jarvis HUD bridge ishlayapti. POST /ask ni ishlating."})


# 2026-09-29 (Azizbek tuzatishi, "bridge nusxalari himoyasi"): 18:05-18:20
# oralig'ida bir nechta bridge nusxasi (fon-agent tomonidan qo'lda, Task
# Scheduler'siz ishga tushirilgan) bir vaqtda tirik qolib, port 8090'ni
# navbat bilan tortib olib turgan holat aniqlandi -- ba'zan ESKI kod
# ishlab turgan bridge portni egallab qolgan. Endi: ishga tushishda
# PID-fayl orqali "allaqachon ishlayapti"ni tekshiradi, ikkinchi nusxa
# JIM ISHLAMAYDI -- darhol chiqib ketadi, log+Telegram xabar beradi.
_BRIDGE_PID_FAYL = BASE_DIR / "bridge.pid"
BRIDGE_ISHGA_TUSHGAN_VAQT = None  # /jarayonlar/holat endpoint uchun, pastda to'ldiriladi


def _bridge_kod_versiyasi() -> str:
    """Kod versiyasi sifatida shu faylning mtime'i (git hash ishonchli emas --
    working tree'da committed bo'lmagan o'zgarish bo'lishi mumkin, mtime
    "qachon oxirgi marta tahrirlangan"ni har doim to'g'ri ko'rsatadi)."""
    try:
        mtime = os.path.getmtime(__file__)
        return _datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "noma'lum"


def _pid_himoyasi_tekshir_va_yoz():
    """Agar PID-fayldagi jarayon HALI TIRIK bo'lsa -- darhol chiqib ketadi
    (ikkinchi nusxa bo'lib ishlamaydi). Aks holda o'z PID'ini yozadi."""
    joriy_pid = os.getpid()
    if _BRIDGE_PID_FAYL.exists():
        try:
            eski_pid = int(_BRIDGE_PID_FAYL.read_text(encoding="utf-8").strip())
        except Exception:
            eski_pid = None
        if eski_pid and eski_pid != joriy_pid:
            try:
                import psutil
                tirik = psutil.pid_exists(eski_pid)
            except Exception:
                tirik = False  # psutil bo'lmasa -- xavfsiz tomonga, eski o'lik deb hisoblaymiz
            if tirik:
                xabar = f"🛑 Bridge ALLAQACHON ishlayapti (PID {eski_pid}) -- yangi nusxa (PID {joriy_pid}) chiqib ketmoqda, ikkita nusxa BIR VAQTDA ishlamasin."
                print(xabar, flush=True)
                try:
                    telegram_xabar_yubor(xabar)
                except Exception:
                    pass
                raise SystemExit(1)
    _BRIDGE_PID_FAYL.write_text(str(joriy_pid), encoding="utf-8")


if __name__ == "__main__":
    _pid_himoyasi_tekshir_va_yoz()
    BRIDGE_ISHGA_TUSHGAN_VAQT = _datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"PID {os.getpid()}, kod versiyasi (oxirgi tahrir): {_bridge_kod_versiyasi()}", flush=True)

    # E6-bosqich: Whisper modelini SERVER ISHGA TUSHGANDA oldindan xotiraga yuklab qo'yamiz
    # (avval faqat birinchi /transcribe so'rovida, Google STT ishlamay qolganda chaqirilardi —
    # bu holda birinchi haqiqiy chaqiruv ~18s gacha cho'zilishi kuzatilgan, mijoz oldida demo
    # paytida bu juda sezilarli kechikish bo'lar edi). Xato bo'lsa ham server ishga tushishda
    # davom etadi — Google STT baribir asosiy yo'l, Whisper faqat zaxira.
    print("Whisper modeli oldindan yuklanmoqda (bir martalik, server tayyorlanish bosqichi)...")
    try:
        _whisper_yukla()
        print("Whisper modeli tayyor — birinchi /transcribe so'rovi ham tez ishlaydi.")
    except Exception as e:
        print(f"OGOHLANTIRISH: Whisper modelini oldindan yuklab bo'lmadi ({e}) — "
              f"birinchi /transcribe so'rovida qayta urinilib ko'riladi (sekinroq bo'lishi mumkin).")

    # E9-bosqich: doimiy Jarvis sessiyasini FON OQIMIDA ochishni boshlaymiz
    # (bloklamaydi — server darhol pastda ishga tushadi). Sessiya tayyor
    # bo'lguncha kelgan so'rovlar avtomatik eski, sekinroq usulga tushib
    # turadi; tayyor bo'lgach, keyingi barcha so'rovlar tezroq bo'ladi.
    print("Doimiy Jarvis sessiyasi fon oqimida ochilmoqda...")
    _doimiy_sessiyani_boshlash()

    # E10-bosqich: threaded=True — MUHIM tuzatish. threaded=False bo'lganda
    # Flask bir vaqtning o'zida FAQAT BITTA so'rovni qabul qiladi: agar bitta
    # so'rov (masalan to'liq AI agentga tushib qolgan murakkab savol) hali
    # javob qaytarmagan bo'lsa, undan KEYIN kelgan HAR QANDAY so'rov — hatto
    # tezkor qatlamda bir zumda bajariladigan "salom jarvis" kabi oddiy
    # buyruq ham — navbatda kutib turishga majbur bo'ladi. Shu sabab tezkor
    # qatlam to'g'ri ishlayotgan bo'lsa ham HUD "sekin javob berdi" deb
    # ko'rinishi mumkin edi. threaded=True bilan har bir so'rov alohida
    # oqimda darhol qabul qilinadi — tezkor buyruqlar boshqa so'rov qancha
    # davom etayotganidan qat'iy nazar bir zumda javob beradi.
    print(f"Jarvis HUD bridge http://localhost:{PORT} da ishga tushmoqda...")
    print("To'xtatish uchun shu oynani yoping yoki Ctrl+C bosing.")
    # roadmap #5 (2026-09-21, xavfsizlik): 0.0.0.0 EMAS — faqat 127.0.0.1.
    # Avval har qanday tarmoqdagi qurilma (bir xil Wi-Fi/LAN'dagi boshqa
    # kompyuter/telefon) ushbu kompyuterning IP-manziliga to'g'ridan-to'g'ri
    # ulanib, TOKEN bilmasa ham 401 javobidan tashqari hech narsaga
    # ega bo'lolmasdi, lekin baribir portga ulana olardi. Endi faqat shu
    # kompyuterning o'zidagi jarayonlar ulana oladi.
    app.run(host="127.0.0.1", port=PORT, threaded=True, debug=False)
