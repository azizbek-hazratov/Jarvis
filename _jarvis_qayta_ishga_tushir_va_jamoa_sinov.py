"""
BIR MARTALIK skript (2026-09-27) -- Jarvisning asosiy jarayonini (jarvis_fon.py)
xavfsiz qayta ishga tushiradi va "jamoa" buyrug'ini sinab, natijasini Telegram
orqali yuboradi.

NEGA ALOHIDA SKRIPT: shu ishni so'ragan suhbatning o'zi aynan jarvis_fon.py
orqali ketayotgani uchun, Jarvis O'ZI o'zini o'ldirsa joriy javobi Azizbekka
yetib bormasligi mumkin edi. Shu sabab Task Scheduler orqali BIR MARTALIK,
mustaqil jarayon sifatida ishga tushiriladi (Jarvisning joriy jarayon
daraxtidan TASHQARIDA).

Ishi: (1) eski jarvis_fon.py jarayonini top+o'ldir, (2) "Jarvis" Task
Scheduler vazifasini qayta ishga tushir, (3) to'liq ko'tarilishini kutish,
(4) "jamoa" hisobotini sinab, natijani alohida Telegram xabar sifatida
yuborish, (5) o'zini (bu bir martalik Task Scheduler vazifasini) o'chirish.
"""

import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"C:\Users\Dell\jarvis")
sys.path.insert(0, str(BASE))

LOG_FILE = BASE / "_jarvis_qayta_ishga_tushir.log"


def log(matn: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {matn}\n")


def ps(cmd: str) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, timeout=30,
    )
    return r.stdout.strip()


def main():
    log("Boshlandi.")

    # 1) Eski jarvis_fon.py jarayon(lar)ini topib, butun daraxti bilan o'ldirish.
    pids_raw = ps(
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -like '*jarvis_fon.py*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    pids = [p.strip() for p in pids_raw.splitlines() if p.strip().isdigit()]
    log(f"Topilgan jarvis_fon.py PID(lar): {pids}")
    for pid in pids:
        subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
        log(f"O'ldirildi: PID {pid}")

    time.sleep(3)

    # 2) "Jarvis" Task Scheduler vazifasini qayta ishga tushirish.
    natija = ps("Start-ScheduledTask -TaskName 'Jarvis'; $?")
    log(f"Task Scheduler 'Jarvis' qayta ishga tushirildi: {natija}")

    # 3) To'liq ko'tarilib, Telegram'ga ulanishi uchun kutish.
    time.sleep(20)

    yangi_pids = ps(
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -like '*jarvis_fon.py*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    log(f"Qayta ishga tushgandan keyingi PID(lar): {yangi_pids.splitlines()}")

    # 4) "jamoa" hisobotini sinash va Telegram orqali yuborish.
    from jarvis_proaktiv import telegram_xabar_yubor
    try:
        from jarvis_jamoa_hisobot import jamoa_hisobot_matni
        jamoa_matni = jamoa_hisobot_matni()
        xabar = (
            "✅ Jarvis qayta ishga tushdi, \"jamoa\" buyrug'i endi FAOL.\n"
            "O'zim sinadim, natija:\n\n" + jamoa_matni
        )
    except Exception as e:
        xabar = f"⚠️ Jarvis qayta ishga tushdi, lekin \"jamoa\" sinovida xato: {e}"
        log(f"jamoa sinovida xato: {e}")

    ok = telegram_xabar_yubor(xabar)
    log(f"Xabar yuborildi: {ok}")

    # 5) O'zini (bir martalik Task Scheduler vazifasini) tozalash.
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Unregister-ScheduledTask -TaskName 'JarvisQaytaIshgaTushirBirMarta' -Confirm:$false"],
        capture_output=True,
    )
    log("Vazifa o'chirildi, yakunlandi.")


if __name__ == "__main__":
    main()
