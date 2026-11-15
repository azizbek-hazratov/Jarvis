# -*- coding: utf-8 -*-
"""
AI yangiliklar kuzatuvchisi + o'zbekcha kontent-loyihasi generatori.

Maqsad: sun'iy intellekt sohasidagi yangiliklarni (yangi modellar, katta
e'lonlar) bir nechta ishonchli manbalardan (OpenAI, Google DeepMind,
TechCrunch AI, The Verge AI, MIT Technology Review AI) kuzatib, YANGI
maqolalar chiqqanda Azizbekka Telegram orqali xabar yuboradi.

2026-09-13, Azizbek ovozli xabar bilan so'ragan qo'shimcha: shaxsiy Telegram
kanali (t.me/azizbek_ai_agent, "Azizbek AI Agent") uchun bu yangiliklarni
o'zbek tilida, biznes egalariga tushunarli post-loyihasi shaklida yozib,
KANALGA TO'G'RIDAN-TO'G'RI, AVTOMATIK qo'yish (userbot/yubor.py orqali,
Azizbekning shaxsiy Telethon sessiyasi bilan, chunki kanal aynan shu
akkaunt orqali yaratilgan).

**MUHIM -- QOIDA O'ZGARISHI TARIXI:** kontent.md'dagi asl qattiq qoida
(2026-09-12, "hech qanday post aniq buyruqsiz qo'yilmaydi") Instagram/
Facebook (Buffer orqali boshqariladigan) kontent uchun edi. 2026-09-13
kuni Azizbek ALOHIDA, aniq so'rab, MAXSUS shu "Azizbek AI Agent" Telegram
kanali uchun avtomatik post qo'yishga RUXSAT berdi ("o'zing
to'g'ridan-to'g'ri qo'yib borasan" -- ovozli xabar bilan ikki marta
tasdiqlangan). **Bu istisno FAQAT shu kanalga tegishli** -- Instagram/
Facebook (Buffer) kontentida asl qattiq qoida (avval tasdiqlash SHART)
o'zgarishsiz davom etadi.

Ishlash tartibi:
- Har manbaning RSS-lentasi o'qiladi.
- Avval ko'rilgan (ai_yangiliklar_korilgan.json'da saqlangan) havolalar bilan
  solishtiriladi -- FAQAT yangilari e'lon qilinadi.
- BIRINCHI ishga tushirishda (fayl hali yo'q) hamma narsa "ko'rilgan" deb
  belgilanadi, lekin HECH NARSA POST QILINMAYDI -- aks holda eski
  maqolalar bilan kanal birdaniga to'lib ketardi.
- Har bir ishga tushirishda YANGI maqolalardan birinchi KONTENT_UCHUN_MAKS
  tasi uchun to'liq o'zbekcha post (Jarvis/Claude orqali) yoziladi va
  DARHOL kanalga qo'yiladi (LLM xarajati/vaqtini cheklash uchun cheklangan
  son). Har postdan keyin Azizbekka QISQA tasdiq-xabar yuboriladi (nazorat
  uchun, tasdiq SO'RAMAYDI -- amal allaqachon bajarilgan). Qolgan yangi
  maqolalar (bo'lsa) faqat sarlavha+havola ro'yxati sifatida Azizbekka
  yuboriladi (post qilinmaydi), keyingi ishga tushirishda navbat ularga yetadi.
- Kanalga post qo'yishda xato bo'lsa (masalan userbot sessiyasi muammosi),
  Azizbekka ALOHIDA ogohlantirish yuboriladi (tayyor matn bilan birga) --
  hech narsa jimgina yo'qolib ketmaydi.
- Xato (masalan bitta manba vaqtincha ishlamasa, yoki bitta post yozilmasa/
  qo'yilmasa) boshqa manbalar/maqolalarga ta'sir qilmaydi -- har biri
  alohida try/except bilan o'raladi.

Task Scheduler: "Jarvis AI Yangiliklar" vazifasi, har 3 daqiqada shu
faylni to'g'ridan-to'g'ri (`python ai_yangiliklar.py`) ishga tushiradi --
Azizbek "darhol/tez-tez" reaksiya so'ragani uchun mavjud 30-daqiqalik
"Jarvis Proaktiv Tekshiruv" tsiklidan AJRATIB, alohida tez tsiklga
o'tkazildi (u yerdan olib tashlangan).
"""
import asyncio
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime

import feedparser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from jarvis_core import Jarvis  # o'zbekcha post-loyihasini yozish uchun (LLM)
import kanal_post_limiti  # 2026-09-15: kanaldagi UMUMIY kunlik post-limiti (ai_yangiliklar + portfolio jami)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "ai_yangiliklar.log")
HOLAT_PATH = os.path.join(BASE_DIR, "ai_yangiliklar_korilgan.json")

# "Azizbek AI Agent" Telegram kanali -- userbot/yubor.py'da "qidir" bilan
# tasdiqlangan chat_id (2026-09-13). userbot/config.py'dagi Telethon
# sessiyasi (Azizbekning shaxsiy akkaunti) orqali ishlaydi, chunki kanal
# aynan shu akkaunt bilan yaratilgan (bot emas, oddiy Bot API bilan
# post qo'ya olmaydi -- kanal egasi/admin sifatida faqat userbot orqali mumkin).
AZIZBEK_AI_AGENT_CHAT_ID = -1003530829848
USERBOT_DIR = os.path.join(BASE_DIR, "userbot")

# Manbalar -- AI-yangiliklari (shov-shuv/shovqinni kamaytirish uchun aniq
# manbalar bilan cheklangan) + 2026-09-13'dan boshlab, Azizbek so'ragani
# uchun buxgalteriya/moliya sohasi yangiliklari ham (tanlov bosqichi allaqachon
# buxgalteriyaga daxldor mavzularga ustuvorlik beradi -- _engqiziqarlilarini_tanla).
# Eslatma: ko'p "buxgalteriya + AI" maxsus feed sinaldi (AccountingToday,
# Thomson Reuters, Journal of Accountancy) -- aksariyati yoki HTML qaytardi
# (haqiqiy RSS emas) yoki 404 berdi, faqat quyidagi ikkitasi ishlagan (RSS
# tekshirilgan, real maqolalar bilan).
MANBALAR = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("CPA Practice Advisor", "https://www.cpapracticeadvisor.com/feed/"),
    ("AccountingWEB", "https://www.accountingweb.co.uk/rss.xml"),
]

HAR_MANBADAN_MAKS = 5   # bitta manbadan bir ishga tushirishda ko'rib chiqiladigan maks maqola soni
JAMI_XABAR_MAKS = 12    # ro'yxat-xabarida ko'rsatiladigan maks yangi maqola soni
KONTENT_UCHUN_MAKS = 3  # bir ishga tushirishda to'liq o'zbekcha post-loyihasi yoziladigan maks maqola soni


def log_yoz(matn):
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{vaqt}] {matn}\n")
    print(matn)


def holatni_ukish():
    if not os.path.exists(HOLAT_PATH):
        return None  # birinchi ishga tushirish
    try:
        with open(HOLAT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_yoz(f"OGOHLANTIRISH: holat fayli o'qilmadi ({e}), birinchi ishga tushirish deb hisoblanadi.")
        return None


def holatni_yozish(korilganlar):
    with open(HOLAT_PATH, "w", encoding="utf-8") as f:
        json.dump({"korilgan_havolalar": sorted(korilganlar)}, f, ensure_ascii=False, indent=2)


def telegram_xabar(matn):
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": config.OWNER_ID,
            "text": matn,
            "disable_web_page_preview": "true",
        }).encode()
        with urllib.request.urlopen(url, data=data, timeout=15) as r:
            r.read()
    except Exception as e:
        log_yoz(f"Telegram xabar yuborishda xato: {e}")


def kanalga_post_qoy(matn):
    """"Azizbek AI Agent" Telegram kanaliga (t.me/azizbek_ai_agent) TO'G'RIDAN-
    TO'G'RI post qo'yadi -- userbot/yubor.py orqali (Azizbekning shaxsiy
    Telethon sessiyasi, chunki kanal shu akkaunt bilan yaratilgan, oddiy
    Bot API bilan ega bo'lmagan kanalga yozib bo'lmaydi). Muvaffaqiyatli
    bo'lsa True, aks holda False qaytaradi (chaqiruvchi xato holatini
    Azizbekka alohida xabar qilishi kerak)."""
    try:
        natija = subprocess.run(
            [sys.executable, "yubor.py", str(AZIZBEK_AI_AGENT_CHAT_ID), "matn", matn],
            cwd=USERBOT_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        muvaffaqiyat = natija.returncode == 0 and "YUBORILDI" in (natija.stdout or "")
        if not muvaffaqiyat:
            log_yoz(f"XATO: kanalga post qo'yilmadi (returncode={natija.returncode}): {natija.stderr or natija.stdout}")
        return muvaffaqiyat
    except Exception as e:
        log_yoz(f"XATO: kanalga post qo'yishda kutilmagan xato: {e}")
        return False


def manbani_ukish(nomi, url):
    """Bitta RSS manbani o'qiydi, [(havola, sarlavha), ...] ro'yxatini qaytaradi
    (eng yangi HAR_MANBADAN_MAKS tasi). Xato bo'lsa bo'sh ro'yxat qaytaradi,
    boshqa manbalarga ta'sir qilmaydi."""
    try:
        # Ba'zi saytlar (masalan TechCrunch) User-Agent'siz so'rovni rad etadi.
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (JarvisAINewsBot)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xom = r.read()
        parsed = feedparser.parse(xom)
        natija = []
        for yozuv in parsed.entries[:HAR_MANBADAN_MAKS]:
            havola = getattr(yozuv, "link", None)
            sarlavha = getattr(yozuv, "title", "(sarlavhasiz)")
            if havola:
                natija.append((havola, sarlavha))
        return natija
    except Exception as e:
        log_yoz(f"OGOHLANTIRISH: '{nomi}' manbasi o'qilmadi: {e}")
        return []


async def _postloyihasi_yoz(manba_nomi, sarlavha, havola):
    """Jarvis (Claude Agent SDK) orqali shu maqola asosida o'zbekcha, biznes
    egalariga qaratilgan Telegram-post matnini yozadi ("Azizbek AI Agent"
    kanali ovoziga mos). Faqat matn yozadi -- hech qanday tashqi amalga
    (post qo'yish, fayl o'zgartirish) qo'l urmaydi, chunki bu yerda hech
    qanday vosita chaqirilishi so'ralmagan.

    2026-09-13, Azizbek namuna sifatida t.me/isroilabdullayev kanalini
    ko'rsatdi (6.75K obunachi, shaxsiy-brend uslubi) -- shu uslub tahlil
    qilinib (qisqa punchy paragraflar, bitta fikr = bitta qator, reaksiya
    uchun aniq chaqiriq, "biz" ovozi orqali ekspertizani ko'rsatish) quyidagi
    so'rovga singdirilgan."""
    soroq = (
        "Sen \"Azizbek AI Agent\" nomli Telegram kanali (t.me/azizbek_ai_agent) "
        "uchun kontent yozuvchisan. Kanal egasi Azizbek -- O'zbekistondagi kichik-"
        "o'rta bizneslar uchun AI agent/avtomatlashtirish yechimlari quruvchi "
        "mutaxassis (bir yo'nalishi -- buxgalteriya hisobi va audit jarayonlarini "
        "AI bilan avtomatlashtirish). Kanalning USLUBI namunaviy o'xshash "
        "kanaldan (t.me/isroilabdullayev, shaxsiy-brend, 6.75K obunachi) "
        "o'rganilgan: QISQA, PUNCHY paragraflar (har birida 1-2 gap, ko'p "
        "bo'sh qator bilan ajratilgan -- uzun tutash matn EMAS), ishonchli va "
        "samimiy \"biz\" ovozi, oxirida reaksiya/muhokamaga aniq chaqiriq "
        "(masalan savol berish yoki emoji bilan reaksiya so'rash).\n\n"
        "Quyidagi yangilik AI sohasidan YOKI buxgalteriya/moliya sohasidan "
        "bo'lishi mumkin (manba nomiga qara) -- ikkalasi ham kanal mavzusiga "
        "kiradi. O'ZBEK TILIDA, shu uslubda Telegram POST qilib yoz. Tuzilma: (1) qisqa, e'tiborni "
        "tortadigan hook-qator bilan boshlansin; (2) 2-4 ta QISQA paragrafda "
        "(har biri 1-2 gap) yangilikning mohiyatini tushuntir; (3) bu O'ZBEK "
        "biznes egalariga (ayniqsa moliya/buxgalteriya/audit kabi jarayonlarni "
        "avtomatlashtirishga qiziquvchilarga, lekin faqat mavzuga chindan mos "
        "kelsa -- zo'rlab bog'lama) NIMA UCHUN/QANDAY daxldor ekanini 1-2 "
        "qatorda yoz; (4) oxirida qisqa reaksiya-chaqiruv (savol yoki emoji "
        "bilan reaksiya so'rash) + manba havolasi. Murakkab texnik "
        "atamalardan qoch, oddiy so'zlashuv tilida yoz. "
        "FAQAT tayyor post matnini qaytar -- boshqa izoh, sarlavha yoki "
        "\"mana post\" kabi kirish so'zlarini qo'shma.\n\n"
        f"Manba: {manba_nomi}\nSarlavha: {sarlavha}\nHavola: {havola}"
    )
    async with Jarvis(log=False) as j:
        return await j.ask(soroq)


async def _engqiziqarlilarini_tanla(nomzodlar, maks_son):
    """2026-09-13, Azizbek aniq so'radi: "eng qiziqarlilarini" tanlab qo'yish
    kerak, oddiy xronologik tartib emas. Jarvis orqali nomzodlar (manba+
    sarlavha) ro'yxatidan eng muhim/qiziqarli (va Azizbekning sohasiga --
    AI agentlar, biznes avtomatlashtirish, buxgalteriya/audit -- alohida
    daxldor bo'lsa ustuvor) maks_son tasini tanlaydi. Nomzodlar soni
    maks_son'dan kam/teng bo'lsa, LLM chaqirilmaydi -- hammasi qaytariladi
    (xarajat/vaqtni tejash)."""
    if len(nomzodlar) <= maks_son:
        return nomzodlar

    royxat_matni = "\n".join(
        f"{i+1}. [{nomi}] {sarlavha}" for i, (nomi, sarlavha, havola) in enumerate(nomzodlar)
    )
    soroq = (
        f"Quyida {len(nomzodlar)} ta yangilik sarlavhasi berilgan -- manbalar ikki "
        f"turdan iborat: AI (sun'iy intellekt) sohasi VA buxgalteriya/moliya sohasi "
        f"(manba nomiga qarab bilib olasan). Sen \"Azizbek AI Agent\" Telegram kanali "
        f"uchun kontent strategisan. Kanal egasi Azizbek -- AI agent/biznes "
        f"avtomatlashtirish quruvchi mutaxassis (buxgalteriya hisobi/audit "
        f"yo'nalishiga alohida e'tibor bilan). Shu ro'yxatdan ENG QIZIQARLI va "
        f"OBUNACHILARGA FOYDALI {maks_son} tasini tanla -- ustuvorlik: (1) katta/muhim "
        f"yangilik (yangi model/funksiya, sezilarli o'zgarish, real amaliy ta'sir -- "
        f"oddiy tashkiliy/marketing xabarlaridan (masalan \"X kompaniya Y tadbirni "
        f"homiylik qildi\" kabi) ko'ra ANCHA ustuvor); (2) AI VA buxgalteriya "
        f"KESISHGAN mavzular (masalan \"AI buxgalteriyada qanday ishlatilmoqda\") "
        f"ENG YUQORI ustuvorlikka ega; (3) sof buxgalteriya/soliq yangiligi bo'lsa "
        f"ham, katta/amaliy ahamiyati bo'lsa tanlash mumkin. FAQAT tanlangan "
        f"raqamlarni vergul bilan ajratib qaytar (masalan: \"2,5,7\"), boshqa hech "
        f"narsa yozma.\n\n{royxat_matni}"
    )
    async with Jarvis(log=False) as j:
        javob = await j.ask(soroq)

    raqamlar = []
    for boʻlak in javob.replace(" ", "").split(","):
        try:
            i = int("".join(ch for ch in boʻlak if ch.isdigit())) - 1
            if 0 <= i < len(nomzodlar):
                raqamlar.append(i)
        except ValueError:
            continue

    if not raqamlar:
        # LLM javobini tahlil qilib bo'lmasa -- xavfsiz zaxira: birinchi maks_son tasi.
        log_yoz(f"OGOHLANTIRISH: tanlov javobini tahlil qilib bo'lmadi ({javob!r}), xronologik tartibga qaytildi.")
        return nomzodlar[:maks_son]

    tanlanganlar = [nomzodlar[i] for i in raqamlar[:maks_son]]
    log_yoz(f"Eng qiziqarlilari tanlandi: {[s for _, s, _ in tanlanganlar]}")
    return tanlanganlar


async def _kontent_loyihalarini_tayyorla(maqolalar):
    """Berilgan (manba, sarlavha, havola) ro'yxati uchun ketma-ket post yozadi
    (Jarvis bitta vaqtda faqat bitta ask()ni qo'llab-quvvatlaydi -- __init__'dagi
    lock'ga qara), har biri tayyor bo'lgach DARHOL "Azizbek AI Agent" kanaliga
    qo'yadi (avtomatik, Azizbekning 2026-09-13 aniq ruxsati bilan -- yuqoridagi
    modul docstring'iga qara), so'ng Azizbekka QISQA nazorat-xabari yuboradi
    (tasdiq so'ramaydi -- amal allaqachon bajarilgan). Bitta maqolada xato
    bo'lsa ham qolganlari davom etadi.

    2026-09-15: har postdan OLDIN UMUMIY kunlik limit (kanal_post_limiti.py,
    ai_yangiliklar+portfolio jami) tekshiriladi -- Azizbek "juda ko'p post,
    kuniga 3 ta yetarli" dedi. Limitga yetilgan maqolalar POST QILINMAYDI,
    o'rniga "post qilinmagan" deb qaytariladi (chaqiruvchi ularni ro'yxat
    sifatida Azizbekka ko'rsatadi, keyingi kunga qoladi)."""
    postqilinmagan = []
    for manba_nomi, sarlavha, havola in maqolalar:
        if kanal_post_limiti.limitga_yetdimi():
            log_yoz(f"Kunlik post-limitiga yetildi, '{sarlavha}' post qilinmadi (keyingi kunga qoladi).")
            postqilinmagan.append((manba_nomi, sarlavha, havola))
            continue

        try:
            postmatni = await _postloyihasi_yoz(manba_nomi, sarlavha, havola)
        except Exception as e:
            log_yoz(f"OGOHLANTIRISH: '{sarlavha}' uchun post yozilmadi: {e}")
            continue

        muvaffaqiyat = kanalga_post_qoy(postmatni)
        if muvaffaqiyat:
            son = kanal_post_limiti.postni_hisobla()
            telegram_xabar(
                f"✅ \"Azizbek AI Agent\" kanaliga yangi post avtomatik qo'yildi (manba: {manba_nomi}, "
                f"bugungi {son}/{kanal_post_limiti.KUNLIK_LIMIT}-post).\n\n{postmatni}"
            )
            log_yoz(f"Post yozildi va kanalga qo'yildi: [{manba_nomi}] {sarlavha} (bugungi {son}-post)")
        else:
            telegram_xabar(
                f"⚠️ AI-yangilik uchun post tayyor bo'ldi, LEKIN \"Azizbek AI Agent\" kanaliga "
                f"AVTOMATIK qo'yishda xato yuz berdi (manba: {manba_nomi}). Log faylini (ai_yangiliklar.log) "
                f"tekshiring. Tayyor matn:\n\n{postmatni}\n\n---\nAsl havola: {havola}"
            )
            log_yoz(f"XATO: post yozildi lekin kanalga qo'yilmadi: [{manba_nomi}] {sarlavha}")
    return postqilinmagan


def asosiy():
    log_yoz("--- AI yangiliklar tekshiruvi boshlandi ---")
    avvalgi_holat = holatni_ukish()
    birinchi_ishga_tushirish = avvalgi_holat is None
    korilgan = set(avvalgi_holat["korilgan_havolalar"]) if avvalgi_holat else set()

    yangi_maqolalar = []  # [(manba_nomi, sarlavha, havola), ...]
    barcha_havolalar = set(korilgan)

    for nomi, url in MANBALAR:
        maqolalar = manbani_ukish(nomi, url)
        for havola, sarlavha in maqolalar:
            barcha_havolalar.add(havola)
            if havola not in korilgan:
                yangi_maqolalar.append((nomi, sarlavha, havola))

    holatni_yozish(barcha_havolalar)

    if birinchi_ishga_tushirish:
        log_yoz(f"Birinchi ishga tushirish -- {len(barcha_havolalar)} ta maqola 'ko'rilgan' deb belgilandi, xabar yuborilmadi.")
        log_yoz("--- AI yangiliklar tekshiruvi tugadi ---")
        return

    if not yangi_maqolalar:
        log_yoz("Yangi maqola topilmadi.")
        log_yoz("--- AI yangiliklar tekshiruvi tugadi ---")
        return

    log_yoz(f"{len(yangi_maqolalar)} ta yangi maqola topildi.")

    # Xronologik tartib o'rniga -- Azizbek aniq so'ragan: eng qiziqarli/muhim
    # (va soham -- AI agentlar/biznes avtomatlashtirish/buxgalteriya -- ga
    # daxldor) KONTENT_UCHUN_MAKS tasi LLM orqali tanlanadi, faqat shulari
    # uchun to'liq post yoziladi (LLM xarajati/vaqtini cheklash uchun cheklangan).
    try:
        kontent_uchun = asyncio.run(_engqiziqarlilarini_tanla(yangi_maqolalar, KONTENT_UCHUN_MAKS))
    except Exception as e:
        log_yoz(f"OGOHLANTIRISH: tanlov bosqichida xato ({e}), xronologik tartibga qaytildi.")
        kontent_uchun = yangi_maqolalar[:KONTENT_UCHUN_MAKS]
    qolganlari = [m for m in yangi_maqolalar if m not in kontent_uchun]

    try:
        postqilinmagan = asyncio.run(_kontent_loyihalarini_tayyorla(kontent_uchun))
    except Exception as e:
        log_yoz(f"OGOHLANTIRISH: post-loyihalarini tayyorlashda kutilmagan xato: {e}")
        postqilinmagan = []

    # Kunlik limit tufayli post qilinmagan maqolalar ham "qolganlari"ga
    # qo'shiladi -- keyingi ishga tushirishda ular ham korilgan hisoblanmagani
    # uchun (holatni_yozish allaqachon hammasini "ko'rilgan" deb belgilagan),
    # hozircha faqat ro'yxat sifatida ko'rsatiladi (qayta avtomatik urinilmaydi).
    qolganlari = postqilinmagan + qolganlari

    # Qolgan yangi maqolalar (bo'lsa) -- faqat sarlavha+havola ro'yxati,
    # post-loyihasiz (keyinroq alohida so'ralsa ishlab chiqilishi mumkin).
    if qolganlari:
        korsatiladiganlar = qolganlari[:JAMI_XABAR_MAKS]
        qatorlar = [f"🤖 Yana {len(qolganlari)} ta yangi AI-maqola (post-loyihasiz, faqat ro'yxat):\n"]
        for nomi, sarlavha, havola in korsatiladiganlar:
            qatorlar.append(f"• [{nomi}] {sarlavha}\n{havola}")
        if len(qolganlari) > len(korsatiladiganlar):
            qatorlar.append(f"\n...va yana {len(qolganlari) - len(korsatiladiganlar)} ta.")
        telegram_xabar("\n\n".join(qatorlar))

    log_yoz("--- AI yangiliklar tekshiruvi tugadi ---")


if __name__ == "__main__":
    asosiy()
