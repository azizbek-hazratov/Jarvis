"""
"jamoa" buyrug'i -- Telegram'da Azizbek "jamoa" deb yozganda, jarvis_telegram.py
shu modulni chaqiradi (AI/Claude ISHLATMASDAN, to'g'ridan-to'g'ri) va bitta
konsolidatsiyalangan xabar qaytaradi -- har bir "AI xodim"ning real holati
(heartbeat/log fayllariga qarab) va bugun nima qilgani.

Nega AI ishlatilmaydi: bu status-tekshiruv, tez va ishonchli bo'lishi kerak --
Claude chaqiruvi kutish vaqtini va xato ehtimolini oshiradi, hech qanday
"talqin" kerak emas (faqat fayl o'qish/vaqt solishtirish).

Xodimlar: Samandar (AI Expert), Malika (JetCafe), Sardor (kuzatuv+backup),
Bekzod (watchdog+HUD), Nozima (buxgalter). (2026-09-28: Malika/Bekzod avval
Dasturxon/Doktor deb atalgan -- Azizbek ismlarni almashtirdi.)

2026-09-27 (Jarvis OS 5-bosqich): asosiy ma'lumot-yig'ish mantiq
`jarvis_jamoa_data.py`ga ko'chirildi -- bu BITTA umumiy modul, uni HUD'dagi
"Jamoa" paneli (`jarvis_hud_bridge.py`ning `GET /jamoa`i) ham ishlatadi. Shu
fayl endi FAQAT o'sha umumiy funksiyalarni chaqirib, Telegram uchun bir xil
qisqa matn formatiga tizadi -- tashqi xatti-harakat (matn ko'rinishi)
o'ZGARMAGAN.
"""

import sys
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import jarvis_jamoa_data as _data

TASHKENT_OFFSET = timedelta(hours=5)


def _hozir():
    return datetime.utcnow() + TASHKENT_OFFSET


def jamoa_hisobot_matni() -> str:
    bugun = _hozir().strftime("%Y-%m-%d")
    satrlar = [
        f"👥 *Jamoa holati* ({_hozir().strftime('%Y-%m-%d %H:%M')}, Toshkent)",
        "",
        _data.samandar_telegram_matn(bugun),
        _data.malika_telegram_matn(bugun),
        _data.sardor_telegram_matn(bugun),
        _data.bekzod_telegram_matn(bugun),
        _data.nozima_telegram_matn(bugun),
    ]
    return "\n".join(satrlar)


if __name__ == "__main__":
    print(jamoa_hisobot_matni())
