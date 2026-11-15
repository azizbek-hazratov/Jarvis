"""
Jarvis — rejalashtirilgan qayta yuklanishdan keyingi DISM (WinSxS) tozalash
+ tekshiruv skripti (2026-09-23, Azizbek buyrug'i bilan).

Ishlash tartibi:
1. "Jarvis DISM Reboot" vazifasi (bir martalik, 03:00 Toshkent) qayta
   yuklashdan OLDIN joriy C: bo'sh joyni `dism_before.txt`ga yozadi va
   `shutdown /r` chaqiradi.
2. Qayta yuklangach, "Jarvis DISM Tekshiruv" vazifasi (AtStartup, 3 daqiqa
   kechikish bilan) shu faylni ishga tushiradi.
3. Bu fayl: birozroq kutadi (tizim/vazifalar to'liq stabillashishi uchun),
   DISM /StartComponentCleanup'ni ishga tushiradi, C: bo'sh joyni oldin/
   keyin solishtiradi, uchta muhim vazifa (AI Expert Bot, Jarvis HUD
   Bridge, Jarvis HUD Frontend) holatini tekshiradi, va Telegram orqali
   Azizbekka hisobot yuboradi. Oxirida ikkala vazifani (reboot + shu
   tekshiruv) Task Scheduler'dan o'chiradi — kelajakdagi har bir oddiy
   qayta yuklanishda qayta ishlab ketmasligi uchun.
"""

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
BEFORE_FILE = BASE_DIR / "dism_before.txt"
LOG_FILE = BASE_DIR / "dism_reboot_tugatuv.log"

sys.path.insert(0, str(BASE_DIR))
import config  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402

TEKSHIRILADIGAN_VAZIFALAR = ["AI Expert Bot", "Jarvis HUD Bridge", "Jarvis HUD Frontend"]


def logga_yoz(matn: str) -> None:
    vaqt = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{vaqt}] {matn}\n")


def telegram_xabar_yubor(matn: str) -> bool:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": config.OWNER_ID, "text": matn}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        logga_yoz(f"Telegram xabar yuborishda xato: {e!r}")
        return False


def free_gb_c() -> float:
    out = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         "(Get-PSDrive C).Free"],
        capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    try:
        return round(float(out) / (1024 ** 3), 2)
    except Exception:
        return -1.0


def vazifa_holati(nom: str) -> str:
    ps = (
        f"$t = Get-ScheduledTask -TaskName '{nom}' -ErrorAction SilentlyContinue; "
        f"if ($t) {{ $i = Get-ScheduledTaskInfo -TaskName '{nom}'; "
        f"\"$($t.State)|$($i.LastRunTime)|$($i.LastTaskResult)\" }} else {{ 'TOPILMADI' }}"
    )
    out = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    return out or "NOMA'LUM"


def main() -> None:
    logga_yoz("Ishga tushdi (qayta yuklangandan keyin).")
    # Tizim va logon-trigger vazifalar to'liq stabillashishi uchun kutish.
    time.sleep(120)

    before = None
    if BEFORE_FILE.exists():
        try:
            before = float(BEFORE_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            before = None

    logga_yoz("DISM StartComponentCleanup boshlandi...")
    dism = subprocess.run(
        ["Dism", "/Online", "/Cleanup-Image", "/StartComponentCleanup", "/NoRestart"],
        capture_output=True, text=True, timeout=1800,
    )
    dism_ok = dism.returncode == 0
    logga_yoz(f"DISM tugadi, kod={dism.returncode}")
    logga_yoz(dism.stdout[-2000:])
    if dism.stderr:
        logga_yoz("STDERR: " + dism.stderr[-1000:])

    after = free_gb_c()

    vazifa_natija = {}
    for nom in TEKSHIRILADIGAN_VAZIFALAR:
        vazifa_natija[nom] = vazifa_holati(nom)
    logga_yoz(f"Vazifalar holati: {vazifa_natija}")

    qatorlar = ["🖥️ Rejalashtirilgan qayta yuklanish + DISM tugadi.", ""]
    if before is not None:
        qatorlar.append(f"C: bo'sh joy: {before:.2f} GB → {after:.2f} GB (+{after-before:.2f} GB)")
    else:
        qatorlar.append(f"C: bo'sh joy hozir: {after:.2f} GB (oldingi qiymat topilmadi)")
    qatorlar.append(f"DISM natijasi: {'muvaffaqiyatli ✅' if dism_ok else f'XATO (kod {dism.returncode}) ⚠️'}")
    qatorlar.append("")
    qatorlar.append("Vazifalar holati (qayta yuklangandan keyin o'zi tiklandimi):")
    for nom, natija in vazifa_natija.items():
        holat = natija.split("|")[0] if "|" in natija else natija
        belgi = "✅" if holat in ("Running", "Ready") else "⚠️"
        qatorlar.append(f"  {belgi} {nom}: {natija}")

    xabar = "\n".join(qatorlar)
    yuborildi = telegram_xabar_yubor(xabar)
    logga_yoz(f"Telegram xabar yuborildi: {yuborildi}")

    # O'z-o'zini va reboot-vazifasini Task Scheduler'dan o'chirish — kelajakdagi
    # oddiy qayta yuklanishlarda qayta ishlab ketmasligi uchun.
    for tn in ["Jarvis DISM Tekshiruv", "Jarvis DISM Reboot"]:
        subprocess.run(["schtasks", "/Delete", "/TN", tn, "/F"], capture_output=True)
    logga_yoz("Ikkala vazifa (reboot+tekshiruv) Task Scheduler'dan o'chirildi. Tugadi.")


if __name__ == "__main__":
    main()
