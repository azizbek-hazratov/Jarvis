# -*- coding: utf-8 -*-
"""
Instagram/AI Javob Bridge WATCHDOG.

Maqsad: `instagram-server` (4020) va `ai_javob_bridge.py` (4031) portlarini
tekshiradi. Biror sabab bilan (noutbuk qopqog'i yopilib uyqu rejimiga o'tishi,
tizim charchashi, kutilmagan xato va h.k.) jarayon o'lib qolgan bo'lsa —
darhol tegishli Task Scheduler vazifasini qayta ishga tushiradi va
Azizbekka Telegram orqali xabar beradi.

Mustaqil modul — jarvis_core.py/jarvis_telegram.py/instagram-server/
ai_javob_bridge.py fayllariga HECH QANDAY tegilmaydi, faqat tashqaridan
kuzatadi.

Task Scheduler orqali har 3 daqiqada ishga tushiriladi ("Jarvis Instagram
Watchdog"). Har ishga tushish `instagram_watchdog.log`ga yoziladi.
"""

import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, r"C:\Users\Dell\jarvis")
import config

LOG_FAYL = r"C:\Users\Dell\jarvis\instagram_watchdog.log"

TEKSHIRISH = [
    {
        "nomi": "Instagram Webhook Server",
        "port": 4020,
        "task": "Instagram Webhook Server",
    },
    {
        "nomi": "Jarvis AI Javob Bridge",
        "port": 4031,
        "task": "Jarvis AI Javob Bridge",
    },
]


def log(matn):
    vaqt = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FAYL, "a", encoding="utf-8") as f:
        f.write(f"[{vaqt}] {matn}\n")


def port_ochiqmi(port, host="127.0.0.1", timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def telegram_xabar_yubor(matn):
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
        data = f"chat_id={config.OWNER_ID}&text={urllib.parse.quote(matn)}".encode()
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception as e:
        log(f"Telegram xabar yuborishda xato: {e}")


def vazifani_qayta_ishga_tushir(task_nomi):
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f'Start-ScheduledTask -TaskName "{task_nomi}"'],
            capture_output=True, timeout=20,
        )
        return True
    except Exception as e:
        log(f"'{task_nomi}' qayta ishga tushirishda xato: {e}")
        return False


def asosiy():
    muammo_topildi = False
    xabar_qatorlari = []

    for band in TEKSHIRISH:
        if port_ochiqmi(band["port"]):
            continue

        muammo_topildi = True
        log(f"{band['nomi']} (port {band['port']}) O'CHIQ — qayta ishga tushirilmoqda...")
        vazifani_qayta_ishga_tushir(band["task"])
        time.sleep(5)

        if port_ochiqmi(band["port"]):
            log(f"{band['nomi']} muvaffaqiyatli qayta yondi (port {band['port']}).")
            xabar_qatorlari.append(f"✅ {band['nomi']} o'chib qolgan edi — avtomatik qayta yoqildi.")
        else:
            log(f"{band['nomi']} qayta yoqishga urinishdan keyin ham JAVOB BERMAYAPTI!")
            xabar_qatorlari.append(f"❌ {band['nomi']} o'chib qoldi VA qayta yoqib bo'lmadi — qo'lda tekshirish kerak!")

    if muammo_topildi:
        telegram_xabar_yubor(
            "🔧 Jarvis Watchdog:\n" + "\n".join(xabar_qatorlari) +
            "\n\nSabab ko'pincha: noutbuk qopqog'i yopilib uyqu rejimiga o'tishi."
        )
    else:
        log("Hammasi sog'lom (4020 va 4031 ikkalasi ham javob berdi).")


if __name__ == "__main__":
    asosiy()
