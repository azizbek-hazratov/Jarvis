"""
JARVIS OS — "AI Xodimlar" uchun UMUMIY ma'lumot-yig'uvchi modul (5-bosqich,
2026-09-27).

MAQSAD: Telegram'dagi "jamoa" buyrug'i (`jarvis_jamoa_hisobot.py`) VA HUD'dagi
yangi "Jamoa" paneli (`jarvis_hud/jamoa.html` + bridge'dagi `GET /jamoa`)
BITTA umumiy ma'lumot-yig'uvchi funksiyalardan (shu fayl) foydalanadi — har
ikkalasi ham xuddi shu logларни/heartbeat/JSON fayllarni faqat BIR MARTA
o'qiydi, keyin har biri o'ziga kerakli formatga (Telegram uchun qisqa matn,
HUD uchun struktura+ovoz matni) chiqaradi.

QOIDA (Nozima bilan bir xil): bu yerda ham AI (Claude) UMUMAN ishlatilmaydi —
faqat fayl o'qish/vaqt solishtirish/oddiy sanash. Tez va deterministik
bo'lishi kerak, chunki HUD uni har 15 soniyada so'rайdi.

Hech qanday raqam qattiq yozilmagan (hardcode qilinmagan) — barchasi real
fayllardan hisoblanadi. Tarixiy kunlik grafik uchun alohida fayl yo'q joyda
(masalan Nozima — haftalik) FAQAT hozirgi haqiqiy qiymat 7 marta takrorlanadi
(soxta tarix TO'QILMAYDI, shunchaki o'zgarish yo'qligi ko'rsatiladi).
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).parent
TASHKENT_OFFSET = timedelta(hours=5)
_SANA_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


# ---------------------------------------------------------------------------
# Umumiy yordamchi funksiyalar
# ---------------------------------------------------------------------------
def _hozir() -> datetime:
    return datetime.utcnow() + TASHKENT_OFFSET


def _bugun_str() -> str:
    return _hozir().strftime("%Y-%m-%d")


def _fayl_oqi(yol: Path, standart: str = "") -> str:
    try:
        return yol.read_text(encoding="utf-8")
    except Exception:
        return standart


def _json_oqi(yol: Path):
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except Exception:
        return None


def _daqiqa_farqi(vaqt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> float | None:
    try:
        vaqt = datetime.strptime(vaqt_str, fmt)
    except Exception:
        return None
    return (_hozir() - vaqt).total_seconds() / 60.0


def _oxirgi_kunlar(n: int = 7) -> list[str]:
    """Bugundan orqaga qarab n ta kun (ESKIDAN YANGIGA, oxirgisi bugun)."""
    return [(_hozir() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n - 1, -1, -1)]


def _kunlik_hisoblagich(qatorlar: list[str], n: int = 7) -> list[int]:
    """Berilgan (allaqachon kerakli kalit so'z bo'yicha filtrlangan) log
    qatorlarini sanaydi — har qatordan BIRINCHI uchragan YYYY-MM-DD sanani
    olib, oxirgi `n` kun bo'yicha kunlik sonini qaytaradi (eskidan yangiga)."""
    hisob: dict[str, int] = {}
    for q in qatorlar:
        m = _SANA_RE.search(q)
        if not m:
            continue
        sana = m.group(1)
        hisob[sana] = hisob.get(sana, 0) + 1
    return [hisob.get(k, 0) for k in _oxirgi_kunlar(n)]


def _bugun_soni(qatorlar: list[str], bugun: str) -> int:
    return sum(1 for q in qatorlar if bugun in q)


# ---------------------------------------------------------------------------
# Xodimlar registri — statik metama'lumot (ovoz, rang, avtonomiya, real jarayon).
# Bu qism ATAYLAB qattiq yozilgan (ism/rol/ovoz o'zgarmaydi), lekin HECH QANDAY
# KUNLIK/HOZIRGI RAQAM shu yerda YO'Q — ular har doim funksiyalar orqali hisoblanadi.
# ---------------------------------------------------------------------------
XODIMLAR = {
    "jarvis": {
        "id": "jarvis", "name": "Jarvis", "role": "Bosh koordinator",
        "ini": "J", "col": "#22d3ee", "lead": True, "ladder": 2,
        "voice": "uz-UZ-SardorNeural", "rate": "+0%", "pitch": "-2Hz",
        "can": "Topshiriqlarni xodimlarga taqsimlaydi, kod yozadi, deploy tayyorlaydi",
        "cannot": "Sizning tasdig'ingizsiz production'ga yozmaydi, pul/o'chirish/ommaviy post qilmaydi",
        "real": "jarvis_fon.py · Telegram",
    },
    "samandar": {
        "id": "samandar", "name": "Samandar", "role": "Sotuvchi · Instagram va Telegram",
        "ini": "S", "col": "#60a5fa", "ladder": 3,
        "voice": "uz-UZ-SardorNeural", "rate": "+12%", "pitch": "+4Hz",
        "can": "DM'larga 24/7 javob beradi, ism va raqam yig'adi, lidni sizga yuboradi",
        "cannot": "Narx va chegirma va'da qilmaydi, fayl/Bash vositalariga kira olmaydi",
        "real": "ai_expert_bot/bot.py · @samandarakajonbot",
    },
    "malika": {
        "id": "malika", "name": "Malika", "role": "Mijoz operatori — Dasturxon restorani",
        "ini": "M", "col": "#f59e0b", "ladder": 3,
        "voice": "uz-UZ-MadinaNeural", "rate": "+0%", "pitch": "+0Hz",
        "can": "Menyu, manzil, ish vaqti bo'yicha javob beradi",
        "cannot": "Buyurtmani tasdiqlamaydi, narxni o'zgartirmaydi, to'lov qabul qilmaydi",
        "real": "jetcafe_bot/bot.py · watchdog bilan",
    },
    "sardor": {
        "id": "sardor", "name": "Sardor", "role": "Nazoratchi",
        "ini": "S", "col": "#34d399", "ladder": 2,
        "voice": "uz-UZ-SardorNeural", "rate": "-6%", "pitch": "-6Hz",
        "can": "Ma'lumotlarni faqat o'qiydi, g'ayrioddiy o'zgarishda ogohlantiradi",
        "cannot": "Hech narsani o'zgartirmaydi (jarvis_readonly — SQL darajasida ham yozib bo'lmaydi)",
        "real": "jarvis_readonly · Task Scheduler (har soat + har kuni 08:30)",
    },
    "bekzod": {
        "id": "bekzod", "name": "Bekzod", "role": "Tizim muhandisi — botlar va serverlar nazorati",
        "ini": "B", "col": "#f472b6", "ladder": 3,
        "voice": "uz-UZ-SardorNeural", "rate": "-10%", "pitch": "-9Hz",
        "can": "Qotib qolgan botni topib qayta ishga tushiradi, sizga xabar beradi",
        "cannot": "Fon ish bor paytda Jarvisni restart qilmaydi, kodni o'zgartirmaydi",
        "real": "jarvis_watchdog.py · heartbeat",
    },
    "nozima": {
        "id": "nozima", "name": "Nozima", "role": "Buxgalter",
        "ini": "N", "col": "#c084fc", "ladder": 3,
        "voice": "uz-UZ-MadinaNeural", "rate": "-6%", "pitch": "+2Hz",
        "can": "To'lovlarni faqat o'qiydi, qarzdorlar ro'yxatini tayyorlaydi",
        "cannot": "Ota-onalarga o'zi yozmaydi, pulga tegmaydi, AI ishlatmaydi",
        "real": "jarvis_readonly · SQL, AI'siz (har dushanba 09:00)",
    },
    "kamola": {
        "id": "kamola", "name": "Kamola", "role": "Marketolog",
        "ini": "K", "col": "#a78bfa", "ladder": 2,
        "voice": "uz-UZ-MadinaNeural", "rate": "+4%", "pitch": "+1Hz",
        "can": "@azizbekhazratov.ai, AzizEdu va Nishon uchun haftalik kontent-reja va post qoralamasi tayyorlaydi",
        "cannot": "Hech narsani o'zi post qilmaydi/joylamaydi — hammasi qoralama, tasdiq kerak",
        "real": "jarvis_hud/kamola_reja.json (qoralama, AI'siz)",
    },
}
XODIM_TARTIBI = ["jarvis", "samandar", "malika", "sardor", "bekzod", "nozima", "kamola"]


# ---------------------------------------------------------------------------
# 2026-09-28 (Azizbek imtihon-tuzatishi): STT buzilgan/vergulsiz xodim
# ismini aniqlash -- BITTA umumiy joy. Avval bu mantiq FAQAT
# jarvis_hud_bridge.py'da (jamoa.html paneli uchun) bor edi, Telegram ovozli
# yo'li (jarvis_xodim_telegram.xodimga_murojaatmi) esa ANIQ, qat'iy nom
# talab qilardi ("Nozima," aniq shu shaklda) -- shuning uchun "begzod",
# "nazima" kabi STT xatolari yoki vergulsiz murojaat ("begzodbotlar
# ishlayaptimi") Telegram ovozli xabarda UMUMAN ishlamas edi. Endi
# ikkalasi ham shu BITTA funksiyadan foydalanadi.
_XODIM_ISM_VARIANTLARI = {
    "bekzod": ["bekzod", "begzod", "bekzot", "bekzat"],
    "nozima": ["nozima", "nazima", "nozim"],
    "malika": ["malika", "malik"],
    "samandar": ["samandar aka", "samandar"],
    "sardor": ["sardor", "sardar"],
    "kamola": ["kamola", "kamala"],
}


def xodim_ismini_top(matn: str):
    """Gap boshidagi xodim ismini VERGULSIZ, hatto keyingi so'zga
    YOPISHIB ketgan bo'lsa ham (masalan "begzodbotlar" -> ("bekzod",
    "botlar")) aniqlaydi. Qaytaradi: (xodim_id, qolgan_savol) yoki None.

    2026-09-28 (imtihon paytida topilgan xato): avval bu yerda "ma'lum
    variantlar"dan keyin QO'SHIMCHA fuzzy (difflib) zaxira ham bor edi --
    lekin u soxta-mos topib qoldi (masalan "kamolotga erishish kerak"
    "Kamola"ga mos deb topildi, chunki so'zni uzunlik bo'yicha KESIB
    solishtirgan, so'z chegarasini hisobga olmagan). Aniq bilingan
    variantlar ro'yxati (pastda) real STT xatolarining HAMMASINI qamrab
    oladi -- shuning uchun noaniq fuzzy zaxira olib tashlandi, faqat
    ANIQ ro'yxat qoldi (soxta-mos xavfi yo'q)."""
    asl = (matn or "").strip()
    if not asl:
        return None
    past = asl.lower()

    barcha_variantlar = sorted(
        ((v, xid) for xid, vlar in _XODIM_ISM_VARIANTLARI.items() for v in vlar),
        key=lambda t: -len(t[0]),
    )
    for variant, xid in barcha_variantlar:
        if past.startswith(variant):
            qolgan = asl[len(variant):].strip(" \t,:;-–—")
            if qolgan:
                return xid, qolgan
    return None


# ---------------------------------------------------------------------------
# Samandar — AI Expert bot
# ---------------------------------------------------------------------------
def _samandar_malumot(bugun: str) -> dict:
    heartbeat = _json_oqi(BASE / "mijozlar" / "ai_expert_bot" / "heartbeat_ai_expert.json")
    farq = _daqiqa_farqi(heartbeat["last_ok"]) if heartbeat and heartbeat.get("last_ok") else None
    if farq is None:
        status, status_text = "bad", "❓ noma'lum"
    elif farq < 15:
        status, status_text = "ok", "✅ ishlayapti"
    else:
        status, status_text = "warn", f"⚠️ {int(farq)} daqiqadan beri javob yo'q"

    log_matni = _fayl_oqi(BASE / "mijozlar" / "ai_expert_bot" / "bot.log")
    xabar_qatorlar = [q for q in log_matni.splitlines() if "XABAR keldi" in q]
    soni = _bugun_soni(xabar_qatorlar, bugun)
    spark = _kunlik_hisoblagich(xabar_qatorlar)

    leads_matni = _fayl_oqi(BASE / "mijozlar" / "ai_expert_bot" / "leads.txt")
    lead_qatorlar = [q for q in leads_matni.splitlines() if q.strip()]
    lead_soni = sum(1 for q in lead_qatorlar if q.startswith(bugun))

    return {
        "status": status, "status_text": status_text, "soni": soni,
        "lead_soni": lead_soni, "spark": spark, "farq": farq,
    }


def samandar_telegram_matn(bugun: str) -> str:
    m = _samandar_malumot(bugun)
    return f"🧑‍💼 *Samandar* (sotuvchi): {m['status_text']} — bugun {m['soni']} ta xabarga javob berdi."


def samandar_karta(bugun: str) -> dict:
    m = _samandar_malumot(bugun)
    hozir = (
        "Yangi xabarlarni kutyapti. Narx so'raganlarga Azizbekning raqamini beradi."
        if m["status"] == "ok" else f"{m['status_text']}."
    )
    say = (
        f"Salom, Azizbek aka! Men Samandar, mijozlar bilan suhbatlashaman. "
        f"Bugun {m['soni']} ta suhbat bo'ldi"
        + (f", shulardan {m['lead_soni']} tasi yangi qiziquvchi qoldirdi." if m["lead_soni"] else ", lekin yangi qiziquvchi hali yo'q.")
        + " Narx so'raganlarga sizning raqamingizni beryapman."
        + (" Tavsiyam: yangi qiziquvchilar bilan tezroq bog'lansangiz yaxshi bo'lardi." if m["lead_soni"] else "")
    )
    batafsil = (
        f"Bugungi suhbatlar soni: {m['soni']}. Yangi qiziquvchi (ism+telefon aniqlangan): {m['lead_soni']}. "
        f"Holat: {m['status_text']}"
        + (f" (oxirgi javobdan {int(m['farq'])} daqiqa o'tgan)." if m["farq"] is not None else ".")
    )
    return {
        "status": m["status"], "status_text": m["status_text"], "hozir": hozir,
        "metrics": [(m["soni"], "bugun suhbat"), (m["lead_soni"], "yangi lid"), (sum(m["spark"]), "7 kunlik suhbat")],
        "spark": m["spark"], "say": say, "batafsil": batafsil,
    }


# ---------------------------------------------------------------------------
# Malika — JetCafe bot (2026-09-28: avval "Dasturxon" deb atalgan, Azizbek
# xodimlarga odamdek murojaat qilish uchun ismini almashtirdi -- "Dasturxon"
# so'zi endi FAQAT restoranning nomi, xodim EMAS)
# ---------------------------------------------------------------------------
def _malika_malumot(bugun: str) -> dict:
    heartbeat = _json_oqi(BASE / "mijozlar" / "jetcafe_bot" / "heartbeat_jetcafe.json")
    farq = _daqiqa_farqi(heartbeat["heartbeat_vaqti"]) if heartbeat and heartbeat.get("heartbeat_vaqti") else None
    if farq is None:
        status, status_text = "bad", "❓ noma'lum"
    elif farq < 15:
        status, status_text = "ok", "✅ ishlayapti"
    else:
        status, status_text = "warn", f"⚠️ {int(farq)} daqiqadan beri javob yo'q"

    log_matni = _fayl_oqi(BASE / "mijozlar" / "jetcafe_bot" / "bot.log")
    qatorlar = log_matni.splitlines()
    xabar_qatorlar = [q for q in qatorlar if "XABAR keldi" in q]
    soni = _bugun_soni(xabar_qatorlar, bugun)
    toxtash_qatorlar = [q for q in qatorlar if "To'xtadi:" in q]
    toxtash_soni = _bugun_soni(toxtash_qatorlar, bugun)
    spark = _kunlik_hisoblagich(xabar_qatorlar)

    return {
        "status": status, "status_text": status_text, "soni": soni,
        "toxtash_soni": toxtash_soni, "spark": spark, "farq": farq,
    }


def malika_telegram_matn(bugun: str) -> str:
    m = _malika_malumot(bugun)
    return f"🍽️ *Malika* (mijoz operatori): {m['status_text']} — bugun {m['soni']} ta xabarga javob berdi."


def malika_karta(bugun: str) -> dict:
    m = _malika_malumot(bugun)
    hozir = "Restoran mijozlarining savollariga javob beradi." if m["status"] == "ok" else f"{m['status_text']}."
    say = (
        f"Salom, Azizbek aka! Men Malika, restoran mijozlariga javob beraman. "
        f"Bugun {m['soni']} ta savolga javob berdim."
        + (f" Aloqa bugun {m['toxtash_soni']} marta uzilib qoldi, lekin har safar o'zim tikladim."
           if m["toxtash_soni"] else " Bugun hech qanday uzilish bo'lmadi.")
        + (" Tavsiyam: restoranning tarmoq aloqasini bir tekshirtirsangiz yaxshi bo'lardi."
           if m["toxtash_soni"] > 20 else "")
    )
    batafsil = (
        f"Bugungi javoblar soni: {m['soni']}. Bugungi vaqtincha uzilishlar soni: {m['toxtash_soni']}. "
        f"Holat: {m['status_text']}"
        + (f" (oxirgi javobdan {int(m['farq'])} daqiqa o'tgan)." if m["farq"] is not None else ".")
    )
    return {
        "status": m["status"], "status_text": m["status_text"], "hozir": hozir,
        "metrics": [(m["soni"], "bugun javob"), (m["toxtash_soni"], "bugun to'xtash"), (sum(m["spark"]), "7 kunlik javob")],
        "spark": m["spark"], "say": say, "batafsil": batafsil,
    }


# ---------------------------------------------------------------------------
# Sardor — kuzatuv + backup (barchasi LOKAL fayl o'qish, tarmoq/SSH YO'Q —
# haqiqiy SSH faqat soatlik/kunlik Task Scheduler skriptlarining o'zida,
# ular natijani shu lokal fayllarga allaqachon yozib qo'ygan bo'ladi).
# ---------------------------------------------------------------------------
def _sardor_malumot(bugun: str) -> dict:
    azizedu_log = _fayl_oqi(BASE / "jarvis_azizedu_kuzatuv.log")
    grampus_log = _fayl_oqi(BASE / "jarvis_grampus_kuzatuv.log")

    def oxirgi_vaqt(log_matni: str) -> float | None:
        qatorlar = [q for q in log_matni.splitlines() if q.strip().startswith("[")]
        if not qatorlar:
            return None
        try:
            vaqt_str = qatorlar[-1].split("]")[0].lstrip("[")
            return _daqiqa_farqi(vaqt_str)
        except Exception:
            return None

    farq_a = oxirgi_vaqt(azizedu_log)
    farq_g = oxirgi_vaqt(grampus_log)
    faol = [f for f in (farq_a, farq_g) if f is not None and f < 90]
    if len(faol) == 2:
        status, status_text = "ok", "✅ ishlayapti"
    elif faol:
        status, status_text = "warn", "⚠️ qisman ishlayapti"
    else:
        status, status_text = "warn", "⚠️ javob yo'q"

    backup_holat = _json_oqi(BASE / "sardor_backup_holat.json")
    if backup_holat and backup_holat.get("sana", "").startswith(bugun):
        natijalar = backup_holat.get("natijalar", {})
        ok_soni = sum(1 for n in natijalar.values() if n.get("ok"))
        jami = len(natijalar) or 3
        hammasi_ok = backup_holat.get("hammasi_ok")
        backup_matn = f"zaxira nusxa {'✅' if hammasi_ok else '⚠️'} ({ok_soni}/{jami} joyida)"
        backup_qator = f"{ok_soni}/{jami}"
    else:
        hammasi_ok = None
        backup_matn = "zaxira nusxa hali bugun tekshirilmagan"
        backup_qator = "—/3"

    xato_qatorlar = [
        q for q in (azizedu_log.splitlines() + grampus_log.splitlines())
        if bugun in q and ("xato" in q.lower() or "ogohlantirish" in q.lower())
    ]

    tekshiruv_qatorlar = [
        q for q in (azizedu_log.splitlines() + grampus_log.splitlines())
        if "checkpoint_tekshir(" in q
    ]
    spark = _kunlik_hisoblagich(tekshiruv_qatorlar)

    return {
        "status": status, "status_text": status_text, "backup_matn": backup_matn,
        "backup_qator": backup_qator, "backup_ok": hammasi_ok,
        "ogohlantirish_soni": len(xato_qatorlar), "spark": spark,
    }


def sardor_telegram_matn(bugun: str) -> str:
    m = _sardor_malumot(bugun)
    return f"🕵️ *Sardor* (nazoratchi): {m['status_text']} — AzizEdu/Grampus kuzatuvi faol, {m['backup_matn']}."


def sardor_karta(bugun: str) -> dict:
    m = _sardor_malumot(bugun)
    hozir = f"Aziz Edu va Grampus'ni kuzatib turibman. {m['backup_matn']}."
    say = (
        "Salom, Azizbek aka! Men Sardor, moliyaviy ko'rsatkichlarni kuzataman. "
        + ("Bugun zaxira nusxalarning barchasi muvaffaqiyatli olindi." if m["backup_ok"]
           else "Zaxira nusxalarda muammo bor edi." if m["backup_ok"] is False
           else "Zaxira nusxa bugun hali tekshirilmagan.")
        + (f" Bugun {m['ogohlantirish_soni']} marta g'ayrioddiy holatni qayd etdim."
           if m["ogohlantirish_soni"] else " Hech qanday g'ayrioddiy holat sezmadim.")
        + (" Tavsiyam: buni birga bir ko'rib chiqsak yaxshi bo'lardi." if (m["ogohlantirish_soni"] or m["backup_ok"] is False) else "")
    )
    batafsil = (
        f"Zaxira nusxa holati: {m['backup_matn']}. Bugungi g'ayrioddiy holatlar soni: {m['ogohlantirish_soni']}. "
        f"Kuzatuv holati: {m['status_text']}."
    )
    return {
        "status": m["status"], "status_text": m["status_text"], "hozir": hozir,
        "metrics": [(m["backup_qator"], "zaxira bugun"), (m["ogohlantirish_soni"], "ogohlantirish bugun"), (sum(m["spark"]), "7 kunlik tekshiruv")],
        "spark": m["spark"], "say": say, "batafsil": batafsil,
    }


# ---------------------------------------------------------------------------
# Bekzod — watchdog + HUD (2026-09-28: avval "Doktor" deb atalgan)
# ---------------------------------------------------------------------------
def _bekzod_malumot(bugun: str) -> dict:
    diag = _fayl_oqi(BASE / "diagnostika.log")
    qatorlar = [q for q in diag.splitlines() if q.strip()]
    asosiy_tirik = False
    if qatorlar:
        try:
            vaqt_qismi = qatorlar[-1].split("]")[0].strip("[")
            h, mnt, s = vaqt_qismi.split(":")
            s = s.split(".")[0]
            hozir = _hozir()
            log_vaqt = hozir.replace(hour=int(h), minute=int(mnt), second=int(s), microsecond=0)
            asosiy_tirik = abs((hozir - log_vaqt).total_seconds()) < 180
        except Exception:
            pass

    ogohlantirishlar = []
    for nomi, yol in [
        ("AI Expert", BASE / "mijozlar" / "ai_expert_bot" / "watchdog_holat.json"),
        ("JetCafe", BASE / "mijozlar" / "jetcafe_bot" / "watchdog_holat.json"),
    ]:
        holat = _json_oqi(yol)
        if holat and holat.get("muammoda"):
            ogohlantirishlar.append(nomi)

    status = "ok" if (asosiy_tirik and not ogohlantirishlar) else "warn"
    status_text = "✅ ishlayapti" if status == "ok" else "⚠️ diqqat"

    toxtash_qatorlar = []
    for bot_log in ("ai_expert_bot", "jetcafe_bot"):
        matn = _fayl_oqi(BASE / "mijozlar" / bot_log / "bot.log")
        toxtash_qatorlar += [q for q in matn.splitlines() if "To'xtadi:" in q]
    toxtash_bugun = _bugun_soni(toxtash_qatorlar, bugun)
    spark = _kunlik_hisoblagich(toxtash_qatorlar)

    return {
        "status": status, "status_text": status_text, "asosiy_tirik": asosiy_tirik,
        "ogohlantirishlar": ogohlantirishlar, "toxtash_bugun": toxtash_bugun, "spark": spark,
    }


def bekzod_telegram_matn(bugun: str) -> str:
    m = _bekzod_malumot(bugun)
    asosiy_matn = "✅ Jarvis tirik" if m["asosiy_tirik"] else "⚠️ Jarvis heartbeat eskirgan"
    muammo_matn = (
        f", bugun {', '.join(m['ogohlantirishlar'])}da muammo qayd etilgan"
        if m["ogohlantirishlar"] else ", bugun hech qanday xodimda muammo yo'q"
    )
    return f"🩺 *Bekzod* (watchdog/HUD): {asosiy_matn}{muammo_matn}."


def bekzod_karta(bugun: str) -> dict:
    m = _bekzod_malumot(bugun)
    hozir = (
        "Diqqat: bir joyda muammo bor, kuzatyapman."
        if m["ogohlantirishlar"] else "3 ta kuzatuvchi tizim har 5 daqiqada holatni tekshirib turibdi, muammo yo'q."
    )
    muammo_bor = bool(m["ogohlantirishlar"]) or m["toxtash_bugun"] > 20
    say = (
        "Salom, Azizbek aka! Men Bekzod, tizimning sog'ligini kuzataman. "
        + ("Bugun barcha xizmatlar tinch ishladi, muammo bo'lmadi." if not muammo_bor
           else f"Bugun {m['toxtash_bugun']} marta vaqtincha uzilish bo'ldi, lekin har safar o'zim tikladim.")
        + (f" Hozir {len(m['ogohlantirishlar'])} ta ochiq masala bor." if m["ogohlantirishlar"] else "")
        + (" Tavsiyam: buni birga ko'rib chiqsak yaxshi bo'lardi." if muammo_bor else "")
    )
    asosiy_holat_matni = "tirik" if m["asosiy_tirik"] else "heartbeat eskirgan"
    ogohlantirish_matni = ", ".join(m["ogohlantirishlar"]) if m["ogohlantirishlar"] else "yo'q"
    batafsil = (
        f"Asosiy tizim holati: {asosiy_holat_matni}. "
        f"Bugungi avtomatik tiklashlar soni: {m['toxtash_bugun']}. "
        f"Ochiq ogohlantirishlar: {ogohlantirish_matni}."
    )
    return {
        "status": m["status"], "status_text": m["status_text"], "hozir": hozir,
        "metrics": [(m["toxtash_bugun"], "bugun to'xtash"), (len(m["ogohlantirishlar"]), "ochiq muammo"), (sum(m["spark"]), "7 kunlik to'xtash")],
        "spark": m["spark"], "say": say, "batafsil": batafsil,
    }


# ---------------------------------------------------------------------------
# Nozima — buxgalter (haftalik)
# ---------------------------------------------------------------------------
def _nozima_malumot(bugun: str) -> dict:
    natija = _json_oqi(BASE / "nozima_oxirgi_natija.json")
    return {"natija": natija, "bugun": bugun}


def nozima_telegram_matn(bugun: str) -> str:
    m = _nozima_malumot(bugun)["natija"]
    if not m:
        return "🧮 *Nozima* (buxgalter): faol (har dushanba 09:00) — hali birorta hisobot yuborilmagan."
    sana = m.get("sana", "?")
    if m.get("xato"):
        return f"🧮 *Nozima* (buxgalter): ⚠️ oxirgi urinish ({sana}) xato berdi: {m['xato']}"
    bugun_yubordimi = " (BUGUN)" if sana.startswith(bugun) else ""
    return f"🧮 *Nozima* (buxgalter): faol (har dushanba 09:00) — oxirgi hisobot {sana}{bugun_yubordimi}."


_NOZIMA_RAQAM_RE = re.compile(
    # 2026-09-28: so'nggi qo'shimchaga qarab qat'iy emas ("tasi"/"tasida",
    # "belgilagan"/"belgilangan" ikkalasi ham mos kelsin) — matn ustidagi
    # kichik so'z o'zgarishlarida bu regex qayta buzilmasin.
    r"AzizEdu[^:]*:\s*(\d+)\s*faol o'quvchidan\s*(\d+)\s*tasi\w*\s*to'lagan.*?(\d+)\s*tasi\w*.*?\n"
    r"Grampus[^:]*:\s*(\d+)\s*faol sportchidan\s*(\d+)\s*tasi\w*\s*to'lov\s*belgila\w*.*?(\d+)\s*tasi\w*",
    re.DOTALL,
)


def nozima_karta(bugun: str) -> dict:
    natija = _nozima_malumot(bugun)["natija"]
    a_tolamagan = g_belgilanmagan = None
    if natija and natija.get("matn") and not natija.get("xato"):
        m = _NOZIMA_RAQAM_RE.search(natija["matn"])
        if m:
            a_tolamagan, g_belgilanmagan = int(m.group(3)), int(m.group(6))

    if a_tolamagan is None:
        status, status_text = "warn", "⚠️ hali hisobot yo'q"
        hozir = "Haftalik hisobotga tayyor. Hali birorta hisobot yuborilmagan."
        say = "Salom, Azizbek aka! Men Nozima, to'lovlarni kuzataman. Birinchi hisobotimni yaqin kunda taqdim etaman."
        metrics = [("—", "AzizEdu: to'lov yozilmagan"), ("—", "Grampus: belgilanmagan")]
        spark = [0] * 7
        batafsil = "Hali birorta haftalik hisobot yuborilmagan."
    else:
        status, status_text = ("warn", "⚠️ diqqat") if (a_tolamagan or g_belgilanmagan) else ("ok", "✅ hammasi to'langan")
        sana = natija.get("sana", "?")
        hozir = f"Oxirgi hisobot: {sana}. Har hafta yangilanadi."
        if a_tolamagan or g_belgilanmagan:
            say = (
                "Salom, Azizbek aka! Men Nozima, to'lovlarni kuzataman. "
                f"Aziz Edu'da {a_tolamagan} kishi, Grampus'da {g_belgilanmagan} kishida tizimda to'lovi yozilmagan. "
                "Tavsiyam: ularga eslatma yuborishni so'rab qo'ying."
            )
        else:
            say = "Salom, Azizbek aka! Men Nozima, to'lovlarni kuzataman. Ikkala tashkilotda ham hammasida tizimda to'lov bor, muammo yo'q."
        metrics = [(a_tolamagan, "AzizEdu: tizimda yozilmagan"), (g_belgilanmagan, "Grampus: tizimda yozilmagan")]
        # Tarixiy kunlik yozuv yo'q (haftalik) -- hozirgi haqiqiy qiymat tekis chiziq sifatida.
        spark = [a_tolamagan + g_belgilanmagan] * 7
        batafsil = f"Oxirgi tekshiruv sanasi: {sana}. AzizEdu (Orzu Akademy) tizimda to'lovi yozilmagan: {a_tolamagan}. Grampus Junior FC tizimda to'lovi yozilmagan: {g_belgilanmagan}."

    return {
        "status": status, "status_text": status_text, "hozir": hozir,
        "metrics": metrics, "spark": spark, "say": say, "batafsil": batafsil,
    }


# ---------------------------------------------------------------------------
# Jarvis — bosh koordinator
# ---------------------------------------------------------------------------
def _jarvis_malumot(bugun: str) -> dict:
    try:
        import jarvis_bildirishnoma
        barchasi = jarvis_bildirishnoma.bildirishnomalarni_oqi()
    except Exception:
        barchasi = []
    bugungi = [b for b in barchasi if str(b.get("vaqt", "")).startswith(bugun)]

    try:
        import jarvis_fon_ishlar
        fon_agentlar = [x for x in jarvis_fon_ishlar.faol_ishlar() if x.get("agent") != "telegram"]
    except Exception:
        fon_agentlar = []

    qator_sanalari = [str(b.get("vaqt", "")) for b in barchasi]
    spark = _kunlik_hisoblagich(qator_sanalari)

    return {"bugungi_soni": len(bugungi), "fon_agentlar": fon_agentlar, "oxirgi": bugungi[-1] if bugungi else None, "spark": spark}


def jarvis_karta(bugun: str) -> dict:
    m = _jarvis_malumot(bugun)
    band_soni = len(m["fon_agentlar"])
    if band_soni:
        hozir = f"Hozir {band_soni} ta ish bajarilmoqda."
    else:
        hozir = "Yangi topshiriqni kutyapman."
    say = (
        "Assalomu alaykum, Azizbek aka! Men Jarvis, jamoani boshqaraman. "
        f"Bugun {m['bugungi_soni']} ta muhim voqea bo'ldi, hammasi nazoratda. "
        + ("Hozir bir nechta ish bajarilmoqda. " if band_soni else "Hozir hammamiz tinch, yangi topshiriq kutyapmiz. ")
        + "Xodimlarimizning hisobotini quyida eshitasiz."
    )
    batafsil = (
        f"Bugungi bildirishnomalar soni: {m['bugungi_soni']}. Faol vazifalar soni: {band_soni}. "
        f"Oxirgi voqea: {(m['oxirgi'] or {}).get('matn', 'yoq')[:200] if m['oxirgi'] else 'yoq'}"
    )
    return {
        "status": "ok", "status_text": "✅ ishlayapti", "hozir": hozir,
        "metrics": [(m["bugungi_soni"], "bugungi voqea"), (band_soni, "faol vazifalar"), (sum(m["spark"]), "7 kunlik voqea")],
        "spark": m["spark"], "say": say, "batafsil": batafsil,
    }


# ---------------------------------------------------------------------------
# Kamola — marketolog (2026-09-28 ishga tushirildi): faqat qoralama tayyorlaydi,
# hech narsani o'zi post qilmaydi. AI ishlatilmaydi — reja jarvis_hud/kamola_reja.json'da
# qo'lda/oldindan tayyorlangan (haftalik yangilanadi).
# ---------------------------------------------------------------------------
_KAMOLA_REJA_FAYL = BASE / "jarvis_hud" / "kamola_reja.json"


def _kamola_reja() -> dict | None:
    d = _json_oqi(_KAMOLA_REJA_FAYL)
    return d


def kamola_karta(bugun: str) -> dict:
    reja = _kamola_reja()
    if not reja:
        return {
            "status": "warn", "status_text": "⚠️ reja yo'q", "hozir": "Hali haftalik reja tayyorlanmagan.",
            "metrics": [("—", "post qoralamasi"), ("—", "kanal")], "spark": [0] * 7,
            "say": "Men Kamola, lekin hali haftalik rejam tayyor emas.", "batafsil": "Hali reja fayli yo'q.",
        }
    kanallar = reja.get("kanallar", [])
    post_soni = sum(len(k.get("postlar", [])) for k in kanallar)
    hozir = f"{reja.get('sana', '?')} uchun {post_soni} ta post qoralamasi tayyor — {len(kanallar)} ta kanal uchun. Faqat qoralama, o'zim joylamayman."
    say = (
        f"Salom, Azizbek aka! Men Kamola, marketing bilan shug'ullanaman. "
        f"Bu hafta uchun {', '.join(k['nomi'].split(' (')[0] for k in kanallar)} kanallariga jami {post_soni} ta post qoralamasi tayyorladim. "
        "Hech birini o'zim joylamayman, sizning ko'rib chiqishingizni va tasdig'ingizni kutaman."
    )
    batafsil = "\n".join(f"{k['nomi']}: {len(k.get('postlar', []))} ta post" for k in kanallar)
    return {
        "status": "ok", "status_text": "✅ ishlayapti", "hozir": hozir,
        "metrics": [(post_soni, "post qoralamasi"), (len(kanallar), "kanal")], "spark": [post_soni] * 7,
        "say": say, "batafsil": batafsil,
    }


# ---------------------------------------------------------------------------
# Yig'uvchi funksiyalar (HUD va Telegram BIR XIL shundan foydalanadi)
# ---------------------------------------------------------------------------
_KARTA_FUNKSIYALAR = {
    "jarvis": jarvis_karta, "samandar": samandar_karta, "malika": malika_karta,
    "sardor": sardor_karta, "bekzod": bekzod_karta, "nozima": nozima_karta, "kamola": kamola_karta,
}
_TELEGRAM_FUNKSIYALAR = {
    "samandar": samandar_telegram_matn, "malika": malika_telegram_matn,
    "sardor": sardor_telegram_matn, "bekzod": bekzod_telegram_matn, "nozima": nozima_telegram_matn,
}


def xodim_kartasi(xodim_id: str, bugun: str | None = None) -> dict:
    bugun = bugun or _bugun_str()
    meta = XODIMLAR[xodim_id]
    paket = _KARTA_FUNKSIYALAR[xodim_id](bugun)
    return {**meta, **paket}


def _barcha_xodimlar_hisobla(bugun: str) -> list[dict]:
    return [xodim_kartasi(xid, bugun) for xid in XODIM_TARTIBI]


# HUD paneli har 15 soniyada so'raydi, lekin log fayllar (ai_expert/jetcafe
# bot.log) bir necha MB -- har so'rovda to'liq qayta o'qish shart emas. Kichik
# TTL-kesh (20s) bilan qisqa vaqt ichidagi qayta-qayta so'rovlarni tejaymiz;
# Telegram "jamoa" buyrug'i (kamdan-kam, qo'lda) har doim FORCE bilan yangi
# hisoblaydi -- eskirgan ma'lumot bermasin.
_KESH_TTL_S = 20.0
_kesh: dict = {"vaqt": 0.0, "bugun": None, "data": None}


def barcha_xodimlar(bugun: str | None = None, force: bool = False) -> list[dict]:
    import time
    bugun = bugun or _bugun_str()
    now = time.time()
    if not force and _kesh["data"] is not None and _kesh["bugun"] == bugun and (now - _kesh["vaqt"]) < _KESH_TTL_S:
        return _kesh["data"]
    data = _barcha_xodimlar_hisobla(bugun)
    _kesh.update(vaqt=now, bugun=bugun, data=data)
    return data


# ---------------------------------------------------------------------------
# "Bugun nima qilindi" lentasi — real bildirishnoma+lid voqealaridan
# ---------------------------------------------------------------------------
_LENTA_KALIT_SOZLAR = [
    (re.compile(r"nozima|to'lov hisoboti", re.IGNORECASE), "nozima"),
    (re.compile(r"fon agent|restart|MAJBURAN", re.IGNORECASE), "bekzod"),
    (re.compile(r"azizedu|grampus|backup", re.IGNORECASE), "sardor"),
    (re.compile(r"\[\[LEAD|samandar|lid", re.IGNORECASE), "samandar"),
    # "dasturxon" so'zi -- restoranning NOMI (endi xodim emas), pattern
    # o'zgarmaydi (log matnida shu so'z chiqadi), FAQAT natija agent_id
    # yangi xodim ("malika")ga ko'rsatadi.
    (re.compile(r"dasturxon|jetcafe", re.IGNORECASE), "malika"),
]


def _lenta_agentini_top(matn: str) -> str:
    for naqsh, agent_id in _LENTA_KALIT_SOZLAR:
        if naqsh.search(matn):
            return agent_id
    return "jarvis"


def _24_soat_ichidami(vaqt_str: str) -> bool:
    """Kalendar-kun (bugun.startswith) O'RNIGA haqiqiy 24-soatlik oyna --
    2026-09-28 (Azizbek so'rovi): tun yarmida/ertalab feed bo'sh ko'rinib
    qolmasin (kecha kechqurundagi voqealar ham ko'rinsin, sana chizig'i
    bo'yicha emas)."""
    farq = _daqiqa_farqi(vaqt_str)
    if farq is None:
        return False
    return 0 <= farq < 24 * 60


def bugungi_lenta(maks: int = 14) -> list[dict]:
    yozuvlar = []
    bugun = _bugun_str()

    try:
        import jarvis_bildirishnoma
        for b in jarvis_bildirishnoma.bildirishnomalarni_oqi():
            vaqt = str(b.get("vaqt", ""))
            if not _24_soat_ichidami(vaqt):
                continue
            matn = str(b.get("matn", "")).split("\n")[0][:110]
            boshqa_kun = not vaqt.startswith(bugun)
            soat_qismi = vaqt.split(" ")[-1][:5] if " " in vaqt else vaqt[:5]
            soat = (vaqt.split(" ")[0][5:] + " " + soat_qismi) if boshqa_kun else soat_qismi
            yozuvlar.append({"vaqt": soat, "agent": _lenta_agentini_top(b.get("matn", "")), "matn": matn, "_xom_vaqt": vaqt})
    except Exception:
        pass

    try:
        leads_matni = _fayl_oqi(BASE / "mijozlar" / "ai_expert_bot" / "leads.txt")
        for q in leads_matni.splitlines():
            xom_vaqt = q[:19]
            if not _24_soat_ichidami(xom_vaqt):
                continue
            boshqa_kun = not q.startswith(bugun)
            soat_qismi = q[11:16] if len(q) > 16 else q[:5]
            soat = (q[5:10] + " " + soat_qismi) if boshqa_kun else soat_qismi
            yozuvlar.append({"vaqt": soat, "agent": "samandar", "matn": "yangi lid topildi (ism+telefon)", "_xom_vaqt": xom_vaqt})
    except Exception:
        pass

    yozuvlar.sort(key=lambda y: y.get("_xom_vaqt", ""), reverse=True)
    for y in yozuvlar:
        y.pop("_xom_vaqt", None)
    return yozuvlar[:maks]


def yakuniy_xulosa(xodimlar: list[dict] | None = None) -> str:
    """Ertalabki yig'ilish oxirida Jarvis aytadigan umumiy xulosa — qisqa,
    biznes tilida, boshqa xodimlarning haqiqiy ko'rsatkichlaridan eng
    muhimini eslatib o'tadi va (bo'lsa) BITTA aniq tavsiya bilan tugaydi."""
    xodimlar = xodimlar or barcha_xodimlar()
    by_id = {x["id"]: x for x in xodimlar}
    gaplar = ["Xulosa qilsam, Azizbek aka: jamoa bugun ham ishini davom ettirmoqda."]

    muammolar = []
    nozima = by_id.get("nozima")
    if nozima and nozima.get("metrics"):
        v1, v2 = nozima["metrics"][0][0], nozima["metrics"][1][0]
        if isinstance(v1, int) and isinstance(v2, int) and (v1 or v2):
            muammolar.append(f"to'lovlarda {v1 + v2} kishi hali belgilanmagan")

    bekzod = by_id.get("bekzod")
    if bekzod and bekzod.get("metrics") and bekzod["metrics"][1][0]:
        muammolar.append("tizimda bitta ochiq masala bor")

    if muammolar:
        gaplar.append("Diqqat qilishingiz kerak bo'lgan narsa: " + ", ".join(muammolar) + ".")
        gaplar.append("Tavsiyam: shularni birinchi navbatda ko'rib chiqing.")
    else:
        gaplar.append("Hozircha diqqat talab qiladigan jiddiy narsa yo'q.")

    gaplar.append("Ishni davom ettiramiz.")
    return " ".join(gaplar)


# ---------------------------------------------------------------------------
# Ovoz uchun talaffuz tayyorlash (2026-09-27, Azizbek so'radi) — EKRANDAGI matn
# O'ZGARMAYDI, faqat edge-tts'ga yuborishdan OLDIN shu funksiya orqali
# o'tkaziladi. Ikkala ovoz-generatsiya nuqtasi (bridge `/jamoa/speak` VA
# `jarvis_ertalabki_yigilish.py`) BIR XIL shu funksiyani chaqiradi.
# ---------------------------------------------------------------------------
TALAFFUZ_FAYL = BASE / "jarvis_hud" / "talaffuz.json"
_talaffuz_kesh: dict | None = None

_BIRLIK_SOZLAR = ["nol", "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti", "sakkiz", "to'qqiz"]
_ONLIK_SOZLAR = {10: "o'n", 20: "yigirma", 30: "o'ttiz", 40: "qirq", 50: "ellik",
                 60: "oltmish", 70: "yetmish", 80: "sakson", 90: "to'qson"}


def _son_uzbekcha(n: int) -> str:
    """Butun sonni o'zbekcha so'z bilan yozadi (masalan 171 -> 'bir yuz
    yetmish bir'), Azizbek bergan namunaga mos — yuzlik doim 'bir yuz' kabi
    aniq raqam bilan aytiladi (shunchaki 'yuz' emas)."""
    if n == 0:
        return "nol"
    if n < 0:
        return "minus " + _son_uzbekcha(-n)
    qismlar = []
    ming, qoldiq = divmod(n, 1000)
    if ming:
        qismlar.append("bir ming" if ming == 1 else _son_uzbekcha(ming) + " ming")
    yuz, qoldiq2 = divmod(qoldiq, 100)
    if yuz:
        qismlar.append(_BIRLIK_SOZLAR[yuz] + " yuz")
    if qoldiq2:
        if qoldiq2 < 10:
            qismlar.append(_BIRLIK_SOZLAR[qoldiq2])
        else:
            onlik = (qoldiq2 // 10) * 10
            qismlar.append(_ONLIK_SOZLAR[onlik])
            birlik = qoldiq2 % 10
            if birlik:
                qismlar.append(_BIRLIK_SOZLAR[birlik])
    return " ".join(qismlar)


def _talaffuz_lugati() -> dict:
    global _talaffuz_kesh
    if _talaffuz_kesh is None:
        try:
            _talaffuz_kesh = json.loads(TALAFFUZ_FAYL.read_text(encoding="utf-8"))
        except Exception:
            _talaffuz_kesh = {}
    return _talaffuz_kesh


_RAQAM_RE = re.compile(r"\d+")


def ovoz_uchun_tayyorla(matn: str) -> str:
    """EKRANGA emas, FAQAT edge-tts'ga yuboriladigan matnni tayyorlaydi:
    1) talaffuz.json lug'atidagi so'zlarni almashtiradi (masalan
       "AzizEdu" -> "Aziz Edu", "backup" -> "zaxira nusxa");
    2) qolgan barcha raqamlarni so'z bilan yozadi (171 -> "bir yuz yetmish
       bir") — edge-tts ba'zan raqamlarni g'alati/notekis o'qiydi, so'z bilan
       yozilgan raqam har doim to'g'ri talaffuz qilinadi."""
    if not matn:
        return matn
    natija = matn
    for asl, yangi in _talaffuz_lugati().items():
        natija = re.sub(r"\b" + re.escape(asl) + r"\b", yangi, natija, flags=re.IGNORECASE)
    natija = _RAQAM_RE.sub(lambda m: _son_uzbekcha(int(m.group(0))), natija)
    return natija


if __name__ == "__main__":
    import pprint
    pprint.pprint(barcha_xodimlar())
    print("\n--- LENTA ---")
    pprint.pprint(bugungi_lenta())
    print("\n--- XULOSA ---")
    print(yakuniy_xulosa())
