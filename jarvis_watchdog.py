"""
Jarvis — o'z-o'zini kuzatuvchi watchdog (2026-09-27, Azizbek buyrug'i).

SABAB: AI Expert va JetCafe botlarida topilgan "tirik-lekin-o'lik" holat
(jarayon TIRIK, lekin Telegram bilan aloqa/polling ISHLAMAYDI) Jarvisning
O'ZIDA ham takrorlanishi mumkin. Eski "Jarvis Watchdog" vazifasi (`watchdog_fon.py`)
ESKIRGAN naqsh bilan ishlagan (faqat jarayon jonligini, Telegram bilan haqiqiy
aloqani EMAS) — endi ai_expert_bot/jetcafe_bot'dagi TO'G'RI mezon bilan
almashtirildi: `heartbeat_jarvis.json`dagi `last_ok` FAQAT `get_me()`
muvaffaqiyatli VA `app.updater.running` bo'lganda yangilanadi
(`jarvis_telegram.py`ga qarang).

MUHIM FARQ: Jarvis UZOQ vazifa bajarayotganda (masalan 15-40 daqiqalik ish)
`handle()`dagi `lock` band bo'ladi, LEKIN heartbeat bundan MUSTAQIL, alohida
asyncio task sifatida yozilib turadi (polling o'zi ham band-holatdan
mustaqil ishlaydi) — shuning uchun "band" holat "qotib qolgan" deb
XATO talqin qilinmaydi, watchdog Jarvisni band paytida O'LDIRMAYDI.

Jarayonni o'ldirish: FAQAT `jarvis_fon.py`ni ishga tushirgan aniq jarayon
(to'liq CommandLine bo'yicha) VA uning bola jarayonlari (ParentProcessId
bo'yicha, masalan Claude Agent SDK CLI subprocess'i) — boshqa hech qanday
botga tegilmaydi. Qayta ishga tushirish "Jarvis" Task Scheduler vazifasi
orqali (`Start-ScheduledTask`), to'g'ri sessiya/muhit kontekstini saqlab
qolish uchun (to'g'ridan-to'g'ri `subprocess.Popen` EMAS).

Ishga tushirish: Task Scheduler orqali, har 5 daqiqada, pythonw.exe bilan.
Qo'lda sinash: python jarvis_watchdog.py
"""

import json
import logging
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HEARTBEAT_FAYL = BASE_DIR / "heartbeat_jarvis.json"
LOG_FAYL = BASE_DIR / "watchdog_jarvis.log"
HOLAT_FAYL = BASE_DIR / "watchdog_jarvis_holat.json"
ESKIRISH_DAQIQA = 10
OGOHLANTIRISH_ORALIGI_DAQIQA = 60  # soatiga ko'pi bilan 1 ta ogohlantirish
TASK_NOMI = "Jarvis"
# 2026-09-27 TUZATISH: 15:32'da heartbeat_jarvis.json HALI YOZILMAGAN edi
# (Jarvis hali to'liq ishga tushmagan -- jarvis.__aenter__() davom etayotgan
# edi), watchdog buni "muammo" deb xato talqin qilib, hali ishga tushayotgan
# jarayonni o'ldirib qo'ydi. Endi: jarayon shu chegaradan yosh bo'lsa,
# heartbeat qanday bo'lishidan qat'i nazar TEGILMAYDI (hali ishga tushmoqda
# deb hisoblanadi).
YOSHLIK_CHEGARA_DAQIQA = 10

logging.basicConfig(
    filename=str(LOG_FAYL),
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("jarvis_watchdog")

try:
    from config import TELEGRAM_TOKEN as JARVIS_TOKEN, OWNER_ID as JARVIS_OWNER_ID
except Exception as e:
    JARVIS_TOKEN = None
    JARVIS_OWNER_ID = None
    log.error("config.py'ni import qilib bo'lmadi (Telegram xabar ishlamaydi): %s", e)


def telegram_xabar_yubor(matn: str) -> None:
    if not JARVIS_TOKEN or not JARVIS_OWNER_ID:
        log.error("Telegram xabar yuborilmadi -- token/owner_id yo'q.")
        return
    try:
        url = f"https://api.telegram.org/bot{JARVIS_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": JARVIS_OWNER_ID, "text": matn}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            if not (200 <= resp.status < 300):
                log.error("Telegram xabar yuborishda kutilmagan status: %s", resp.status)
    except Exception as e:
        log.error("Telegram xabar yuborishda xato: %s", e)


def holat_oqi() -> dict:
    if not HOLAT_FAYL.exists():
        return {"oxirgi_ogohlantirish": None, "muammoda": False}
    try:
        return json.loads(HOLAT_FAYL.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("watchdog_jarvis_holat.json o'qib bo'lmadi (yangidan boshlanadi): %s", e)
        return {"oxirgi_ogohlantirish": None, "muammoda": False}


def holat_yoz(holat: dict) -> None:
    try:
        HOLAT_FAYL.write_text(json.dumps(holat, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log.error("watchdog_jarvis_holat.json yozib bo'lmadi: %s", e)


def last_ok_eskirganmi():
    """(eskirganmi: bool, sabab: str|None) qaytaradi."""
    if not HEARTBEAT_FAYL.exists():
        return True, "heartbeat_jarvis.json fayli umuman yo'q"
    try:
        d = json.loads(HEARTBEAT_FAYL.read_text(encoding="utf-8"))
    except Exception as e:
        return True, f"heartbeat faylini o'qib bo'lmadi: {e}"
    last_ok = d.get("last_ok")
    if not last_ok:
        return True, "last_ok hali hech qachon yozilmagan (Jarvis hali Telegram'ga bir marta ham ulanmagan)"
    try:
        t = datetime.strptime(last_ok, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return True, f"last_ok formati noto'g'ri: {last_ok!r}"
    farq = datetime.now() - t
    if farq > timedelta(minutes=ESKIRISH_DAQIQA):
        daqiqa = int(farq.total_seconds() // 60)
        return True, f"last_ok {daqiqa} daqiqa oldin edi (limit {ESKIRISH_DAQIQA} daqiqa)"
    return False, None


def _ps_run(ps: str) -> str:
    natija = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=30,
    )
    return natija.stdout


def jarvis_fon_pidlarini_top():
    """FAQAT aynan `jarvis_fon.py`ni ishga tushirgan jarayon(lar)ni topadi --
    umumiy "pythonw.exe" nomi bo'yicha EMAS, to'liq buyruq qatori bo'yicha."""
    belgi = "jarvis_fon.py"
    ps = (
        "Get-CimInstance Win32_Process -Filter \"name='pythonw.exe' or name='python.exe'\" "
        "| Where-Object { $_.CommandLine -like '*" + belgi + "*' } "
        "| Select-Object -ExpandProperty ProcessId"
    )
    try:
        return [int(p) for p in _ps_run(ps).split() if p.strip().isdigit()]
    except Exception as e:
        log.error("jarvis_fon.py jarayonini qidirishda xato: %s", e)
        return []


def jarayon_yoshi_daqiqada(pid: int):
    """Berilgan PID qachon ishga tushganini (Windows jarayon StartTime'i)
    tekshirib, hozirgacha necha daqiqa o'tganini qaytaradi. Aniqlab
    bo'lmasa (jarayon topilmadi/xato) None qaytaradi."""
    ps = f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).StartTime.ToString('yyyy-MM-dd HH:mm:ss')"
    try:
        natija = _ps_run(ps).strip()
        if not natija:
            return None
        boshlanish = datetime.strptime(natija, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - boshlanish).total_seconds() / 60
    except Exception as e:
        log.error("PID %s yoshini aniqlashda xato: %s", pid, e)
        return None


def bola_pidlarini_top(ota_pidlar):
    """Berilgan ota-PID(lar)ga ega bo'lgan BARCHA bola jarayonlarni topadi
    (masalan Claude Agent SDK CLI subprocess'i) -- ParentProcessId bo'yicha."""
    natija = []
    for ota_pid in ota_pidlar:
        ps = f"Get-CimInstance Win32_Process -Filter \"ParentProcessId={ota_pid}\" | Select-Object -ExpandProperty ProcessId"
        try:
            natija.extend(int(p) for p in _ps_run(ps).split() if p.strip().isdigit())
        except Exception as e:
            log.error("PID %s ning bolalarini qidirishda xato: %s", ota_pid, e)
    return natija


def jarayonlarni_oldirish():
    ota_pidlar = jarvis_fon_pidlarini_top()
    if not ota_pidlar:
        log.warning("jarvis_fon.py jarayoni topilmadi (allaqachon o'lgan bo'lishi mumkin).")
        return

    bola_pidlar = bola_pidlarini_top(ota_pidlar)

    # Avval bolalarni, keyin otalarni o'ldiramiz (ota `/T /F` bilan ham
    # o'z pastki daraxtini o'ldiradi, bu FAQAT qo'shimcha ehtiyot chorasi --
    # ParentProcessId orqali qolib ketishi mumkin bo'lgan har qanday
    # jarayonni ham qamrab olish uchun, Azizbek aniq shuni so'ragan).
    for pid in bola_pidlar:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=15)
            log.info("Bola jarayon o'ldirildi: PID %s", pid)
        except Exception as e:
            log.error("Bola PID %s ni o'ldirishda xato: %s", pid, e)

    for pid in ota_pidlar:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=15)
            log.info("jarvis_fon.py jarayoni o'ldirildi (daraxti bilan): PID %s", pid)
        except Exception as e:
            log.error("PID %s ni o'ldirishda xato: %s", pid, e)


def jarvis_vazifasini_qayta_ishga_tushir():
    """`subprocess.Popen` O'RNIGA `Start-ScheduledTask` ishlatiladi -- "Jarvis"
    vazifasi allaqachon to'g'ri sessiya/muhit (Interactive, Claude Code OAuth
    uchun kerak) bilan sozlangan, uni qayta yaratishga hojat yo'q."""
    ps = f'Start-ScheduledTask -TaskName "{TASK_NOMI}"'
    natija = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=30,
    )
    if natija.returncode != 0:
        raise RuntimeError(f"Start-ScheduledTask xato qaytardi: {natija.stderr.strip()}")


def main():
    holat = holat_oqi()
    eskirgan, sabab = last_ok_eskirganmi()

    if not eskirgan:
        log.info("Holat yaxshi, aralashuv shart emas.")
        if holat.get("muammoda"):
            telegram_xabar_yubor(
                "✅ Jarvis tiklandi -- polling qayta normal ishlayapti.\n"
                f"Vaqt: {datetime.now():%Y-%m-%d %H:%M:%S}"
            )
            log.info("Tiklanish xabari yuborildi.")
        holat_yoz({"oxirgi_ogohlantirish": holat.get("oxirgi_ogohlantirish"), "muammoda": False})
        return

    # YANGI (2026-09-27): jarayon hozirgina ishga tushgan bo'lishi mumkin
    # (heartbeat hali ulgurmagan) -- bunday holda TEGMAYMIZ.
    ota_pidlar = jarvis_fon_pidlarini_top()
    if ota_pidlar:
        yoshlar = [y for y in (jarayon_yoshi_daqiqada(p) for p in ota_pidlar) if y is not None]
        if yoshlar and min(yoshlar) < YOSHLIK_CHEGARA_DAQIQA:
            log.info(
                "'Muammo' ko'rindi (%s), lekin jarvis_fon.py jarayoni hali yosh "
                "(%.1f daqiqa, chegara %d daqiqa) -- hali to'liq ishga tushmagan deb "
                "hisoblanib, HECH NARSA QILINMADI.",
                sabab, min(yoshlar), YOSHLIK_CHEGARA_DAQIQA,
            )
            return

    log.warning("MUAMMO topildi: %s. jarvis_fon.py va bola jarayonlari o'ldirilib, 'Jarvis' vazifasi qayta ishga tushiriladi.", sabab)

    jarayonlarni_oldirish()

    oxirgi = holat.get("oxirgi_ogohlantirish")
    ogohlantirish_kerak = True
    if oxirgi:
        try:
            oxirgi_vaqt = datetime.strptime(oxirgi, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - oxirgi_vaqt < timedelta(minutes=OGOHLANTIRISH_ORALIGI_DAQIQA):
                ogohlantirish_kerak = False
        except Exception:
            pass

    try:
        jarvis_vazifasini_qayta_ishga_tushir()
        log.info("'%s' vazifasi qayta ishga tushirildi.", TASK_NOMI)
        if ogohlantirish_kerak:
            telegram_xabar_yubor(
                "⚠️ Jarvis \"tirik-lekin-o'lik\" holatda topildi (watchdog) "
                "va qayta ishga tushirildi.\n"
                f"Sabab: {sabab}\n"
                f"Vaqt: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                "(Muammo davom etsa, keyingi ogohlantirish 1 soatdan keyin.)"
            )
            log.info("Ogohlantirish yuborildi.")
            holat_yoz({"oxirgi_ogohlantirish": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "muammoda": True})
        else:
            log.info("Ogohlantirish O'TKAZIB YUBORILDI (rate-limit: 1/soat, oxirgisi %s edi).", oxirgi)
            holat_yoz({"oxirgi_ogohlantirish": oxirgi, "muammoda": True})
    except Exception as e:
        log.error("'%s' vazifasini qayta ishga tushirishda xato: %s", TASK_NOMI, e)
        if ogohlantirish_kerak:
            telegram_xabar_yubor(
                f"❌ Jarvis watchdog: qayta ishga tushirishga urindi, lekin XATO: {e}"
            )
            holat_yoz({"oxirgi_ogohlantirish": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "muammoda": True})
        else:
            holat_yoz({"oxirgi_ogohlantirish": oxirgi, "muammoda": True})


if __name__ == "__main__":
    main()
