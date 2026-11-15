"""
HAQIQIY watchdog sinovi — STUB EMAS.

Avvalgi sinov (sinov/watchdog_sinov.py) real restart funksiyasini soxta
stub bilan almashtirgan edi va bu haqda "muvaffaqiyatli" degan taassurot
qoldiruvchi xabar yuborilgan — bu xato edi.

Bu skript watchdog.py modulini HECH QANDAY monkeypatch qilmasdan ishlatadi:
- DIAG_LOG = asl diagnostika.log (sinov nusxasi emas)
- jarvisni_qayta_ishga_tushir() = asl funksiya (haqiqiy schtasks/kill)
- owner_ga_xabar() = asl funksiya (haqiqiy Telegram Bot API so'rovi)

Faqat ikkita narsa qilinadi, sinovni HOZIR ishlatish uchun:
1) watchdog_holat.json o'chiriladi — aks holda oldingi (stub) urinishdan
   qolgan 5 daqiqalik "sovish davri" haqiqiy restartga to'sqinlik qiladi.
2) diagnostika.log oxiriga ataylab ESKIRGAN "tirikman" yozuvi qo'shiladi
   (90s chegaradan oshib ketadigan qilib) — real bot band/qotib qolmagan,
   shunchaki sinov uchun "qotib qolgandek" ko'rsatilyapti.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import watchdog as w  # ASL, o'zgartirilmagan modul — hech narsa monkeypatch qilinmagan

print(f"[{datetime.now():%H:%M:%S}] Haqiqiy sinov boshlandi. DIAG_LOG={w.DIAG_LOG}")

# 1) cooldown'ni tozalaymiz
if w.STATE_FILE.exists():
    w.STATE_FILE.unlink()
    print("watchdog_holat.json o'chirildi (cooldown tozalandi).")

# 2) haqiqiy diagnostika.log oxiriga eskirgan yozuv qo'shamiz
eski = (datetime.now() - timedelta(minutes=3)).strftime("%H:%M:%S.%f")[:-3]
with open(w.DIAG_LOG, "a", encoding="utf-8") as f:
    f.write(f"[{eski}] tirikman\n")
print(f"diagnostika.log oxiriga eskirgan yozuv qo'shildi: [{eski}] tirikman")

# 3) zudlik bilan HAQIQIY (stubsiz) tekshiruvni bir marta ishga tushiramiz
holat = w.bir_marta_tekshir({})
print("YAKUNIY HOLAT:", holat)
print(f"[{datetime.now():%H:%M:%S}] Haqiqiy sinov tugadi.")
