"""
WATCHDOG — Jarvis botini kuzatib turadigan, undan MUSTAQIL alohida skript.

Maqsad: agar asosiy Jarvis jarayoni (jarvis_fon.py -> jarvis_telegram.py)
biror joyda qotib qolsa (masalan cheksiz kutish, deadlock), buni
diagnostika.log dagi "tirikman" heartbeat yozuvi orqali aniqlab, avtomatik
qayta ishga tushirish va Azizbekka Telegram orqali xabar berish.

MUHIM: bu fayl atayin Jarvis botining ichidan emas, alohida python
jarayoni sifatida ishga tushiriladi (hali Task Scheduler'ga qo'shilmagan,
qo'lda `python watchdog.py` bilan sinaladi). Shu sababli Telegram xabarini
ham asosiy botga bog'liq bo'lmagan holda, to'g'ridan-to'g'ri Bot API'ga
so'rov yuborib jo'natadi (userbot/monitor.py dagi notify_owner bilan bir xil
uslub).

Ishlash mantig'i (60 soniyada bir marta):
  1. diagnostika.log dagi ENG OXIRGI "tirikman" yozuvini topadi.
  2. Agar shu yozuvdan hozirgi vaqtgacha 90 soniyadan ko'p o'tgan bo'lsa
     (yoki umuman topilmasa) -> muammo deb hisoblaydi.
  3. Muammo bo'lsa: (a) Azizbekka Telegram orqali xabar beradi,
     (b) "Jarvis" Task Scheduler vazifasini to'xtatib qayta ishga
     tushiradi (qayta.ps1 bilan bir xil g'oya, lekin faqat aniq
     jarvis_fon.py jarayonini nishonga oladi — userbot yoki watchdog'ning
     o'zini emas), (c) buni watchdog.log ga vaqti va sababi bilan yozadi.
  4. Ketma-ket qayta-qayta restart bo'lib ketmasligi uchun ikki restart
     orasida kamida 5 daqiqa saqlanadi (watchdog_holat.json faylida
     saqlanadi, watchdog qayta ishga tushsa ham yo'qolmaydi).
  5. O'zi ikki nusxada ishlab ketmasligi uchun watchdog.lock fayli orqali
     himoyalangan.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

try:
    import psutil
except ImportError:
    print("XATO: psutil o'rnatilmagan. O'rnatish uchun: pip install psutil")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402  (TELEGRAM_TOKEN, OWNER_ID shu yerdan olinadi)

DIAG_LOG = BASE_DIR / "diagnostika.log"
WATCHDOG_LOG = BASE_DIR / "watchdog.log"
STATE_FILE = BASE_DIR / "watchdog_holat.json"
LOCK_FILE = BASE_DIR / "watchdog.lock"

TASK_NAME = "Jarvis"
ASOSIY_JARAYON_BELGISI = "jarvis_fon.py"  # asosiy botni aniqlash uchun (aniq belgi)
FON_VBS = BASE_DIR / "jarvis_fon.vbs"

TEKSHIRISH_ORALIGI = 60       # soniya — har necha soniyada tekshiradi
MAKSIMAL_SUKUNAT = 90         # soniya — shundan ko'p o'tsa, qotib qolgan deb hisoblanadi
RESTART_SOVUSH_VAQTI = 5 * 60  # soniya — ikki restart orasidagi minimal oraliq
BOSHLANGICH_KUTISH = 3 * 60    # soniya — watchdog ishga tushgandan keyin birinchi
                               # tekshiruvdan oldingi kutish (Jarvis ulgurishi uchun)


# ---------------------------------------------------------------------------
# Yordamchi: log yozish
# ---------------------------------------------------------------------------

def log_watchdog(matn: str) -> None:
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{vaqt}] {matn}\n")
    except Exception:
        pass
    # konsolga ham chiqarib turamiz (qo'lda sinashda ko'rinib tursin)
    print(f"[{vaqt}] {matn}")


# ---------------------------------------------------------------------------
# Ikki nusxada ishlamaslik himoyasi
# ---------------------------------------------------------------------------

def boshqa_nusxa_ishlayaptimi() -> bool:
    """Lock faylini tekshiradi. Agar undagi PID hali ham watchdog.py sifatida
    tirik bo'lsa -> True (bu nusxa chiqishi kerak). Aks holda lock'ni
    o'ziniki qilib yozib qo'yadi va False qaytaradi."""
    if LOCK_FILE.exists():
        try:
            eski_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            eski_pid = None

        if eski_pid and eski_pid != os.getpid() and psutil.pid_exists(eski_pid):
            try:
                jarayon = psutil.Process(eski_pid)
                cmdline = " ".join(jarayon.cmdline()).lower()
            except Exception:
                cmdline = ""
            if "watchdog.py" in cmdline:
                return True  # boshqa nusxa haqiqatan ishlayapti

    # lock bo'sh, eskirgan yoki begona jarayonga tegishli — o'zimizga yozamiz
    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass
    return False


def lockni_bosalish() -> None:
    try:
        if LOCK_FILE.exists():
            eski_pid = LOCK_FILE.read_text(encoding="utf-8").strip()
            if eski_pid == str(os.getpid()):
                LOCK_FILE.unlink()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Holat fayli (oxirgi restart vaqtini eslab qolish uchun)
# ---------------------------------------------------------------------------

def holatni_oqi() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def holatni_yoz(holat: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(holat, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log_watchdog(f"holatni_yoz xatosi: {e}")


# ---------------------------------------------------------------------------
# diagnostika.log dagi oxirgi "tirikman" yozuvini topish
# ---------------------------------------------------------------------------

def oxirgi_tirikman_vaqti():
    """diagnostika.log dagi eng oxirgi 'tirikman' qatorini topib, uni
    to'liq datetime'ga aylantirib qaytaradi. Topilmasa None."""
    if not DIAG_LOG.exists():
        return None

    try:
        # Fayl juda katta bo'lib ketsa ham tez ishlashi uchun oxirgi ~50KB
        # ni o'qiymiz — bu bir necha yuzlab qatorga yetadi.
        with open(DIAG_LOG, "rb") as f:
            f.seek(0, os.SEEK_END)
            hajm = f.tell()
            f.seek(max(0, hajm - 50_000))
            qismi = f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        log_watchdog(f"diagnostika.log o'qishda xato: {e}")
        return None

    qatorlar = qismi.splitlines()
    for qator in reversed(qatorlar):
        if "tirikman" not in qator:
            continue
        # format: [14:35:57.364] tirikman
        try:
            vaqt_matni = qator.split("]", 1)[0].lstrip("[").strip()
            faqat_vaqt = datetime.strptime(vaqt_matni, "%H:%M:%S.%f").time()
        except Exception:
            continue

        hozir = datetime.now()
        natija = datetime.combine(hozir.date(), faqat_vaqt)
        # log faylida sana yo'q — agar hisoblangan vaqt hozirdan
        # kelajakda chiqib qolsa (masalan yozuv kecha, hozir yarim
        # tundan keyin), demak u kecha yozilgan.
        if natija > hozir + timedelta(seconds=5):
            natija -= timedelta(days=1)
        return natija

    return None


# ---------------------------------------------------------------------------
# Telegram orqali to'g'ridan-to'g'ri xabar (asosiy bot jarayoniga bog'liq emas)
# ---------------------------------------------------------------------------

def owner_ga_xabar(matn: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": config.OWNER_ID, "text": matn},
            timeout=10,
        )
    except Exception as e:
        log_watchdog(f"owner_ga_xabar yuborib bo'lmadi: {e}")


# ---------------------------------------------------------------------------
# Jarvis'ni qayta ishga tushirish (qayta.ps1 bilan bir xil g'oya)
# ---------------------------------------------------------------------------

def jarvis_jarayonlarini_top():
    natija = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            nomi = (p.info["name"] or "").lower()
            if nomi not in ("python.exe", "pythonw.exe"):
                continue
            cmdline = " ".join(p.info["cmdline"] or []).lower()
            if ASOSIY_JARAYON_BELGISI in cmdline and p.info["pid"] != os.getpid():
                natija.append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return natija


def vazifa_mavjudmi() -> bool:
    natija = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True, text=True,
    )
    return natija.returncode == 0


def jarvisni_qayta_ishga_tushir():
    """qayta.ps1 bilan bir xil ketma-ketlik: to'xtat -> qolganini o'ldir
    -> qayta ishga tushir. (muvaffaqiyat: bool, tafsilot: str) qaytaradi."""
    tafsilotlar = []

    vazifa_bor = vazifa_mavjudmi()

    if vazifa_bor:
        subprocess.run(["schtasks", "/End", "/TN", TASK_NAME],
                        capture_output=True, text=True)
        tafsilotlar.append("vazifa to'xtatildi")
    else:
        tafsilotlar.append("Task Scheduler vazifasi topilmadi")

    time.sleep(2)

    qoldiq_pidlar = jarvis_jarayonlarini_top()
    for pid in qoldiq_pidlar:
        try:
            psutil.Process(pid).kill()
        except Exception:
            pass
    if qoldiq_pidlar:
        tafsilotlar.append(f"qolgan jarayonlar o'ldirildi: {qoldiq_pidlar}")

    time.sleep(2)

    if vazifa_bor:
        subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME],
                        capture_output=True, text=True)
        tafsilotlar.append("vazifa qayta ishga tushirildi")
    else:
        # zaxira yo'l: vbs orqali yashirin holda ishga tushiramiz
        try:
            subprocess.Popen(["wscript.exe", str(FON_VBS)])
            tafsilotlar.append("run_bot to'g'ridan-to'g'ri (vbs orqali) ishga tushirildi")
        except Exception as e:
            tafsilotlar.append(f"to'g'ridan-to'g'ri ishga tushirishda xato: {e}")

    time.sleep(5)

    yangi_pidlar = jarvis_jarayonlarini_top()
    muvaffaqiyat = len(yangi_pidlar) > 0
    if muvaffaqiyat:
        tafsilotlar.append(f"tasdiqlandi, yangi PID: {yangi_pidlar}")
    else:
        tafsilotlar.append("OGOHLANTIRISH: qayta ishga tushgani tasdiqlanmadi")

    return muvaffaqiyat, "; ".join(tafsilotlar)


# ---------------------------------------------------------------------------
# Asosiy tekshiruv sikli
# ---------------------------------------------------------------------------

def bir_marta_tekshir(holat: dict) -> dict:
    oxirgi_vaqt = oxirgi_tirikman_vaqti()
    hozir = datetime.now()

    if oxirgi_vaqt is None:
        muammo = True
        sabab = "diagnostika.log topilmadi yoki unda 'tirikman' yozuvi yo'q"
    else:
        sukunat = (hozir - oxirgi_vaqt).total_seconds()
        muammo = sukunat > MAKSIMAL_SUKUNAT
        sabab = f"oxirgi 'tirikman' yozuvidan {sukunat:.0f} soniya o'tdi"

    if not muammo:
        return holat

    oxirgi_restart_str = holat.get("oxirgi_restart")
    if oxirgi_restart_str:
        oxirgi_restart = datetime.fromisoformat(oxirgi_restart_str)
        sovish_qoldi = RESTART_SOVUSH_VAQTI - (hozir - oxirgi_restart).total_seconds()
        if sovish_qoldi > 0:
            log_watchdog(
                f"MUAMMO ({sabab}), lekin sovish davri tugamagan "
                f"(yana {sovish_qoldi:.0f}s kutish kerak) — restart qilinmadi"
            )
            return holat

    log_watchdog(f"MUAMMO ANIQLANDI: {sabab}. Qayta ishga tushirish boshlanmoqda...")
    owner_ga_xabar(f"⚠️ Jarvis qotib qoldi ({sabab}). Avtomatik qayta ishga tushiryapman...")

    muvaffaqiyat, tafsilot = jarvisni_qayta_ishga_tushir()
    holat["oxirgi_restart"] = hozir.isoformat()
    holatni_yoz(holat)

    log_watchdog(f"Qayta ishga tushirish natijasi: {tafsilot}")
    if muvaffaqiyat:
        owner_ga_xabar("✅ Jarvis qayta ishga tushirildi.")
    else:
        owner_ga_xabar(f"❌ Jarvis qayta ishga tushirilganda muammo bo'ldi: {tafsilot}")

    return holat


def main():
    if boshqa_nusxa_ishlayaptimi():
        log_watchdog("Watchdog allaqachon boshqa nusxada ishlab turibdi — bu nusxa chiqadi.")
        sys.exit(0)

    log_watchdog(
        f"Watchdog ishga tushdi (PID {os.getpid()}). "
        f"Har {TEKSHIRISH_ORALIGI}s tekshiradi, {MAKSIMAL_SUKUNAT}s sukunatdan keyin "
        f"muammo deb hisoblaydi, restartlar orasi kamida {RESTART_SOVUSH_VAQTI}s."
    )

    log_watchdog(
        f"Boshlang'ich kutish: {BOSHLANGICH_KUTISH}s — bu vaqt Jarvis (odatda "
        f"watchdog bilan bir vaqtda, LogonTrigger orqali) to'liq ishga tushib, "
        f"birinchi haqiqiy 'tirikman' yozuvini ulgurishiga beriladi. Shu davrda "
        f"eski/qolgan yozuv yolg'on signal bermasligi uchun tekshiruv qilinmaydi."
    )
    time.sleep(BOSHLANGICH_KUTISH)

    holat = holatni_oqi()
    try:
        while True:
            try:
                holat = bir_marta_tekshir(holat)
            except Exception as e:
                log_watchdog(f"Tekshiruv siklida kutilmagan xato: {e}")
            time.sleep(TEKSHIRISH_ORALIGI)
    except KeyboardInterrupt:
        log_watchdog("Watchdog qo'lda to'xtatildi (Ctrl+C).")
    finally:
        lockni_bosalish()


if __name__ == "__main__":
    main()
