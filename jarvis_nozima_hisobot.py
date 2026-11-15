"""
Nozima — Buxgalter (Jarvis OS'ning birinchi yangi xodimi, 2026-09-27).

Har dushanba 09:00 (Toshkent) — AzizEdu (Orzu Akademy) va Grampus Junior FC
uchun joriy oyda kim to'lamagani haqida QISQA (5 qatorlik) hisobot yuboradi.

QAT'IY QOIDA (Azizbek buyrug'i): AI (Claude) UMUMAN ishlatilmaydi -- faqat
oddiy SQL (COUNT/JOIN). DB'ga FAQAT jarvis_readonly roli orqali (o'qish,
yozish jismonan mumkin emas -- default_transaction_read_only=on VA GRANT
faqat SELECT, ikkalasi ham 2026-09-21'da AzizEdu/Grampus kuzatuvida
sinovdan o'tgan).

Ishga tushirish: python jarvis_nozima_hisobot.py
Task Scheduler: "Nozima Oylik Hisobot" (har dushanba 09:00).
"""

import json
import shlex
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import config
from jarvis_proaktiv import telegram_xabar_yubor

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "jarvis_nozima_hisobot.log"
NATIJA_FILE = BASE_DIR / "nozima_oxirgi_natija.json"

TASHKENT_OFFSET = timedelta(hours=5)


def _tashkent_hozir() -> datetime:
    return datetime.utcnow() + TASHKENT_OFFSET


def _logga_yoz(matn: str):
    vaqt = _tashkent_hozir().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{vaqt}] {matn}\n")
    except Exception:
        pass
    print(f"[{vaqt}] {matn}")


def _ssh_psql(db_host: str, db_name: str, db_user: str, db_password: str, sql: str) -> str:
    """AzizEdu/Grampus kuzatuv skriptlaridagi (`jarvis_azizedu_kuzatuv.py`)
    bilan AYNAN bir xil naqsh -- SSH orqali Hetzner serverga kirib,
    jarvis_readonly roli bilan SQL bajaradi. -t -A -F'|' -- sarlavhasiz,
    '|' bilan ajratilgan natija."""
    remote_cmd = (
        f"PGPASSWORD={shlex.quote(db_password)} "
        f"psql -h {db_host} -U {db_user} -d {db_name} -t -A -F'|' -c {shlex.quote(sql)}"
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


def _azizedu_holati(oy: str) -> tuple[int, int]:
    """(jami_faol, tolagan) -- AzizEdu (Orzu Akademy), joriy oy.
    "To'lagan" = shu oy uchun KAMIDA bitta guruh bo'yicha holat='tolangan'
    yozuvi bor (bir nechta guruhga yozilgan o'quvchi uchun proksi -- to'liq
    aniqlik emas, lekin "oddiy SQL" talabiga mos sodda mezon)."""
    sql = f"""
        SELECT
            (SELECT COUNT(*) FROM oquvchilar
                WHERE organization_id='{config.AZIZEDU_ORG_ID}' AND faol=true),
            (SELECT COUNT(DISTINCT o.id) FROM oquvchilar o
                JOIN tolovlar t ON t.oquvchi_id = o.id
                WHERE o.organization_id='{config.AZIZEDU_ORG_ID}' AND o.faol=true
                    AND t.oy='{oy}' AND t.holat='tolangan')
    """
    qator = _ssh_psql(
        config.AZIZEDU_DB_HOST, config.AZIZEDU_DB_NAME,
        config.AZIZEDU_DB_USER, config.AZIZEDU_DB_PASSWORD, sql,
    )
    jami, tolagan = qator.split("|")
    return int(jami), int(tolagan)


def _grampus_holati(oy: str) -> tuple[int, int]:
    """(jami_faol, tolov_belgilangan) -- Grampus Junior FC, joriy oy.
    Haqiqiy so'm summasi emas (tolov_holatlari.summa 0-100000 bilan
    cheklangan, real oylik to'lov emas) -- faqat "holati='tolandi' deb
    belgilanganmi" soni."""
    sql = f"""
        SELECT
            (SELECT COUNT(*) FROM sportchilar
                WHERE organization_id='{config.GRAMPUS_ORG_ID}' AND ochirilgan_sana IS NULL),
            (SELECT COUNT(*) FROM sportchilar s
                JOIN tolov_holatlari th ON th.sportchi_id = s.id
                WHERE s.organization_id='{config.GRAMPUS_ORG_ID}' AND s.ochirilgan_sana IS NULL
                    AND th.oy='{oy}' AND th.holati='tolandi')
    """
    qator = _ssh_psql(
        config.GRAMPUS_DB_HOST, config.GRAMPUS_DB_NAME,
        config.GRAMPUS_DB_USER, config.GRAMPUS_DB_PASSWORD, sql,
    )
    jami, tolagan = qator.split("|")
    return int(jami), int(tolagan)


def hisobot_matnini_tuz() -> str:
    hozir = _tashkent_hozir()
    oy = hozir.strftime("%Y-%m")
    sana_matn = hozir.strftime("%Y-%m-%d")

    a_jami, a_tolagan = _azizedu_holati(oy)
    a_tolamagan = a_jami - a_tolagan

    g_jami, g_tolagan = _grampus_holati(oy)
    g_tolamagan = g_jami - g_tolagan

    # 2026-09-27 (Azizbek tuzatdi): "TO'LAMAGAN" o'rniga neytralroq ibora --
    # bu son aslida "haqiqatan to'lamagan" emas, balki "tizimda bu oy uchun
    # to'lov yozuvi/belgisi topilmadi" degani (masalan Grampus'da admin hali
    # kiritmagan bo'lishi mumkin, proaktiv_kuzatuv.md'da ham shu holat qayd
    # etilgan) -- noto'g'ri ayblov taassurotini bermaslik uchun.
    matn = (
        f"📋 Nozima — Oylik to'lov hisoboti ({oy}, {sana_matn})\n\n"
        f"AzizEdu (Orzu Akademy): {a_jami} faol o'quvchidan {a_tolagan} tasi "
        f"to'lagan, {a_tolamagan} tasida tizimda to'lovi yozilmagan.\n"
        f"Grampus Junior FC: {g_jami} faol sportchidan {g_tolagan} tasida to'lov "
        f"belgilangan, {g_tolamagan} tasida tizimda to'lovi yozilmagan.\n\n"
        f"Manba: jarvis_readonly (faqat o'qish), AI ishlatilmadi."
    )
    return matn


def natijani_saqla(matn: str, xato: str | None = None):
    try:
        NATIJA_FILE.write_text(
            json.dumps(
                {
                    "sana": _tashkent_hozir().strftime("%Y-%m-%d %H:%M:%S"),
                    "matn": matn,
                    "xato": xato,
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        _logga_yoz(f"natijani saqlashda xato: {e}")


def main():
    _logga_yoz("Ishga tushdi.")
    try:
        matn = hisobot_matnini_tuz()
    except Exception as e:
        xato_matni = f"⚠️ Nozima: hisobot tayyorlashda xato: {e}"
        _logga_yoz(f"XATO: {e}")
        natijani_saqla(None, xato=str(e))
        telegram_xabar_yubor(xato_matni)
        return
    _logga_yoz("Hisobot tayyor, yuborilmoqda.")
    telegram_xabar_yubor(matn)
    natijani_saqla(matn)
    _logga_yoz("Yuborildi.")


if __name__ == "__main__":
    main()
