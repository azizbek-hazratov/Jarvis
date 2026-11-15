"""
JARVIS — fon rejimi uchun ishga tushirgich

Bu fayl to'g'ridan-to'g'ri ishlatilmaydi — uni Windows Task Scheduler
`pythonw.exe` orqali chaqiradi (oynasiz).

pythonw'da ekran bo'lmagani uchun barcha xabarlar bot.log fayliga yoziladi.
Nimadir ishlamasa, birinchi navbatda shu faylni oching.
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "bot.log"

# pythonw.exe da stdout/stderr yo'q — faylga yo'naltiramiz
_log = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
sys.stdout = _log
sys.stderr = _log

os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

print(f"\n{'=' * 50}")
print(f"Ishga tushdi: {datetime.now():%Y-%m-%d %H:%M:%S}")

try:
    import jarvis_telegram

    jarvis_telegram.main()
except Exception:
    print("XATO:")
    traceback.print_exc()
finally:
    print(f"To'xtadi: {datetime.now():%Y-%m-%d %H:%M:%S}")
