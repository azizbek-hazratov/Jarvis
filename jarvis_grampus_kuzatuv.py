"""
JARVIS BIZNES KUZATUV — Grampus Junior FC (2026-09-21, 2-bosqich).

`jarvis_azizedu_kuzatuv.py` bilan BIR XIL naqsh (mustaqil skript, SSH orqali
faqat-o'qish Postgres rol, kunlik hisobot + anomaliya-checkpoint, 14 kunlik
silent-baseline). Farqlar quyida aniq izohlangan — Grampus ma'lumot
tuzilishi AzizEdu'dan farq qiladi.

MUHIM MA'LUMOT CHEKLOVLARI (Azizbekka ma'lum qilingan, reja bosqichida):
1. `sportchilar` jadvalida `created_at` USTUNI YO'Q — "bugun necha yangi
   sportchi qo'shildi" to'g'ridan-to'g'ri SQL bilan so'ralmaydi. Shu sabab
   bu yerda JORIY AKTIV sportchi sonini (`ochirilgan_sana IS NULL`) har
   safar o'lchab, OLDINGI o'lchovdan farqini (netto o'zgarish) hisoblaymiz
   — bu "sof qo'shilgan" emas, "aktiv soni qancha o'zgardi" (qo'shilish
   MINUS chiqarilish/o'chirilish).
2. `tolov_holatlari.summa` maydoni bor, LEKIN CHECK (0-100000) bilan
   cheklangan — bu haqiqiy oylik to'lov summasi (300-400 ming so'm) EMAS,
   balki chegirma/qisman qiymat ko'rinadi. Shuning uchun Azizbek talabiga
   ko'ra REAL summa emas, faqat **"joriy oy necha % sportchiga to'lov hali
   'tolandi' deb belgilanmagan"** proksi-signal ishlatiladi.
3. `baholash_yozuvlari.sana` (mashg'ulotdan keyingi baholash yozuvi sanasi)
   HAQIQIY tarixiy ustun — shu orqali "kunlik faollik" (davomatga eng yaqin
   proksi: shu kuni necha NOYOB sportchi baholangan) hisoblanadi, AzizEdu'
   dagi `davomat` bilan bir xil ishonchlilikda.

ANOMALIYA MEZONI:
- **Faollik** (baholangan sportchi soni): rolling-14 o'rtachadan 50%+ past
  → anomaliya (AzizEdu'dagi davomat bilan bir xil mantiq).
- **To'lov-belgilanmagan foizi**: rolling-14 o'rtachadan 20+ foiz-punkt
  YUQORI (ko'proq belgilanmagan) → anomaliya.
- **Aktiv sportchi netto o'zgarishi**: kunlik/checkpoint'lik |delta| rolling-
  14 o'rtacha |delta|'dan 2.5x katta (minimal chegara 3 kishi) → anomaliya
  (kutilmagan ommaviy qo'shilish YOKI chiqib ketish — ikkala yo'nalish ham).

Ikki signal (AzizEdu bilan bir xil farq): kunlik hisobot (soat 08, har doim
yuboriladi) + anomaliya-checkpoint (11/14/17/20, faqat 14+ tarixdan keyin
ogohlantiradi). Alohida Task Scheduler vazifasi sifatida ro'yxatga olinadi
(o'zining ro'yxatga olingan daqiqasida takrorlanadi — AzizEdu vazifasi bilan
bir xil soatda, lekin boshqa daqiqada ishga tushadi, shu sabab ikkala SSH
so'rovi navbatga tiqilib qolmaydi, alohida tekshirish shart emas).
"""

import json
import shlex
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import config
from jarvis_proaktiv import telegram_xabar_yubor

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "jarvis_grampus_kuzatuv.log"
TARIX_FILE = BASE_DIR / "grampus_kuzatuv_tarix.json"

TASHKENT_OFFSET = timedelta(hours=5)
KUNLIK_HISOBOT_SOAT = 8
CHECKPOINT_SOATLAR = [11, 14, 17, 20]
OGANISH_MINIMAL_KUN = 14

ANOMALIYA_NISBAT_CHEGARA = 0.5   # faollik shu nisbatdan past bo'lsa anomaliya
TOLOV_PUNKT_CHEGARA = 20.0       # belgilanmagan foizi shuncha punkt oshsa anomaliya
SPORTCHI_DELTA_KOEFF = 2.5       # |delta| o'rtacha |delta|dan shuncha marta katta bo'lsa
SPORTCHI_DELTA_MINIMAL = 3       # va eng kamida shuncha kishilik o'zgarish bo'lsa


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
    remote_cmd = (
        f"PGPASSWORD={shlex.quote(config.GRAMPUS_DB_PASSWORD)} "
        f"psql -h {config.GRAMPUS_DB_HOST} -U {config.GRAMPUS_DB_USER} "
        f"-d {config.GRAMPUS_DB_NAME} -t -A -F'|' -c {shlex.quote(sql)}"
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


def _statistika_ol(faollik_sana_str: str) -> dict:
    """`faollik_sana_str` — baholash faolligini shu ANIQ sana bo'yicha
    o'lchaydi (haqiqiy tarixiy ustun bor). `aktiv_sportchi`/`tolov` esa
    har doim JORIY (so'rov vaqtidagi) holatni ko'rsatadi — DB'da o'tmish
    holatini saqlaydigan ustun yo'q (yuqoridagi izohga qarang)."""
    org = config.GRAMPUS_ORG_ID
    joriy_oy = _tashkent_hozir().strftime("%Y-%m")
    sql = f"""
        SELECT
            (SELECT COUNT(*) FROM sportchilar
                WHERE organization_id='{org}' AND ochirilgan_sana IS NULL) AS aktiv_sportchi,
            (SELECT COUNT(DISTINCT sportchi_id) FROM baholash_yozuvlari
                WHERE organization_id='{org}' AND sana='{faollik_sana_str}') AS faollik,
            (SELECT COUNT(*) FROM tolov_holatlari
                WHERE organization_id='{org}' AND oy='{joriy_oy}' AND holati='tolandi') AS tolandi_soni
    """
    qator = _ssh_psql(sql)
    aktiv_sportchi, faollik, tolandi_soni = (int(x) for x in qator.split("|"))
    tolov_belgilanmagan_foiz = (
        round((aktiv_sportchi - tolandi_soni) / aktiv_sportchi * 100, 1) if aktiv_sportchi > 0 else None
    )
    return {
        "aktiv_sportchi": aktiv_sportchi,
        "faollik": faollik,
        "tolov_belgilanmagan_foiz": tolov_belgilanmagan_foiz,
        "joriy_oy": joriy_oy,
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
    sanalar = sorted(k for k in tarix_bolimi if k < kalitdan_oldin)
    return [tarix_bolimi[s] for s in sanalar[-n:]]


def _oxirgi_qiymat(tarix_bolimi: dict, kalitdan_oldin: str):
    """Shu bo'limdagi ENG SO'NGGI (kalitdan_oldin sanasidan oldingi) yozuvni
    qaytaradi — sportchi-delta hisoblash uchun ("oldingi o'lchov")."""
    sanalar = sorted(k for k in tarix_bolimi if k < kalitdan_oldin)
    return tarix_bolimi[sanalar[-1]] if sanalar else None


def _anomaliyalarni_topish(stat: dict, oldingilar: list, delta_tarix: list, kalit_matn: str) -> list:
    """Umumiy anomaliya-tekshiruv mantiqi — kunlik va checkpoint uchun bir xil."""
    ogohlantirishlar = []
    if len(oldingilar) >= OGANISH_MINIMAL_KUN:
        ort_faollik = _ortacha([o["faollik"] for o in oldingilar])
        ort_tolov = _ortacha([o["tolov_belgilanmagan_foiz"] for o in oldingilar if o["tolov_belgilanmagan_foiz"] is not None])

        if ort_faollik and stat["faollik"] < ort_faollik * (1 - ANOMALIYA_NISBAT_CHEGARA):
            ogohlantirishlar.append(
                f"🔴 {kalit_matn} baholangan sportchi {stat['faollik']} ta — "
                f"oxirgi {OGANISH_MINIMAL_KUN} o'rtacha ({ort_faollik:.1f}) dan sezilarli past "
                "(mashg'ulot/baholash faolligi tushgan bo'lishi mumkin)."
            )
        if ort_tolov is not None and stat["tolov_belgilanmagan_foiz"] is not None \
                and stat["tolov_belgilanmagan_foiz"] > ort_tolov + TOLOV_PUNKT_CHEGARA:
            ogohlantirishlar.append(
                f"🔴 {kalit_matn} to'lov belgilanmagan {stat['tolov_belgilanmagan_foiz']}% — "
                f"o'rtacha ({ort_tolov:.1f}%) dan {TOLOV_PUNKT_CHEGARA}+ punkt yuqori."
            )

    if len(delta_tarix) >= OGANISH_MINIMAL_KUN:
        ort_abs_delta = _ortacha([abs(d) for d in delta_tarix])
        joriy_delta = stat.get("_delta")
        if joriy_delta is not None:
            chegara = max(SPORTCHI_DELTA_MINIMAL, (ort_abs_delta or 0) * SPORTCHI_DELTA_KOEFF)
            if abs(joriy_delta) >= chegara:
                belgi = "+" if joriy_delta > 0 else ""
                ogohlantirishlar.append(
                    f"🔴 {kalit_matn} aktiv sportchi soni {belgi}{joriy_delta} ta o'zgardi "
                    f"(hozir {stat['aktiv_sportchi']} ta) — kutilganidan (odatiy o'zgarish "
                    f"~{ort_abs_delta:.1f} ta) sezilarli katta."
                )
    return ogohlantirishlar


# --------------------------------------------------------- 1) kunlik hisobot

def kunlik_hisobot():
    """08:05 (Toshkent). Faollik — KECHAGI sana bo'yicha (haqiqiy tarixiy
    ustun). Aktiv sportchi/to'lov — JORIY holat (DB'da o'tmish saqlanmaydi),
    delta oldingi o'lchovga nisbatan hisoblanadi."""
    bugun = _tashkent_hozir().date()
    kecha_str = (bugun - timedelta(days=1)).strftime("%Y-%m-%d")
    bugun_str = bugun.strftime("%Y-%m-%d")

    try:
        stat = _statistika_ol(kecha_str)
    except Exception as e:
        _logga_yoz(f"kunlik_hisobot: statistika olishda xato: {e!r}")
        telegram_xabar_yubor(
            "⚠️ Jarvis Biznes Kuzatuv (Grampus): kunlik hisobot uchun "
            f"ma'lumot olib bo'lmadi ({e}). Iltimos tekshiring."
        )
        return

    tarix = _tarix_yukla()
    oldingi_yozuv = _oxirgi_qiymat(tarix["kunlik"], bugun_str)  # kechagi kirishdan OLDINGI (ya'ni avvalgi kun)
    stat["_delta"] = (stat["aktiv_sportchi"] - oldingi_yozuv["aktiv_sportchi"]) if oldingi_yozuv else None

    oldingilar = _oxirgi_n(tarix["kunlik"], kecha_str, OGANISH_MINIMAL_KUN)
    delta_tarix = [o["_delta"] for o in oldingilar if o.get("_delta") is not None]
    yetarli_tarix = len(oldingilar) >= OGANISH_MINIMAL_KUN

    ogohlantirishlar = _anomaliyalarni_topish(stat, oldingilar, delta_tarix, "Kecha")

    delta_matn = (
        f" ({'+' if stat['_delta'] >= 0 else ''}{stat['_delta']} kechagidan)"
        if stat["_delta"] is not None else ""
    )
    tolov_matn = (
        f"{stat['tolov_belgilanmagan_foiz']}%" if stat["tolov_belgilanmagan_foiz"] is not None else "ma'lumot yo'q"
    )
    matn = (
        f"⚽ Grampus Junior FC — {kecha_str} hisoboti:\n"
        f"• Aktiv sportchi: {stat['aktiv_sportchi']} ta{delta_matn}\n"
        f"• Kecha baholangan sportchi (faollik): {stat['faollik']} ta\n"
        f"• {stat['joriy_oy']} — to'lov belgilanmagan: {tolov_matn}"
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
    bugun_str = _tashkent_hozir().date().strftime("%Y-%m-%d")
    soat_kalit = str(soat)

    try:
        stat = _statistika_ol(bugun_str)  # bugungi faollik ham bugungi sana bo'yicha (kun davomida o'sib boradi)
    except Exception as e:
        _logga_yoz(f"checkpoint_tekshir({soat}): statistika olishda xato: {e!r}")
        return

    tarix = _tarix_yukla()
    tarix["checkpoint"].setdefault(soat_kalit, {})
    oldingi_yozuv = _oxirgi_qiymat(tarix["checkpoint"][soat_kalit], bugun_str)
    stat["_delta"] = (stat["aktiv_sportchi"] - oldingi_yozuv["aktiv_sportchi"]) if oldingi_yozuv else None

    oldingilar = _oxirgi_n(tarix["checkpoint"][soat_kalit], bugun_str, OGANISH_MINIMAL_KUN)
    delta_tarix = [o["_delta"] for o in oldingilar if o.get("_delta") is not None]

    _logga_yoz(
        f"checkpoint_tekshir({soat}:05, {bugun_str}): {stat} "
        f"(tarix: {len(oldingilar)}/{OGANISH_MINIMAL_KUN})"
    )

    ogohlantirishlar = _anomaliyalarni_topish(stat, oldingilar, delta_tarix, f"Soat {soat}:00'gacha")
    if ogohlantirishlar:
        matn = "⚠️ Grampus Junior FC — kun davomida anomaliya:\n\n" + "\n".join(ogohlantirishlar)
        telegram_xabar_yubor(matn)
        _logga_yoz(f"Anomaliya xabari yuborildi (checkpoint {soat}:00).")

    tarix["checkpoint"][soat_kalit][bugun_str] = stat
    _tarix_saqla(tarix)


# --------------------------------------------------------------- dispatch ----

def main():
    hozir = _tashkent_hozir()
    soat, daqiqa = hozir.hour, hozir.minute
    _logga_yoz(f"Ishga tushdi (Toshkent vaqti {hozir.strftime('%Y-%m-%d %H:%M')}).")

    if soat == KUNLIK_HISOBOT_SOAT:
        kunlik_hisobot()
    elif soat in CHECKPOINT_SOATLAR:
        checkpoint_tekshir(soat)
    else:
        _logga_yoz(f"Soat {soat} — bu soatda vazifa yo'q, chiqildi.")


if __name__ == "__main__":
    main()
