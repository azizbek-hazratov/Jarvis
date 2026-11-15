"""
JARVIS OS — xodimlar o'z sohasida javob berishi uchun markazlashtirilgan
mantiq (2026-09-28 kechasi, Azizbek qoidasi: "HAR KIM O'Z SOHASIDA").

ASOSIY G'OYA: savol/topshiriq MATNI bo'yicha MAVZU aniqlanadi (kim
so'ralganidan qat'i nazar), keyin o'sha mavzuning HAQIQIY EGASI javob
beradi:
  - agar so'ralgan xodim = mavzu egasi bo'lsa -> to'g'ridan-to'g'ri javob
  - agar boshqa xodim bo'lsa -> "bu <egasi>ning ishi, unga beraman" +
    egasi o'z ovozida/nomidan javob beradi (ikki bosqichli javob)
  - agar mavzu HECH bir xodimga mos kelmasa (bizda bunday ma'lumot yo'q)
    -> "bu ma'lumot menda yo'q" (AI chaqirilmaydi, raqam to'qilmaydi)

Barcha handler'lar REAL ma'lumotdan foydalanadi (jarvis_jamoa_data, SSH+
jarvis_readonly, log fayllar) -- hech qanday son qattiq yozilmagan.
"""

import re
import shlex
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import config
import jarvis_jamoa_data as jjd

BASE = Path(__file__).parent
TASHKENT_OFFSET = timedelta(hours=5)


def _hozir() -> datetime:
    return datetime.utcnow() + TASHKENT_OFFSET


def _oy_str() -> str:
    return _hozir().strftime("%Y-%m")


# ---------------------------------------------------------------------------
# SSH + jarvis_readonly (jarvis_nozima_hisobot.py bilan BIR XIL, sinalgan naqsh)
# ---------------------------------------------------------------------------
def _ssh_psql(db_host: str, db_name: str, db_user: str, db_password: str, sql: str) -> str:
    remote_cmd = (
        f"PGPASSWORD={shlex.quote(db_password)} "
        f"psql -h {db_host} -U {db_user} -d {db_name} -t -A -F'|' -c {shlex.quote(sql)}"
    )
    cmd = [
        "ssh", "-i", config.HETZNER_NISHON_SERVER_SSH_KEY,
        "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15",
        f"root@{config.HETZNER_NISHON_SERVER_IP}", remote_cmd,
    ]
    kwargs = {}
    import sys
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    natija = subprocess.run(cmd, capture_output=True, text=True, timeout=25, **kwargs)
    if natija.returncode != 0:
        raise RuntimeError(natija.stderr.strip()[:300])
    return natija.stdout.strip()


def _royxat_parse(qatorlar: str) -> list[tuple[str, str]]:
    natija = []
    for q in qatorlar.splitlines():
        if "|" not in q:
            continue
        guruh, ism = q.split("|", 1)
        natija.append((guruh.strip(), ism.strip()))
    return natija


def _azizedu_royxat(oy: str) -> list[tuple[str, str]]:
    sql = f"""SELECT COALESCE(g.nomi, 'Guruhsiz'), o.ism
FROM oquvchilar o
LEFT JOIN guruhlar g ON g.id = o.guruh_id
WHERE o.organization_id='{config.AZIZEDU_ORG_ID}' AND o.faol=true
AND o.id NOT IN (SELECT oquvchi_id FROM tolovlar WHERE oy='{oy}' AND holat='tolangan')
ORDER BY 1, 2"""
    qatorlar = _ssh_psql(config.AZIZEDU_DB_HOST, config.AZIZEDU_DB_NAME, config.AZIZEDU_DB_USER, config.AZIZEDU_DB_PASSWORD, sql)
    return _royxat_parse(qatorlar)


def _grampus_royxat(oy: str) -> list[tuple[str, str]]:
    sql = f"""SELECT COALESCE(f.nomi, 'Filialsiz'), s.ism
FROM sportchilar s
LEFT JOIN filiallar f ON f.id = s.filial_id
WHERE s.organization_id='{config.GRAMPUS_ORG_ID}' AND s.ochirilgan_sana IS NULL
AND s.id NOT IN (SELECT sportchi_id FROM tolov_holatlari WHERE oy='{oy}' AND holati='tolandi')
ORDER BY 1, 2"""
    qatorlar = _ssh_psql(config.GRAMPUS_DB_HOST, config.GRAMPUS_DB_NAME, config.GRAMPUS_DB_USER, config.GRAMPUS_DB_PASSWORD, sql)
    return _royxat_parse(qatorlar)


def _royxat_matni(royxat: list[tuple[str, str]]) -> str:
    guruhlar: dict[str, list[str]] = {}
    for guruh, ism in royxat:
        guruhlar.setdefault(guruh, []).append(ism)
    qismlar = []
    for guruh, ismlar in guruhlar.items():
        qismlar.append(f"{guruh} ({len(ismlar)}): " + ", ".join(ismlar))
    return "\n".join(qismlar)


# ---------------------------------------------------------------------------
# NOZIMA -- to'lovlar, qarzdorlar, hisobotlar (AzizEdu, Nishon/Grampus)
# ---------------------------------------------------------------------------
def nozima_royxat_javobi(matn: str) -> dict:
    matnl = (matn or "").lower()
    azizedu_kerak = any(k in matnl for k in ("orzu", "azizedu", "aziz edu"))
    grampus_kerak = "grampus" in matnl
    if not azizedu_kerak and not grampus_kerak:
        azizedu_kerak = grampus_kerak = True

    oy = _oy_str()
    ekran_qismlar = []
    ovoz_qismlar = []
    xato = False
    try:
        if azizedu_kerak:
            royxat = _azizedu_royxat(oy)
            ekran_qismlar.append(f"AzizEdu (Orzu Akademy) — tizimda to'lovi yozilmagan ({len(royxat)} kishi):\n" + (_royxat_matni(royxat) or "(yo'q)"))
            birinchi5 = [ism for _, ism in royxat[:5]]
            ovoz_qismlar.append(f"Aziz Edu'da {len(royxat)} kishida tizimda to'lovi yozilmagan" + (f", birinchi beshtasi: {', '.join(birinchi5)}" if birinchi5 else ""))
        if grampus_kerak:
            royxat = _grampus_royxat(oy)
            ekran_qismlar.append(f"Grampus Junior FC — tizimda to'lovi yozilmagan ({len(royxat)} kishi):\n" + (_royxat_matni(royxat) or "(yo'q)"))
            birinchi5 = [ism for _, ism in royxat[:5]]
            ovoz_qismlar.append(f"Grampus'da {len(royxat)} kishida tizimda to'lovi yozilmagan" + (f", birinchi beshtasi: {', '.join(birinchi5)}" if birinchi5 else ""))
    except Exception as e:
        xato = True
        ekran_qismlar.append(f"⚠️ Real vaqtda bazaga ulanib bo'lmadi: {e}")
        ovoz_qismlar.append("kechirasiz, hozir bazaga ulanib bo'lmadi")

    ekran = "\n\n".join(ekran_qismlar)
    # 2026-09-28 — "Gapirish uslubi" talabi: 1-shaxs, "Azizbek aka" bilan
    # boshlanadi, texnik so'zsiz, oxiri taklif bilan tugaydi (Kamola/Instagram
    # voqeasidan keyin BARCHA xodimlarga qo'llanadigan yagona uslub).
    if xato:
        ovoz = "Azizbek aka, " + ". ".join(ovoz_qismlar) + " — birozdan so'ng qayta urinib ko'raman."
    else:
        ovoz = "Azizbek aka, " + ". ".join(ovoz_qismlar) + ". To'liq ro'yxatni ko'rsataymi?"
    return {"ekran": ekran, "ovoz": ovoz, "xato": xato}


def nozima_grampus_soni_javobi(matn: str) -> dict:
    try:
        sql = f"SELECT COUNT(*) FROM sportchilar WHERE organization_id='{config.GRAMPUS_ORG_ID}' AND ochirilgan_sana IS NULL"
        soni = int(_ssh_psql(config.GRAMPUS_DB_HOST, config.GRAMPUS_DB_NAME, config.GRAMPUS_DB_USER, config.GRAMPUS_DB_PASSWORD, sql))
        return {"ekran": f"Grampus Junior FC'da hozir {soni} ta faol sportchi bor.", "ovoz": f"Azizbek aka, Grampus'da hozir {soni} ta faol sportchi bor. Boshqa narsa kerakmi?", "xato": False}
    except Exception as e:
        return {"ekran": f"⚠️ Real vaqtda bazaga ulanib bo'lmadi: {e}", "ovoz": "Azizbek aka, kechirasiz, hozir bazaga ulanib bo'lmadi — birozdan so'ng qayta urinib ko'raman.", "xato": True}


# ---------------------------------------------------------------------------
# SAMANDAR -- lidlar va suhbatlar (Instagram/Telegram sotuv)
# ---------------------------------------------------------------------------
def samandar_lidlar_javobi(matn: str) -> dict:
    bugun = jjd._bugun_str()
    m = jjd._samandar_malumot(bugun)
    ekran = f"Bugun {m['soni']} ta suhbat bo'ldi, shulardan {m['lead_soni']} tasi yangi qiziquvchi (ism+telefon) qoldirdi."
    if m["lead_soni"]:
        ovoz = f"Azizbek aka, bugun {m['lead_soni']} ta yangi lid keldi, jami {m['soni']} ta suhbat bo'ldi. Ro'yxatini ko'rsataymi?"
    else:
        ovoz = f"Azizbek aka, bugun {m['soni']} ta suhbat bo'ldi, lekin yangi lid hali yo'q. Kuzatishda davom etayapman."
    return {"ekran": ekran, "ovoz": ovoz, "xato": False}


# ---------------------------------------------------------------------------
# SARDOR -- backup, server, xavfsizlik
# ---------------------------------------------------------------------------
def sardor_holati_javobi(matn: str) -> dict:
    bugun = jjd._bugun_str()
    m = jjd._sardor_malumot(bugun)
    ekran = (
        f"Zaxira nusxa holati: {m['backup_matn']}.\n"
        f"AzizEdu+Grampus kuzatuvi: {m['status_text']}.\n"
        f"Bugungi g'ayrioddiy holatlar soni: {m['ogohlantirish_soni']}."
    )
    if m["ogohlantirish_soni"]:
        ovoz = f"Azizbek aka, {m['backup_matn']}. Bugun {m['ogohlantirish_soni']} ta g'ayrioddiy holat qayd etdim — batafsilini ko'rsataymi?"
    else:
        ovoz = f"Azizbek aka, {m['backup_matn']}. Hech qanday g'ayrioddiy holat yo'q, hammasi tinch."
    return {"ekran": ekran, "ovoz": ovoz, "xato": False}


# ---------------------------------------------------------------------------
# BEKZOD -- botlar va watchdoglar (2026-09-28: avval "Doktor" deb atalgan)
# ---------------------------------------------------------------------------
def bekzod_botlar_javobi(matn: str) -> dict:
    bugun = jjd._bugun_str()
    m = jjd._bekzod_malumot(bugun)
    sam = jjd._samandar_malumot(bugun)
    dst = jjd._malika_malumot(bugun)

    def holat_matni(farq):
        if farq is None:
            return "holati noma'lum"
        if farq < 15:
            return f"tirik ({int(farq)} daqiqa oldin javob bergan)"
        return f"⚠️ {int(farq)} daqiqadan beri javob yo'q"

    ogohlantirish_matni = ", ".join(m["ogohlantirishlar"]) if m["ogohlantirishlar"] else "yo'q"
    ekran = (
        f"Asosiy Jarvis: {'tirik' if m['asosiy_tirik'] else '⚠️ heartbeat eskirgan'}.\n"
        f"AI Expert bot (Samandar): {holat_matni(sam['farq'])}.\n"
        f"JetCafe bot (Malika): {holat_matni(dst['farq'])}.\n"
        f"Bugungi avtomatik tiklashlar: {m['toxtash_bugun']}. Ochiq ogohlantirish: {ogohlantirish_matni}."
    )
    muammo = m["ogohlantirishlar"] or (sam["farq"] is not None and sam["farq"] >= 15) or (dst["farq"] is not None and dst["farq"] >= 15)
    ovoz = ("Azizbek aka, barcha botlar tinch ishlayapti, muammo yo'q." if not muammo
            else f"Azizbek aka, diqqat, {', '.join(m['ogohlantirishlar']) if m['ogohlantirishlar'] else 'bir bot'}da muammo bor — hoziroq tekshirib ko'raymi?")
    return {"ekran": ekran, "ovoz": ovoz, "xato": False}


# ---------------------------------------------------------------------------
# MALIKA -- restoran bot suhbatlari (JetCafe) (2026-09-28: avval "Dasturxon"
# deb atalgan -- "Dasturxon" endi FAQAT restoranning nomi)
# ---------------------------------------------------------------------------
def malika_buyurtma_javobi(matn: str) -> dict:
    """2026-09-28 (Azizbek tuzatishi): "buyurtma" mavzusi Sardor (backup/
    server) yoki Bekzod (botlar) EMAS -- Malikaning ishi (restoran mijozlari
    va buyurtmalar). Hozircha buyurtmalar bo'yicha REAL ulangan ma'lumot
    manbasi yo'q -- shuning uchun HALOL "ma'lumot yo'q" javob beriladi,
    raqam TO'QILMAYDI, faqat EGASI to'g'ri ko'rsatiladi."""
    ekran = "Buyurtmalar bo'yicha hozircha real ma'lumot manbasi ulanmagan."
    ovoz = "Azizbek aka, buyurtmalar bo'yicha hozircha aniq ma'lumotim yo'q — bu ma'lumot manbasini ulab qo'yishimni xohlaysizmi?"
    return {"ekran": ekran, "ovoz": ovoz, "xato": False}


def malika_mijozlar_javobi(matn: str) -> dict:
    bugun = jjd._bugun_str()
    m = jjd._malika_malumot(bugun)
    # Haqiqiy log FAQAT "XABAR keldi"/"JAVOB berildi" belgilarini saqlaydi,
    # mijozning ANIQ savol matnini saqlamaydi -- shuning uchun HALOL javob:
    # sonlarni beramiz, lekin savol MAZMUNINI "yo'q" deb aytamiz (to'qib
    # chiqarmaymiz).
    ekran = (
        f"Bugun {m['soni']} ta mijoz savoliga javob berildi"
        + (f", {m['toxtash_soni']} marta aloqa vaqtincha uzilib, o'zi tiklandi" if m["toxtash_soni"] else "")
        + ".\nSavollarning ANIQ matni log faylda saqlanmaydi (faqat soni), shuning uchun \"nima haqida\" so'ralganini bu yerda ko'rsata olmayman."
    )
    ovoz = f"Azizbek aka, bugun {m['soni']} ta mijoz savoliga javob berdim. Savollarning aniq matnini hozircha saqlamayapmiz, faqat sonini bilaman — xohlasangiz buni ham yozib borishni yo'lga qo'yaman."
    return {"ekran": ekran, "ovoz": ovoz, "xato": False}


# ---------------------------------------------------------------------------
# KAMOLA -- marketing, kontent-reja (qoralama, hech narsa post qilinmaydi)
# ---------------------------------------------------------------------------
KAMOLA_REJA_FAYL = BASE / "jarvis_hud" / "kamola_reja.json"


def kamola_reja_javobi(matn: str) -> dict:
    import json
    try:
        data = json.loads(KAMOLA_REJA_FAYL.read_text(encoding="utf-8"))
    except Exception:
        return {"ekran": "Hali haftalik reja tayyorlanmagan.", "ovoz": "Azizbek aka, hali haftalik rejam tayyor emas — hoziroq tayyorlashni boshlaymi?", "xato": False}

    qismlar = []
    for kanal in data.get("kanallar", []):
        qismlar.append(f"{kanal['nomi']}:\n" + "\n".join(f"  • {p}" for p in kanal.get("postlar", [])))
    ekran = "\n\n".join(qismlar)
    soni = sum(len(k.get("postlar", [])) for k in data.get("kanallar", []))
    ovoz = f"Azizbek aka, bu hafta uchun {soni} ta post qoralamasi tayyorladim — {', '.join(k['nomi'] for k in data.get('kanallar', []))} uchun. Hech birini o'zim joylamayman, ko'rib chiqib tasdiqlaysizmi?"
    return {"ekran": ekran, "ovoz": ovoz, "xato": False}


# ---------------------------------------------------------------------------
# MAVZU -> EGASI + HANDLER ro'yxati (tartib muhim -- birinchi mos kelgani ishlaydi)
# ---------------------------------------------------------------------------
_MAVZULAR = [
    # (regex, egasi_xodim_id, handler)
    (re.compile(r"grampus.*(faol sportchi|sportchi soni|nechta sportchi)", re.IGNORECASE), "nozima", nozima_grampus_soni_javobi),
    (re.compile(r"qarizdor|qarzdor|to'lov\w*\s*yoz\w*magan|to'lamagan|kim to'la|kim.*to'lov", re.IGNORECASE), "nozima", nozima_royxat_javobi),
    # 2026-09-29 (Azizbek xato-tuzatishi, band 4): "moliyaviy ahvol/hisobot/
    # to'lov/tushum" so'zlari oldin HECH bir xodimga mos kelmay, AI'ga tushib
    # ketardi (masalan "moliyaviy ahvolimiz haqida hisobot ber"). Bizda
    # umumiy tushum/foyda bo'yicha real ma'lumot manbasi yo'q, lekin
    # to'lov/qarzdorlik bo'yicha BOR (nozima_royxat_javobi, AzizEdu+Grampus,
    # SQL) -- shuning uchun bu so'zlar ham shu real-ma'lumot handleriga.
    (re.compile(r"moliyaviy\s*(ahvol|holat)|moliya\w*\s*hisobot|to'lov\w*\s*hisobot|hisobot.*to'lov\w*", re.IGNORECASE), "nozima", nozima_royxat_javobi),
    (re.compile(r"\blid\w*|qiziquvchi|lead", re.IGNORECASE), "samandar", samandar_lidlar_javobi),
    (re.compile(r"zaxira|backup|nusxa|server\b|xavfsizlik", re.IGNORECASE), "sardor", sardor_holati_javobi),
    (re.compile(r"\bbot\w*\s*(holat\w*|ishla\w*)|watchdog|holat\w*\s*qanday|hamma\s*ishlayap\w*", re.IGNORECASE), "bekzod", bekzod_botlar_javobi),
    (re.compile(r"buyurtma\w*\s*(holat\w*|nech\w*|qancha)|nech\w*\s*(ta\s*)?buyurtma", re.IGNORECASE), "malika", malika_buyurtma_javobi),
    (re.compile(r"mijoz\w*.*so'ra|nima\s*so'ra|restoran|jetcafe|menyu", re.IGNORECASE), "malika", malika_mijozlar_javobi),
    (re.compile(r"post|kontent|marketing|reja\b", re.IGNORECASE), "kamola", kamola_reja_javobi),
]

# Bizda UMUMAN kuzatilmaydigan mavzular (aniq "ma'lumot yo'q" uchun, AI
# chaqirilmasin -- xato/xalq bo'lib raqam to'qib chiqarish xavfi yo'qolsin).
_NOMALUM_MAVZULAR = re.compile(
    r"kofe|qahva|taom|osh\b|menyudagi\s*narx|nechta\s*stol|"
    r"ombordagi|sklad|inventar|tushum|foyda\b|xarajat",
    re.IGNORECASE,
)


def aniqla(matn: str):
    """Matn qaysi mavzuga tegishli ekanini aniqlaydi.
    Qaytaradi: (egasi_xodim_id, handler) yoki None (mavzu topilmadi)."""
    for naqsh, egasi, handler in _MAVZULAR:
        if naqsh.search(matn or ""):
            return egasi, handler
    return None


def malumot_yoqmi(matn: str) -> bool:
    return bool(_NOMALUM_MAVZULAR.search(matn or ""))
