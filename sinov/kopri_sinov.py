"""
Ko'prik sinovi (2026-09-26) — jarvis_core.Jarvis'ni Telegram'ga ULANMASDAN
to'g'ridan-to'g'ri chaqirib, 3 narsani tekshiradi:
(a) heartbeat callback HEARTBEAT_INTERVAL_S (150s) da chaqirilyaptimi
(b) jarvis.stop() interrupt() + kerak bo'lsa taskkill bilan tashqi
    jarayonni HAQIQATDA to'xtatyaptimi (10s ichida yo'qolmasa)
(c) fon-ishlar.json ga yozuv tushib, ish tugagach o'chyaptimi

MUHIM: bu skript Telegram bot tokenini ISHLATMAYDI (Jarvis klassini
to'g'ridan-to'g'ri chaqiradi) — shuning uchun asosiy jarvis_telegram.py
jarayoni bilan "Conflict" bo'lmaydi, ikkalasi bir vaqtda ishlashi mumkin.

Natija: sinov/kopri_sinov_natija.json (UTF-8).
"""
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from jarvis_core import Jarvis, HEARTBEAT_INTERVAL_S  # noqa: E402
import jarvis_fon_ishlar as fon_ishlar  # noqa: E402

NATIJA_FAYL = Path(__file__).resolve().parent / "kopri_sinov_natija.json"
HB_SKRIPT = Path(__file__).resolve().parent / "_hb_task.py"

natija = {"boshlandi": datetime.now().isoformat(), "testlar": {}}


def log(msg):
    vaqt = datetime.now().strftime("%H:%M:%S")
    print(f"[{vaqt}] {msg}", flush=True)


def process_bormi(marker: str) -> bool:
    """WMIC orqali command-line'ida `marker` bo'lgan jarayon bormi tekshiradi
    (tasklist standart holda to'liq buyruq qatorini ko'rsatmaydi)."""
    try:
        r = subprocess.run(
            ["wmic", "process", "where", f"CommandLine like '%{marker}%'", "get", "ProcessId"],
            capture_output=True, text=True, timeout=15,
        )
        satrlar = [
            s.strip() for s in r.stdout.splitlines()
            if s.strip() and s.strip() != "ProcessId"
        ]
        return len(satrlar) > 0
    except Exception as e:
        log(f"process_bormi xato: {e}")
        return False


async def test_fon_ishlar(jarvis: Jarvis):
    log("TEST C boshlandi: fon-ishlar.json")
    natija["testlar"]["fon_ishlar_oldin"] = fon_ishlar.royxatni_oqi()

    async def kuzat():
        await asyncio.sleep(3)
        natija["testlar"]["fon_ishlar_ishlash_paytida"] = fon_ishlar.royxatni_oqi()

    kuzatuvchi = asyncio.create_task(kuzat())
    javob = await jarvis.ask(
        "Bash orqali `python -c \"import time; time.sleep(8)\"` ishga tushir "
        "va kut. Tugagach faqat 'tayyor' deb yoz."
    )
    await kuzatuvchi
    natija["testlar"]["fon_ishlar_keyin"] = fon_ishlar.royxatni_oqi()

    ishlash_paytida = natija["testlar"].get("fon_ishlar_ishlash_paytida", [])
    natija["testlar"]["fon_ishlar_muvaffaqiyatli"] = (
        len(ishlash_paytida) >= 1 and len(natija["testlar"]["fon_ishlar_keyin"]) == 0
    )
    log(
        f"TEST C tugadi: ishlash paytida={len(ishlash_paytida)} ta yozuv, "
        f"keyin={len(natija['testlar']['fon_ishlar_keyin'])} ta, javob={javob[:80]!r}"
    )


async def test_stop(jarvis: Jarvis):
    log("TEST B boshlandi: /stop ekvivalenti (interrupt + kerak bo'lsa taskkill)")
    marker = "SINOV_STOP_MARKER"
    prompt = (
        f"Bash orqali ushbu buyruqni bitta chaqiruvda, timeout=600000 bilan "
        f"ishga tushir: `python {HB_SKRIPT} 20 {marker}`. Buyruq tugashini kut."
    )
    run_task = asyncio.create_task(jarvis.ask(prompt))
    await asyncio.sleep(15)
    jarayon_ishga_tushdimi = process_bormi(marker)
    log(f"  15s dan keyin marker-jarayon ishlayaptimi: {jarayon_ishga_tushdimi}")

    stop_boshlandi = time.monotonic()
    stop_natija = await jarvis.stop()
    stop_davomiyligi = time.monotonic() - stop_boshlandi

    try:
        await asyncio.wait_for(run_task, timeout=30)
    except Exception:
        pass

    await asyncio.sleep(12)
    jarayon_qoldimi = process_bormi(marker)

    natija["testlar"]["stop"] = {
        "jarayon_ishga_tushdimi_15s": jarayon_ishga_tushdimi,
        "stop_davomiyligi_s": round(stop_davomiyligi, 1),
        "stop_javobi": stop_natija,
        "jarayon_qoldimi_27s_dan_keyin": jarayon_qoldimi,
        "MUVAFFAQIYATLI": jarayon_ishga_tushdimi and not jarayon_qoldimi,
    }
    log(f"TEST B tugadi: jarayon_qoldimi={jarayon_qoldimi}, stop_javobi={stop_natija[:150]!r}")


async def test_heartbeat(jarvis: Jarvis):
    log("TEST A boshlandi: heartbeat (6 daqiqalik vazifa)")
    hb_vaqtlari = []

    def on_hb(qadam):
        hb_vaqtlari.append(time.monotonic())
        log(f"  heartbeat keldi, oxirgi qadam: {qadam}")

    boshlandi = time.monotonic()
    prompt = (
        f"Bash orqali ushbu buyruqni bitta chaqiruvda, timeout=420000 bilan "
        f"ishga tushir va tugashini kut, orada boshqa hech narsa qilma: "
        f"`python {HB_SKRIPT} 6`. Tugagach faqat 'tayyor' deb yoz."
    )
    javob = await jarvis.ask(prompt, on_heartbeat=on_hb)
    davomiyligi = time.monotonic() - boshlandi
    oraliqlar = [round(b - a, 1) for a, b in zip(hb_vaqtlari, hb_vaqtlari[1:])]
    natija["testlar"]["heartbeat"] = {
        "davomiyligi_s": round(davomiyligi, 1),
        "heartbeat_soni": len(hb_vaqtlari),
        "oraliqlar_s": oraliqlar,
        "kutilgan_oraliq_s": HEARTBEAT_INTERVAL_S,
        "javob_oxiri": javob[-300:],
        "MUVAFFAQIYATLI": len(hb_vaqtlari) >= 2 and all(abs(o - HEARTBEAT_INTERVAL_S) < 20 for o in oraliqlar),
    }
    log(f"TEST A tugadi: {len(hb_vaqtlari)} heartbeat, oraliqlar={oraliqlar}")


async def main():
    async with Jarvis(log=False) as jarvis:
        await test_fon_ishlar(jarvis)
        await test_stop(jarvis)
        await test_heartbeat(jarvis)
    natija["tugadi"] = datetime.now().isoformat()
    NATIJA_FAYL.write_text(
        json.dumps(natija, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"Barcha testlar tugadi. Natija: {NATIJA_FAYL}")


if __name__ == "__main__":
    asyncio.run(main())
