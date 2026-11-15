"""
Watchdog'ning aniqlash + xabar berish + log yozish qismini XAVFSIZ tekshirish.

Bu skript:
  - watchdog.py dagi haqiqiy DIAG_LOG o'rniga sinov papkasidagi soxta
    diagnostika_sinov.log ni ishlatadi (real botga tegmaydi).
  - jarvisni_qayta_ishga_tushir() funksiyasini soxta stub bilan almashtiradi
    (haqiqiy "Jarvis" Task Scheduler vazifasiga yoki jarayoniga TEGMAYDI).
  - Qolgan hammasi (owner_ga_xabar - haqiqiy Telegram xabari, log_watchdog -
    haqiqiy watchdog.log, holatni_yoz - haqiqiy watchdog_holat.json) asl
    kod bo'yicha ishlaydi.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import watchdog as w

# 1) diag log manzilini sinov fayliga almashtiramiz
w.DIAG_LOG = Path(__file__).parent / "diagnostika_sinov.log"


# 2) real restart funksiyasini soxta stub bilan almashtiramiz
def soxta_restart():
    w.log_watchdog("   [SINOV STUB] haqiqiy restart chaqirilmadi — "
                    "faqat funksiya to'g'ri chaqirilganini tekshirmoqda")
    return True, "SINOV: haqiqiy schtasks/kill ishlatilmadi, bu faqat stub natija"


w.jarvisni_qayta_ishga_tushir = soxta_restart

print(f"Sinov log fayli: {w.DIAG_LOG}")
print(f"Oxirgi 'tirikman' vaqti: {w.oxirgi_tirikman_vaqti()}")
print("Tekshiruv boshlanmoqda...\n")

holat = {}  # cooldown'ga to'sqinlik qilmasligi uchun toza holatdan boshlaymiz
holat = w.bir_marta_tekshir(holat)

print("\nYakuniy holat:", holat)
