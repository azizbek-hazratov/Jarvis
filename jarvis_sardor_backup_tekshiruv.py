"""
Sardor — Nazoratchi: kunlik backup tekshiruvi (2026-09-27).

Har kuni 08:30 (Toshkent) -- Hetzner serverdagi 3 ta baza (Nishon, AzizEdu/
oquv_markaz, Dasturxon) uchun BUGUNGI tungi backup muvaffaqiyatli o'tganini
tekshiradi (mavjud backup skriptlari yozgan logni FAQAT O'QIYDI -- hech
narsa yozmaydi/ishga tushirmaydi).

QOIDA (Azizbek buyrug'i): faqat MUAMMO bo'lsa Telegram xabar yuboradi.
Hammasi joyida bo'lsa -- jim, faqat lokal log+holat faylga yozadi.

Ishga tushirish: python jarvis_sardor_backup_tekshiruv.py
Task Scheduler: "Sardor Backup Tekshiruvi" (har kuni 08:30).
"""

import json
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
LOG_FILE = BASE_DIR / "jarvis_sardor_backup_tekshiruv.log"
HOLAT_FILE = BASE_DIR / "sardor_backup_holat.json"

TASHKENT_OFFSET = timedelta(hours=5)

# (nomi, log fayl yo'li, "muvaffaqiyat" belgisi shu matnni o'z ichiga olishi kerak)
# TUZATISH (2026-11-02): "Dasturxon" serverdagi crontab'da 2026-10-08'dan
# beri ATAYLAB MUZLATILGAN (`# ... MUZLATILDI 2026-10-08` izohi bilan) --
# shu sabab bu yerda ham ro'yxatdan olib tashlandi, aks holda har kuni
# "backup ishlamagan" soxta signal berardi (haqiqiy muammo emas, Azizbek
# o'zi to'xtatgan). Dasturxon qayta yoqilsa -- shu qatorni qaytaring:
# ("Dasturxon", "/root/db-backup/logs/dasturxon.log", "muvaffaqiyatli yakunlandi"),
BAZALAR = [
    ("Nishon", "/root/nishon-platform/logs/backup.log", "Zaxira tugadi."),
    ("AzizEdu (oquv_markaz)", "/root/db-backup/logs/oquv_markaz.log", "muvaffaqiyatli yakunlandi"),
]


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


def _ssh_run(remote_cmd: str, urinishlar: int = 3) -> str:
    # TUZATISH (2026-11-02, Azizbek audit so'rovi paytida topildi): bu
    # skript Task Scheduler ostida ("Sardor Backup Tekshiruvi", S4U logon
    # turi) 2026-10-14'dan beri DEYARLI HAR KUNI SSH ulanish xatosi
    # ("Unknown error"/timeout) bergan -- HAQIQIY backup esa (serverda
    # to'g'ridan-to'g'ri tekshirilganda) har kuni muvaffaqiyatli bo'lgan.
    # Ya'ni muammo SERVERDA/backup'da EMAS -- shu skriptning S4U sessiyadan
    # SSH ulanishi vaqti-vaqti bilan (tranzient) muvaffaqiyatsiz bo'lgan,
    # natijada Azizbekka 3+ hafta deyarli har kuni NOTO'G'RI "backup
    # muammosi" xabari ketgan. Tuzatish: shu tranzient xatolarni ichkarida
    # engish uchun 3 marta qayta urinish (har birida 5 soniya kutish) --
    # agar HAQIQATAN server/backup muammosi bo'lsa, 3 urinishdan keyin ham
    # xato qoladi va Telegram xabari TO'G'RI yuboriladi.
    import time
    oxirgi_xato = None
    for urinish in range(1, urinishlar + 1):
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
        try:
            natija = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
        except subprocess.TimeoutExpired as e:
            oxirgi_xato = RuntimeError(f"ssh timeout (urinish {urinish}/{urinishlar}): {e}")
            _logga_yoz(f"_ssh_run: urinish {urinish}/{urinishlar} timeout, qayta uriniladi...")
            time.sleep(5)
            continue
        if natija.returncode != 0:
            oxirgi_xato = RuntimeError(f"ssh xato (kod {natija.returncode}, urinish {urinish}/{urinishlar}): {natija.stderr.strip()}")
            if urinish < urinishlar:
                _logga_yoz(f"_ssh_run: urinish {urinish}/{urinishlar} muvaffaqiyatsiz ({natija.stderr.strip()[:100]}), 5s kutib qayta uriniladi...")
                time.sleep(5)
                continue
            raise oxirgi_xato
        return natija.stdout
    raise oxirgi_xato


def tekshir() -> dict:
    """Har baza uchun {"ok": bool, "sabab": str} qaytaradi."""
    # Server UTC'da ishlaydi (Etc/UTC) -- 08:30 Toshkent = 03:30 UTC, bu UTC
    # kun almashinuvidan (00:00 UTC) ancha keyin, shuning uchun "bugungi UTC
    # sana" bilan solishtirish xavfsiz (Tashkent va UTC kalendar kunlari mos).
    bugun_utc = datetime.utcnow().strftime("%Y-%m-%d")

    natijalar = {}
    for nomi, log_yoli, muvaffaqiyat_belgisi in BAZALAR:
        try:
            tail = _ssh_run(f"tail -5 {log_yoli} 2>&1 || echo '__FAYL_YOQ__'")
        except Exception as e:
            natijalar[nomi] = {"ok": False, "sabab": f"SSH/log o'qishda xato: {e}"}
            continue

        if "__FAYL_YOQ__" in tail or not tail.strip():
            natijalar[nomi] = {"ok": False, "sabab": "Log fayli topilmadi/bo'sh"}
            continue

        bugungi_qatorlar = [q for q in tail.splitlines() if bugun_utc in q]
        if not bugungi_qatorlar:
            natijalar[nomi] = {"ok": False, "sabab": f"Bugungi ({bugun_utc}) yozuv topilmadi -- backup ishlamagan bo'lishi mumkin"}
            continue

        oxirgi_qator = bugungi_qatorlar[-1]
        if "XATO" in oxirgi_qator.upper() or muvaffaqiyat_belgisi not in tail:
            natijalar[nomi] = {"ok": False, "sabab": f"Muvaffaqiyat belgisi topilmadi. Oxirgi qator: {oxirgi_qator}"}
            continue

        natijalar[nomi] = {"ok": True, "sabab": oxirgi_qator}

    return natijalar


def holatni_saqla(natijalar: dict):
    try:
        HOLAT_FILE.write_text(
            json.dumps(
                {
                    "sana": _tashkent_hozir().strftime("%Y-%m-%d %H:%M:%S"),
                    "natijalar": natijalar,
                    "hammasi_ok": all(n["ok"] for n in natijalar.values()),
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        _logga_yoz(f"holatni saqlashda xato: {e}")


def main():
    _logga_yoz(f"Ishga tushdi -- {len(BAZALAR)} baza backup logini tekshirmoqda.")
    try:
        natijalar = tekshir()
    except Exception as e:
        _logga_yoz(f"KUTILMAGAN XATO: {e}")
        telegram_xabar_yubor(f"⚠️ Sardor: backup tekshiruvida kutilmagan xato: {e}")
        return

    holatni_saqla(natijalar)

    muammolar = {nomi: n for nomi, n in natijalar.items() if not n["ok"]}
    if not muammolar:
        _logga_yoz(f"Hammasi joyida ({len(natijalar)}/{len(natijalar)} baza bugun muvaffaqiyatli backup qilingan). Jim -- xabar yuborilmaydi.")
        return

    satrlar = [f"⚠️ Sardor: backup muammosi topildi ({len(muammolar)}/{len(natijalar)} baza)!\n"]
    for nomi, n in muammolar.items():
        satrlar.append(f"❌ {nomi}: {n['sabab']}")
    for nomi, n in natijalar.items():
        if n["ok"]:
            satrlar.append(f"✅ {nomi}: OK")
    matn = "\n".join(satrlar)
    _logga_yoz(f"MUAMMO TOPILDI: {muammolar}")
    telegram_xabar_yubor(matn)


if __name__ == "__main__":
    main()
