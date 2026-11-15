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
DEMO = "C:/Users/Dell/jarvis/kiruvchi/demo/"

MATN = """✅ <b>Jarvis OS — Majlis + portretli panel TAYYOR</b> (deadline 07:30'dan ancha oldin, soat 23:15'da tugadi)

<b>Nima qilindi:</b>
1) 6 ta xodim portreti (real rasm) — kartochkalarda va yuqoridagi "Majlis zali"da (video-qo'ng'iroq ko'rinishi). Jarvis — yorug' shar.
2) Gapirayotgan xodim zalda kattalashadi, halqasi yonadi, to'lqin animatsiyasi chiqadi, pastda subtitr yoziladi.
3) "Ismga murojaat" — pastda bitta maydon: "Nozima, Orzu'da kim to'lamagan?" kabi yozasiz, ism bo'yicha to'g'ri xodimga yo'naltiriladi. 4 ta tayyor mavzu (qarzdorlar/zaxira nusxa/lidlar/bot holati) AI'siz darhol javob beradi, qolgani AI orqali o'sha xodim rolida (faqat o'qish). Javob ovozda + ekranda chiqadi.
4) "Majlis" — mavzu yozib "🗣️ Majlis boshlash" bossangiz, 5 xodim real raqamlarga tayanib fikr bildiradi, bir-biriga javob beradi, oxirida men 3 ta aniq g'oya beraman (mas'ul+muddat bilan), har birida "✅ Topshiriq qilish" tugmasi — bosilsa vazifalar.md'ga yoziladi.
5) MAJBURIY demo: "Orzu Akademy'da 199'dan 171 tasi to'lamagan" mavzusidagi majlis matni+ovozi diskka saqlangan — "▶️ Oxirgi majlis" tugmasi buni INTERNETSIZ ham ijro etadi.

<b>Qanday sinaldi:</b> to'liq oqim (ochilish → standup → ismga murojaat → oxirgi majlis → topshiriq tugmasi) Playwright bilan 2 MARTA avtomatik sinaldi, ikkalasida ham brauzer konsolida xato chiqmadi. Qo'shimcha: to'liq 6-xodimli "Ertalabki yig'ilish" alohida qayta sinaldi (mavjud kodga tegilgani uchun) — xatosiz. Jonli AI-Majlis boshqa mavzu bilan ("Narxlarni 20% oshirish kerakmi?") alohida sinaldi — 39 soniyada real raqamlarga tayangan to'g'ri natija berdi.

<b>Nima ISHLAMAYDI / cheklovlar (yashirmayman):</b>
• Ilova qildim video'da OVOZ YO'Q — Playwright ekran-yozgichi brauzer tovushini yozmaydi, faqat vizual+subtitr. Haqiqiy ovozni eshitish uchun panelning o'zini brauzerda ochish kerak.
• "Tayyor mavzular"da (qarzdorlar/zaxira/lid/bot holati) javob MAVZU bo'yicha aniqlanadi — qaysi xodimga murojaat qilsangiz ham bir xil manbadan javob beradi (masalan boshqa xodimdan "zaxira nusxa?" desangiz ham Sardorning ma'lumoti chiqadi, ovozi so'ragan xodimniki bo'ladi).
• "Kim to'lamagan" javobida faqat SON bor (171 kishi), ism-ro'yxat yo'q — chunki Nozimaning saqlangan hisobotida ham faqat son bor.
• Erkin savol/jonli Majlis AI orqali ~15-40 soniya davom etadi (darhol emas, lekin ekranda "tayyorlanmoqda" holati bor).

jarvis_telegram.py'ga tegilmadi, asosiy Jarvis jarayoni restart qilinmadi — faqat alohida HUD bridge (8090-port) 3 marta qayta ishga tushirildi (test izlarini tozalash uchun, sizga hech qanday ta'sir qilmaydi).

Panel: http://localhost:8080/jamoa.html"""


def send_photo(path, caption=""):
    with open(path, "rb") as f:
        r = requests.post(
            f"{API}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": (path.split("/")[-1], f, "image/png")},
            timeout=60,
        )
    print(path, "->", r.status_code, r.text[:200])


def send_video(path, caption=""):
    with open(path, "rb") as f:
        r = requests.post(
            f"{API}/sendVideo",
            data={"chat_id": CHAT_ID, "caption": caption, "supports_streaming": True},
            files={"video": (path.split("/")[-1], f, "video/mp4")},
            timeout=180,
        )
    print(path, "->", r.status_code, r.text[:200])


def send_text(text):
    r = requests.post(
        f"{API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=30,
    )
    print("text ->", r.status_code, r.text[:300])


if __name__ == "__main__":
    send_text(MATN)
    send_photo(HUD + "_sinov_1920_asosiy.png", "1/3 — Asosiy panel (1920px): portretli zal + kartochkalar")
    send_photo(HUD + "_sinov_1920_majlis.png", "2/3 — Oxirgi majlis ijro etilgandan keyin: 3 ta g'oya + Topshiriq tugmalari")
    send_photo(HUD + "_sinov_375_mobil.png", "3/3 — Mobil ko'rinish (375px)")
    send_video(DEMO + "ai_xodimlar_demo.mp4", "Demo video (ovozsiz, faqat vizual) — panel, standup, ismga murojaat, oxirgi majlis")
