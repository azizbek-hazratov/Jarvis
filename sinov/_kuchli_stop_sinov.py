"""Kuchaytirilgan /stop sinovi (2026-09-26).

jarvis_core.py'GA TEGILMAGAN — faqat sinov infratuzilmasi yaxshilandi:
  1) process_bormi() PowerShell o'rniga psutil.process_iter() bilan
     qayta yozildi (o'z-o'ziga mos kelish bug'i yo'q, chunki tashqi
     PowerShell jarayon ishga tushirilmaydi — hammasi shu Python
     jarayonining ichida). Test skriptining o'z PID'i har ehtimolga
     qarshi ro'yxatdan chiqarib tashlanadi.
  2) Marker vazifasi 300 soniyalik (5 daqiqa, _hb_task.py 5 ...) — o'z-
     o'zidan tugab qolmasligi kafolatlanadi.
  3) Ikki stsenariy: (A) marker Bash ichida to'g'ridan-to'g'ri, (B)
     marker Bash'dan AJRATILGAN holda (PowerShell Start-Process bilan,
     detached) ishga tushiriladi — bu production'dagi "ssh orphan"
     holatini taqlid qiladi.
"""
import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from jarvis_core import Jarvis, auto_approve, DIAG_LOG  # noqa: E402

HB_SKRIPT = Path(__file__).resolve().parent / "_hb_task.py"
OWN_PID = os.getpid()


def log(msg):
    vaqt = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{vaqt}] {msg}", flush=True)


def process_bormi(marker: str):
    """psutil.process_iter() bilan — tashqi PowerShell jarayon ishga
    tushirilmaydi, shuning uchun o'z-o'ziga mos kelish MUMKIN EMAS.
    O'z PID (OWN_PID) har ehtimolga qarshi ro'yxatdan chiqariladi."""
    topilganlar = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        if p.info["pid"] == OWN_PID:
            continue
        cmdline = p.info["cmdline"] or []
        agar = any(marker in (qism or "") for qism in cmdline)
        if agar:
            topilganlar.append({"pid": p.info["pid"], "cmdline": " ".join(cmdline)})
    return (len(topilganlar) > 0), topilganlar


def soxta_marker_isboti():
    marker = "ABSOLUTELY_FAKE_MARKER_XYZ_NOBODY_RUNS_THIS_2026"
    bormi, ro_yxat = process_bormi(marker)
    log(f"SOXTA MARKER ISBOTI: bormi={bormi}, topilganlar={ro_yxat} (kutilgan: False, [])")
    assert bormi is False and ro_yxat == [], "process_bormi() soxta marker bilan False qaytarishi SHART edi!"
    log("SOXTA MARKER ISBOTI: OK — psutil-asosli process_bormi() o'z-o'ziga mos kelmaydi.")


def diag_log_oraligi(marker: str, boshlanish_offset: int):
    """diagnostika.log faylining boshlanish_offset dan keyingi qismida
    marker haqida yozilgan qatorlarni qaytaradi."""
    try:
        matn = DIAG_LOG.read_text(encoding="utf-8")
    except Exception:
        return []
    qatorlar = matn.splitlines()[boshlanish_offset:]
    return qatorlar


def diag_log_uzunligi():
    try:
        return len(DIAG_LOG.read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0


async def stsenariy_ishga_tushir(jarvis: Jarvis, nomi: str, marker: str, launch_prompt: str):
    natija = {"stsenariy": nomi, "marker": marker}
    log(f"=== STSENARIY {nomi} boshlandi (marker={marker}) ===")

    diag_offset = diag_log_uzunligi()

    run_task = asyncio.create_task(jarvis.ask(launch_prompt))
    await asyncio.sleep(15)
    bormi_15s, royxat_15s = process_bormi(marker)
    log(f"  15s dan keyin marker jarayon bormi: {bormi_15s} ({royxat_15s})")
    natija["jarayon_ishga_tushdimi_15s"] = bormi_15s
    natija["jarayon_royxati_15s"] = royxat_15s

    stop_boshlandi_vaqt = datetime.now().isoformat()
    stop_boshlandi_mono = time.monotonic()
    stop_javobi = await jarvis.stop()
    stop_davomiyligi = time.monotonic() - stop_boshlandi_mono
    natija["interrupt_boshlandi_vaqt"] = stop_boshlandi_vaqt
    natija["stop_davomiyligi_s"] = round(stop_davomiyligi, 1)
    natija["stop_javobi"] = stop_javobi
    log(f"  jarvis.stop() {round(stop_davomiyligi, 1)}s davom etdi. Javob: {stop_javobi[:150]!r}")

    try:
        await asyncio.wait_for(run_task, timeout=30)
    except Exception:
        pass

    # 15 soniya davomida har 1s'da tekshirib, marker ANIQ QAYSI soniyada
    # yo'qolganini aniqlaymiz (talab: 15s ichida yo'qolishi kerak).
    yoqolgan_soniya = None
    yoqolgan_vaqt = None
    for s in range(1, 21):  # 20s gacha kuzatamiz (talab 15s, ortiqcha 5s zахира)
        await asyncio.sleep(1)
        bormi, royxat = process_bormi(marker)
        if not bormi:
            yoqolgan_soniya = s
            yoqolgan_vaqt = datetime.now().isoformat()
            log(f"  marker jarayon {s}s da YO'QOLDI (interrupt()dan keyin).")
            break
    else:
        log("  marker jarayon 20s ichida YO'QOLMADI.")

    natija["yoqolgan_soniya_stopdan_keyin"] = yoqolgan_soniya
    natija["yoqolgan_vaqt"] = yoqolgan_vaqt
    natija["15s_ichida_yoqoldi"] = (yoqolgan_soniya is not None and yoqolgan_soniya <= 15)

    # diagnostika.log'dan shu stsenariy davridagi yozuvlarni olib, "kim
    # to'xtatgan"ni aniqlaymiz.
    yangi_qatorlar = diag_log_oraligi(marker, diag_offset)
    natija["diag_log_qatorlari"] = yangi_qatorlar

    bizning_kod_toxtatdi = any(
        "orphan avlod jarayon to'xtatildi" in q or "taskkill" in q.lower()
        for q in yangi_qatorlar
    )
    natija["kim_toxtatdi"] = "bizning_kod" if bizning_kod_toxtatdi else (
        "ozi_tugadi_yoki_asosiy_jarayon_bilan_birga" if natija["15s_ichida_yoqoldi"] else "hech_kim_(tirik_qoldi)"
    )

    log(f"  diag log yozuvlari ({len(yangi_qatorlar)} ta):")
    for q in yangi_qatorlar:
        log(f"    {q}")

    natija["MUVAFFAQIYATLI"] = bool(bormi_15s and natija["15s_ichida_yoqoldi"])

    log(f"=== STSENARIY {nomi} tugadi: MUVAFFAQIYATLI={natija['MUVAFFAQIYATLI']}, kim_toxtatdi={natija['kim_toxtatdi']} ===")
    return natija


async def main():
    umumiy_boshlandi = time.monotonic()
    natijalar = {}

    soxta_marker_isboti()

    async with Jarvis(log=False, confirm_fn=auto_approve) as jarvis:
        # --- STSENARIY A: oddiy holat, marker Bash ICHIDA ishlaydi ---
        marker_a = "SINOV_STOP_A_ODDIY"
        prompt_a = (
            f"Bash orqali ushbu buyruqni bitta chaqiruvda, timeout=600000 bilan "
            f"ishga tushir: `python {HB_SKRIPT} 5 {marker_a}`. Buyruq tugashini kut."
        )
        natijalar["A"] = await stsenariy_ishga_tushir(jarvis, "A_oddiy_bash_ichida", marker_a, prompt_a)

    async with Jarvis(log=False, confirm_fn=auto_approve) as jarvis:
        # --- STSENARIY B: qiyin holat, marker Bash'dan AJRATILGAN (detached) ---
        marker_b = "SINOV_STOP_B_AJRATILGAN"
        prompt_b = (
            f"Bash orqali ushbu buyruqni ishga tushir: "
            f"`powershell.exe -NoProfile -Command \"Start-Process -FilePath python "
            f"-ArgumentList '{HB_SKRIPT}','5','{marker_b}' -WindowStyle Hidden\"`. "
            f"Bu buyruq darhol tugaydi (ichkarida mustaqil/ajratilgan jarayon qoladi, "
            f"uni kutish shart emas). Buyruq tugagach faqat 'ishga tushdi' deb yoz."
        )
        natijalar["B"] = await stsenariy_ishga_tushir(jarvis, "B_qiyin_ajratilgan", marker_b, prompt_b)

    umumiy_davomiyligi = time.monotonic() - umumiy_boshlandi
    log(f"UMUMIY DAVOMIYLIK: {round(umumiy_davomiyligi, 1)}s")

    import json
    natija_fayl = Path(__file__).resolve().parent / "_kuchli_stop_natija.json"
    natija_fayl.write_text(
        json.dumps({"umumiy_davomiyligi_s": round(umumiy_davomiyligi, 1), **natijalar},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"Natija: {natija_fayl}")


if __name__ == "__main__":
    asyncio.run(main())
