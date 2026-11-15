# -*- coding: utf-8 -*-
import sys
import requests
import config

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TOKEN = config.TELEGRAM_TOKEN
CHAT_ID = config.OWNER_ID
API = f"https://api.telegram.org/bot{TOKEN}"
HUD = "C:/Users/Dell/jarvis/jarvis_hud/"

MATN = """✅ <b>5 ta kosmetik tuzatish bajarildi</b> (faqat jamoa.html ichida, boshqa hech narsaga tegilmadi)

1) Feed'dagi test yozuvlari (bildirishnomalar.jsonl'dan) o'chirildi + endi "- [ ]" belgisi avtomatik olib tashlanadi, **qalin** haqiqiy qalin bo'lib chiqadi, bo'sh yozuv umuman ko'rinmaydi.
2) "Jarvis" yozuvi endi orb tagida, boshqa ismlar bilan bir qatorda — overlap yo'q.
3) "✅ Topshiriq qilish" endi kichik, o'ngga tekislangan, cyan tugma (boshqalarga mos).
4) 6 ta xodim endi tekis 3x2 panjarada, Jarvis alohida yuqori qatorda — yolg'iz karta yo'q.
5) Majlis natijasida endi "▸ Muhokamani ko'rish" bo'limi bor — bosilsa har bir xodimning portret+ism bilan aytgan gaplari (1-tur, 2-tur) ko'rinadi. "manba: saqlangan (offline)" endi kichik, xira kulrang.

Playwright bilan qayta tekshirdim — brauzer konsolida xato yo'q, hammasi ishlayapti. Bridge'ga tegilmadi (frontend fayl, restart shart emas edi)."""


def send_photo(path, caption):
    with open(path, "rb") as f:
        r = requests.post(
            f"{API}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": (path.split("/")[-1], f, "image/png")},
            timeout=60,
        )
    print(path, "->", r.status_code, r.text[:150])


def send_text(text):
    r = requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=30)
    print("text ->", r.status_code, r.text[:200])


if __name__ == "__main__":
    send_text(MATN)
    send_photo(HUD + "_sinov_1920_asosiy.png", "1/3 — Asosiy panel (1920px): Jarvis alohida, 6 xodim 3x2 panjarada")
    send_photo(HUD + "_sinov_375_mobil.png", "2/3 — Mobil ko'rinish (375px)")
    send_photo(HUD + "_sinov_1920_muhokama.png", "3/3 — 'Oxirgi majlis' bosilgandan keyin, Muhokama ochilgan holda")
