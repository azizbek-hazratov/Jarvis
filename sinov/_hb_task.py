"""Ko'prik sinovi uchun yordamchi skript: N marta 60 soniya kutib, har safar
belgi chiqaradi. Ikkinchi argument (bo'lsa) faqat process command-line'da
ko'rinishi uchun ("marker") — sinov skripti tashqaridan shu jarayonni
topish/tirikligini tekshirish uchun ishlatadi, skriptning o'zi uni
ishlatmaydi.
"""
import sys
import time

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
for i in range(n):
    time.sleep(60)
    print(f"SINOV_TICK {i}", flush=True)
print("SINOV_DONE", flush=True)
