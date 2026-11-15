"""
JARVIS BIZNES KUZATUV — AzizEdu/Orzu Akademy (2026-09-21, 1-bosqich).

Maqsad: Azizbekning "3 ta biznesni har kuni proaktiv kuzatib, g'alati narsa
bo'lsa darhol ogohlantir" so'roviga javoban qurilgan birinchi (AzizEdu)
modul. Keyingi bosqichlarda Grampus va JetCafe (log-monitoring) ham xuddi
shu naqsh bilan qo'shiladi — reja: xotira/loyihalar/proaktiv_kuzatuv.md.

Bu fayl jarvis_core.py/jarvis_telegram.py'ga HECH QANDAY aloqasi yo'q —
mustaqil skript, `jarvis_proaktiv.py`dagi bilan bir xil naqsh:
Task Scheduler orqali (S4U, har soat) ishga tushiriladi, ichida vaqtga
qarab (08:00 kunlik hisobot / 11-14-17-20:00 anomaliya-checkpoint)
o'zi qaror qiladi.

MA'LUMOT MANBASI: Hetzner "nishon-server" (49.12.111.53)dagi Postgres
`oquv_markaz` bazasi, SSH orqali (5432-port tashqariga ochiq emas,
ufw faqat 22/80/443). Postgres darajasida FAQAT O'QISH huquqli
`jarvis_readonly` roli ishlatiladi (2026-09-21 yaratildi, sinovda
tasdiqlandi: SELECT ishlaydi, INSERT/DELETE "read-only transaction"
xatosi bilan rad etiladi — default_transaction_read_only=on VA yozish
GRANT'i yo'q, ikkala himoya qatlami mustaqil).

Tashkilot: faqat "Orzu Akademy" (organization_id config.AZIZEDU_ORG_ID)
kuzatiladi — bu production'dagi YAGONA real (134 o'quvchi) tashkilot,
qolgan ikkitasi ("AzizEdu Platform", "Azizbek Hazratov") test/bo'sh.

ANOMALIYA MEZONI (2026-09-21 rejasiga mos, dastlab moslashuvchan):
birinchi 14 kun (yoki 14 checkpoint) faqat ma'lumot YIG'ILADI, hech qanday
"anomaliya" xabari yuborilmaydi (tarix hali yo'q — noto'g'ri signal berish
xavfi bor). Shundan keyin: joriy qiymat oxirgi 14 kunlik/checkpoint'lik
o'rtachadan 50%+ past bo'lsa (yoki davomat foizi 20 foiz-punktdan ko'p
pasaysa) — DARHOL Telegram xabar.

IKKI XIL SIGNAL (Azizbek bilan kelishilgan farq):
1) **Kunlik hisobot** (har kuni 08:00, Toshkent vaqti) — KECHAGI to'liq
   kun bo'yicha raqamlar, tarix bor-yo'qligidan qat'i nazar HAR DOIM
   yuboriladi (bu oddiy statistika, "anomaliya" emas — birinchi kundan
   foydali).
2) **Anomaliya-checkpoint** (11:00/14:00/17:00/20:00, Toshkent vaqti) —
   BUGUNGI kunning hozirgacha to'plangan qiymati, faqat 14+ ta tarixiy
   checkpoint to'planganidan keyin xabar yuboradi (aks holda faqat
   tarixga yozadi, jim turadi).
"""

import json
import shlex
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import config  # AZIZEDU_DB_*, AZIZEDU_ORG_ID, HETZNER_NISHON_SERVER_*, TELEGRAM_TOKEN, OWNER_ID
from jarvis_proaktiv import telegram_xabar_yubor  # mavjud, sinaldi (2026-09-12dan beri ishlatiladi)

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "jarvis_azizedu_kuzatuv.log"
TARIX_FILE = BASE_DIR / "azizedu_kuzatuv_tarix.json"

TASHKENT_OFFSET = timedelta(hours=5)  # O'zbekiston DST qo'llamaydi — doim +5
KUNLIK_HISOBOT_SOAT = 8
CHECKPOINT_SOATLAR = [11, 14, 17, 20]
OGANISH_MINIMAL_KUN = 14  # shu sondan kam tarix bo'lsa anomaliya xabari yuborilmaydi

ANOMALIYA_NISBAT_CHEGARA = 0.5  # qiymat o'rtachadan 50%+ past bo'lsa
DAVOMAT_PUNKT_CHEGARA = 20.0    # yoki davomat foizi 20 punktdan ko'p pasaysa


def _tashkent_hozir() -> datetime:
    return datetime.utcnow() + TASHKENT_OFFSET


def _logga_yoz(matn: str):
    vaqt = _tashkent_hozir().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{vaqt}] {matn}\n")
    except Exception:
        pass


def _ssh_psql(sql: str) -> str:
    """Hetzner nishon-server'ga SSH orqali kirib, jarvis_readonly roli bilan
    berilgan SQL'ni bajaradi. -t -A -F'|' — sarlavhasiz, tekislashsiz,
    '|' bilan ajratilgan qator(lar) qaytaradi (parse qilish oson).
    Faqat SELECT so'rovlar uchun mo'ljallangan — yozish SQL'lari baribir
    Postgres darajasida rad etiladi (yuqoridagi izohga qarang)."""
    remote_cmd = (
        f"PGPASSWORD={shlex.quote(config.AZIZEDU_DB_PASSWORD)} "
        f"psql -h {config.AZIZEDU_DB_HOST} -U {config.AZIZEDU_DB_USER} "
        f"-d {config.AZIZEDU_DB_NAME} -t -A -F'|' -c {shlex.quote(sql)}"
    )
    cmd = [
        "ssh",
        "-i", config.HETZNER_NISHON_SERVER_SSH_KEY,
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=15",
        f"root@{config.HETZNER_NISHON_SERVER_IP}",
        remote_cmd,
    ]
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    natija = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
    if natija.returncode != 0:
        raise RuntimeError(f"ssh/psql xato (kod {natija.returncode}): {natija.stderr.strip()}")
    return natija.stdout.strip()


def _statistika_ol(sana_str: str) -> dict:
    """Berilgan sana (YYYY-MM-DD, Toshkent kalendar kuni) uchun AzizEdu
    (Orzu Akademy) statistikasini bitta SQL so'rovda oladi."""
    org = config.AZIZEDU_ORG_ID
    sql = f"""
        SELECT
            (SELECT COUNT(*) FROM oquvchilar
                WHERE organization_id='{org}' AND created_at::date='{sana_str}') AS yangi_oquvchi,
            (SELECT COUNT(*) FILTER (WHERE holat IN ('keldi','kech_keldi')) FROM davomat
                WHERE organization_id='{org}' AND sana='{sana_str}') AS keldi,
            (SELECT COUNT(*) FROM davomat
                WHERE organization_id='{org}' AND sana='{sana_str}') AS davomat_jami,
            (SELECT COALESCE(SUM(summa),0) FROM tolovlar
                WHERE organization_id='{org}' AND tolangan_sana='{sana_str}' AND holat='tolangan') AS kassa
    """
    qator = _ssh_psql(sql)
    yangi_oquvchi, keldi, davomat_jami, kassa = qator.split("|")
    yangi_oquvchi = int(yangi_oquvchi)
    keldi = int(keldi)
    davomat_jami = int(davomat_jami)
    kassa = float(kassa)
    davomat_foiz = round(keldi / davomat_jami * 100, 1) if davomat_jami > 0 else None
    return {
        "yangi_oquvchi": yangi_oquvchi,
        "davomat_foiz": davomat_foiz,
        "davomat_jami_yozuv": davomat_jami,
        "kassa": kassa,
    }


# ---------------------------------------------------------------- tarix ----

def _tarix_yukla() -> dict:
    if not TARIX_FILE.exists():
        return {"kunlik": {}, "checkpoint": {}}
    try:
        return json.loads(TARIX_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        _logga_yoz(f"Tarix fayli o'qishda xato ({e!r}) — bo'sh tarix bilan davom etiladi.")
        return {"kunlik": {}, "checkpoint": {}}


def _tarix_saqla(tarix: dict):
    TARIX_FILE.write_text(json.dumps(tarix, ensure_ascii=False, indent=2), encoding="utf-8")


def _ortacha(qiymatlar: list) -> float | None:
    raqamlar = [q for q in qiymatlar if q is not None]
    if not raqamlar:
        return None
    return sum(raqamlar) / len(raqamlar)


def _oxirgi_n(tarix_bolimi: dict, kalitdan_oldin: str, n: int) -> list:
    """tarix_bolimi = {"2026-09-20": {...}, ...} — kalitdan_oldin sanasidan
    OLDINGI kunlarni (xronologik) tanlab, oxirgi n tasini qaytaradi."""
    sanalar = sorted(k for k in tarix_bolimi if k < kalitdan_oldin)
    return [tarix_bolimi[s] for s in sanalar[-n:]]


# --------------------------------------------------------- 1) kunlik hisobot

def kunlik_hisobot():
    """Har kuni 08:00 (Toshkent) — KECHAGI to'liq kun statistikasi, tarix
    bor-yo'qligidan qat'i nazar HAR DOIM yuboriladi."""
    bugun = _tashkent_hozir().date()
    kecha = bugun - timedelta(days=1)
    kecha_str = kecha.strftime("%Y-%m-%d")

    try:
        stat = _statistika_ol(kecha_str)
    except Exception as e:
        _logga_yoz(f"kunlik_hisobot: statistika olishda xato: {e!r}")
        telegram_xabar_yubor(
            "⚠️ Jarvis Biznes Kuzatuv (AzizEdu): kunlik hisobot uchun "
            f"ma'lumot olib bo'lmadi ({e}). Iltimos tekshiring."
        )
        return

    tarix = _tarix_yukla()
    oldingilar = _oxirgi_n(tarix["kunlik"], kecha_str, OGANISH_MINIMAL_KUN)
    yetarli_tarix = len(oldingilar) >= OGANISH_MINIMAL_KUN

    ogohlantirishlar = []
    if yetarli_tarix:
        ort_yangi = _ortacha([o["yangi_oquvchi"] for o in oldingilar])
        ort_kassa = _ortacha([o["kassa"] for o in oldingilar])
        ort_davomat = _ortacha([o["davomat_foiz"] for o in oldingilar if o["davomat_foiz"] is not None])

        if ort_yangi and stat["yangi_oquvchi"] < ort_yangi * (1 - ANOMALIYA_NISBAT_CHEGARA):
            ogohlantirishlar.append(
                f"🔴 Yangi o'quvchi kecha {stat['yangi_oquvchi']} ta — "
                f"oxirgi {OGANISH_MINIMAL_KUN} kunlik o'rtacha ({ort_yangi:.1f}) dan sezilarli past."
            )
        if ort_kassa and stat["kassa"] < ort_kassa * (1 - ANOMALIYA_NISBAT_CHEGARA):
            ogohlantirishlar.append(
                f"🔴 Kassa tushumi kecha {stat['kassa']:,.0f} so'm — "
                f"oxirgi {OGANISH_MINIMAL_KUN} kunlik o'rtacha ({ort_kassa:,.0f} so'm) dan sezilarli past."
            )
        if ort_davomat is not None and stat["davomat_foiz"] is not None \
                and stat["davomat_foiz"] < ort_davomat - DAVOMAT_PUNKT_CHEGARA:
            ogohlantirishlar.append(
                f"🔴 Davomat kecha {stat['davomat_foiz']}% — "
                f"o'rtacha ({ort_davomat:.1f}%) dan {DAVOMAT_PUNKT_CHEGARA}+ punkt past."
            )

    davomat_matn = f"{stat['davomat_foiz']}%" if stat["davomat_foiz"] is not None else "ma'lumot yo'q"
    matn = (
        f"📊 AzizEdu (Orzu Akademy) — {kecha_str} hisoboti:\n"
        f"• Yangi o'quvchi: {stat['yangi_oquvchi']} ta\n"
        f"• Davomat: {davomat_matn} ({stat['davomat_jami_yozuv']} yozuv)\n"
        f"• Kassa tushumi: {stat['kassa']:,.0f} so'm"
    )
    if ogohlantirishlar:
        matn += "\n\n" + "\n".join(ogohlantirishlar)
    elif not yetarli_tarix:
        matn += f"\n\n(hali o'rganish davri — {len(oldingilar)}/{OGANISH_MINIMAL_KUN} kun tarix to'plandi)"

    telegram_xabar_yubor(matn)
    _logga_yoz(f"Kunlik hisobot yuborildi ({kecha_str}): {stat}, ogohlantirish={len(ogohlantirishlar)}")

    tarix["kunlik"][kecha_str] = stat
    _tarix_saqla(tarix)


# ------------------------------------------------------ 2) anomaliya-checkpoint

def checkpoint_tekshir(soat: int):
    """11:00/14:00/17:00/20:00 (Toshkent) — BUGUNGI kunning hozirgacha
    to'plangan qiymati. Faqat shu checkpoint uchun 14+ ta tarix bo'lsa
    anomaliya xabari yuboradi, aks holda faqat tarixga yozadi."""
    bugun_str = _tashkent_hozir().date().strftime("%Y-%m-%d")
    soat_kalit = str(soat)

    try:
        stat = _statistika_ol(bugun_str)
    except Exception as e:
        _logga_yoz(f"checkpoint_tekshir({soat}): statistika olishda xato: {e!r}")
        return  # kunlik hisobotda xato allaqachon xabar qilinadi, har checkpoint'da spam qilmaslik uchun jim

    tarix = _tarix_yukla()
    tarix["checkpoint"].setdefault(soat_kalit, {})
    oldingilar = _oxirgi_n(tarix["checkpoint"][soat_kalit], bugun_str, OGANISH_MINIMAL_KUN)
    yetarli_tarix = len(oldingilar) >= OGANISH_MINIMAL_KUN

    _logga_yoz(
        f"checkpoint_tekshir({soat}:00, {bugun_str}): {stat} "
        f"(tarix: {len(oldingilar)}/{OGANISH_MINIMAL_KUN})"
    )

    if yetarli_tarix:
        ort_yangi = _ortacha([o["yangi_oquvchi"] for o in oldingilar])
        ort_kassa = _ortacha([o["kassa"] for o in oldingilar])
        ogohlantirishlar = []
        if ort_yangi and stat["yangi_oquvchi"] < ort_yangi * (1 - ANOMALIYA_NISBAT_CHEGARA):
            ogohlantirishlar.append(
                f"🔴 Soat {soat}:00'gacha yangi o'quvchi {stat['yangi_oquvchi']} ta — "
                f"shu vaqtgacha odatiy o'rtacha ({ort_yangi:.1f}) dan sezilarli past."
            )
        if ort_kassa and stat["kassa"] < ort_kassa * (1 - ANOMALIYA_NISBAT_CHEGARA):
            ogohlantirishlar.append(
                f"🔴 Soat {soat}:00'gacha kassa tushumi {stat['kassa']:,.0f} so'm — "
                f"shu vaqtgacha odatiy o'rtacha ({ort_kassa:,.0f} so'm) dan sezilarli past."
            )
        if ogohlantirishlar:
            matn = "⚠️ AzizEdu (Orzu Akademy) — kun davomida anomaliya:\n\n" + "\n".join(ogohlantirishlar)
            telegram_xabar_yubor(matn)
            _logga_yoz(f"Anomaliya xabari yuborildi (checkpoint {soat}:00).")

    tarix["checkpoint"][soat_kalit][bugun_str] = stat
    _tarix_saqla(tarix)


# --------------------------------------------------------------- dispatch ----

def main():
    hozir = _tashkent_hozir()
    soat = hozir.hour
    _logga_yoz(f"Ishga tushdi (Toshkent vaqti {hozir.strftime('%Y-%m-%d %H:%M')}).")

    if soat == KUNLIK_HISOBOT_SOAT:
        kunlik_hisobot()
    elif soat in CHECKPOINT_SOATLAR:
        checkpoint_tekshir(soat)
    else:
        _logga_yoz(f"Soat {soat} — bu soatda vazifa yo'q, chiqildi.")


if __name__ == "__main__":
    main()
