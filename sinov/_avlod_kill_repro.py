"""Jarvis_core'dagi _avlodlarni_yozib_ol / _tirik_avlodlarni_toxtat
funksiyalarini, HAQIQIY claude.exe/bash zanjirisiz, mustaqil tekshiradi.
Nested bash.exe -> bash.exe -> python.exe zanjiri qo'lda yaratiladi va
o'sha funksiyalar bilan o'chirilishi tekshiriladi.
"""
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from jarvis_core import _avlodlarni_yozib_ol, _tirik_avlodlarni_toxtat  # noqa: E402

# bash orqali ichma-ich bash chaqirib, oxirida uzoq python jarayon ishga
# tushiramiz — xuddi Bash tool ichida ishlaganidek.
bash = r"C:\Program Files\Git\bin\bash.exe"
py = sys.executable
cmd = f'"{bash}" -c \'"{bash}" -c "\\"{py}\\" -c \\"import time;time.sleep(120)\\""\''
print("ishga tushirilyapti:", cmd)
proc = subprocess.Popen(cmd, shell=True)
print("top-level PID:", proc.pid)

time.sleep(3)
avlodlar = _avlodlarni_yozib_ol(proc.pid)
print("avlodlar:", avlodlar)

toxtatilgan = _tirik_avlodlarni_toxtat(avlodlar)
print("to'xtatilgan:", toxtatilgan)

time.sleep(1)
avlodlar2 = _avlodlarni_yozib_ol(proc.pid)
print("kill'dan keyin hali qolgan avlodlar:", avlodlar2)

try:
    proc.wait(timeout=2)
except Exception:
    proc.kill()
