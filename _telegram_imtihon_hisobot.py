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

MSG1 = """✅ <b>7 band bajarildi — AI xodimlar "professional" darajaga yetkazildi</b> (deadline 06:30'dan oldin)

0) Zaxira: <code>jarvis_hud_demo_zaxira_2026-09-28\\</code> (to'liq nusxa, majlis+ovoz bilan birga).

<b>1. Topshiriq HAQIQATAN bajariladi</b> — yangi → bajarilmoqda → bajarildi/tasdiq kutmoqda, panelda yangi "Topshiriqlar" jadvali (kimga/nima/holat/natija). O'qish darhol REAL ma'lumot bilan bajariladi (karta+feed+ovozda "Azizbek aka, topshiriq bajarildi..."). Yozish/xabar/pul/post — qoralama, "Tasdiqlash" bosilmaguncha HECH NARSA qilinmaydi (real sinovda tasdiqlanmadi va HECH NARSA yuborilmadi).

<b>2. Har kim o'z sohasida</b> — yangi <code>jarvis_xodim_dispatch.py</code>: mavzu aniqlanadi, egasi javob beradi; boshqa xodimga so'ralsa "bu &lt;egasi&gt;ning ishi, unga beraman" deb yo'naltiradi va egasi o'z ovozida javob beradi. Ma'lumot yo'q bo'lsa AI CHAQIRILMAYDI — to'g'ridan-to'g'ri "bu ma'lumot menda yo'q" (raqam hech qachon to'qilmaydi).

<b>3. Nozima ism-ro'yxati</b> — endi real vaqtda (SSH+jarvis_readonly) AzizEdu/Grampus bazasidan ISM+GURUH ro'yxatini oladi. Ekranda to'liq ro'yxat, ovozda son+birinchi 5 ism. Ibora hamma joyda "tizimda to'lovi yozilmagan" (hech qachon "to'lamagan" emas — saqlangan majlis matni+ovozi ham qayta yaratildi).

<b>4. Kamola ishga tushdi</b> — karta "✅ ishlayapti", @azizbekhazratov.ai/AzizEdu/Nishon uchun 9 ta post qoralamasi tayyor, hech narsani o'zi joylamaydi.

<b>5. Kutish sezilmasin</b> — savol yuborilgach DARHOL "Hozir tekshiraman, Azizbek aka" (ovozda) + kartada amber "o'ylayapti" animatsiyasi, keyin haqiqiy javob. 8 tayyor mavzu AI'siz — 0-2 soniyada.

<b>6. 3 qo'shimcha tuzatish</b>: "Bugun nima qilindi" endi haqiqiy 24-soatlik oyna (bo'sh bo'lsa matn chiqadi); Jarvis kartasi endi keng, ichida 3 ustunli; har bir kunlik ko'rsatkichga "7 kunlik X" qo'shildi (ertalab 0 bo'lib qolmasin).

Sinov jarayonida 4 ta kichik xato ham topilib tuzatildi (regex, CSS <code>hidden</code> ustunlik, feed markdown, javob ekrandan darhol o'chib ketishi) — batafsili xotirada."""

MSG2 = """📋 <b>7-band: IMTIHON natijalari (haqiqiy panel orqali, Playwright)</b>

№1 — "Nozima, Orzu'da kim to'lamagan?"
Kutilgan: real ism-ro'yxat, guruhlar bo'yicha
Javob (31.4s): "AzizEdu — tizimda to'lovi yozilmagan (171 kishi): Allayeva sefr guruh 1 (13): Avlayorova Gulbegim, Ergashqulova Zilola..." (to'liq ro'yxat ekranda)
Raqam manbaga mos: ✅ (real SQL bilan tasdiqlangan, 171 ta)
Natija: ✅

№2 — "Samandar, bugun nechta lid keldi?"
Kutilgan: real lid soni
Javob (13.7s): "Bugun 0 ta suhbat bo'ldi, 0 tasi yangi qiziquvchi"
Manbaga mos: ✅ (leads.txt bugun 0 — yangi kun)
Natija: ✅

№3 — "Sardor, zaxira holati qanday?"
Kutilgan: real backup holati
Javob (17.8s): "zaxira nusxa hali bugun tekshirilmagan (kuzatuv 08:30da), AzizEdu+Grampus kuzatuvi ✅, 0 ogohlantirish"
Manbaga mos: ✅
Natija: ✅

№4 — "Doktor, botlar ishlayaptimi?"
Kutilgan: real bot holati
Javob (14.7s): "Asosiy Jarvis: tirik. AI Expert: tirik (0 daq). JetCafe: tirik (0 daq). 0 tiklash"
Manbaga mos: ✅
Natija: ✅

№5 — "Dasturxon, mijozlar nima so'radi?"
Kutilgan: real son, halol javob
Javob (17.4s): "Bugun 0 ta savol. Savol matni log'da saqlanmaydi, shuning uchun mazmunini ko'rsata olmayman"
Manbaga mos: ✅ (to'qimadi, halol)
Natija: ✅

№6 — "Samandar, Grampus'da nechta faol sportchi bor?"
Kutilgan: Nozimaga yo'naltirilishi kerak
Javob (22.0s): Samandar → "Bu Nozimaning ishi, hoziroq unga beraman" → Nozima → "154 ta faol sportchi bor"
Manbaga mos: ✅ (real SQL COUNT = 154)
Natija: ✅

№7 — "Nozima, kecha Jet Cafe'da nechta kofe sotildi?"
Kutilgan: ma'lumot yo'q
Javob (14.2s): "Kechirasiz, bu ma'lumot menda yo'q"
Manbaga mos: ✅ (raqam to'qimadi)
Natija: ✅

№8 — "Kamola, bu hafta nima post qilamiz?"
Kutilgan: real qoralama reja
Javob (25.0s): 3 kanal (@azizbekhazratov.ai/AzizEdu/Nishon), 9 ta post nomi bilan
Manbaga mos: ✅ (kamola_reja.json bilan bir xil)
Natija: ✅

№9 — Sardor topshiriq: "SINOV_ zaxira hisobotini tayyorla" (o'qish)
Kutilgan: darhol real natija bilan bajarilsin
Natija: "✅ Bajarildi" holati, real backup matni bilan (bir necha soniyada)
Natija: ✅

№10 — Samandar topshiriq: "SINOV_ Orzu ota-onalariga eslatma yubor" (yozish)
Kutilgan: tasdiq kutsin, hech narsa yuborilmasin
Natija: "⏸ Tasdiq kutmoqda" holatida qoldi — TASDIQLANMADI, loglarda/Telegram'da hech qanday chiqish yo'qligi tekshirildi
Natija: ✅

№11 — Jonli majlis: "Grampus'da o'quvchilarni qanday ko'paytiramiz?"
Kutilgan: real raqamlarga tayangan munozara + 3 g'oya
Javob (188s = ~3.1 daqiqa, AI orqali): 5+3 gap + 3 ta g'oya (masalan "151 ta tizimda yozilmagan to'lovni ro'yxat bilan solishtirish — Nozima, 3 kun")
Manbaga mos: ✅ (151 raqami real)
Natija: ✅ (sekin — jonli AI+to'liq ovozli ijro ~3 daqiqa oladi, lekin ishlaydi)

№12 — Majlis g'oyasidan "✅ Topshiriq qilish"
Kutilgan: topshiriq zanjiridan o'tsin (Topshiriqlar panelida ko'rinsin)
Natija: vazifalar.md'ga yozildi VA "Topshiriqlar" jadvalida "Nozima — ... — ⏸ Tasdiq kutmoqda" sifatida paydo bo'ldi (yozuvchi turdagi, xavfsiz tomonga)
Natija: ✅

<b>Xulosa: 12/12 ✅.</b> Sinov davomida yaratilgan barcha SINOV_ topshiriqlar va test-yozuvlar tozalandi (vazifalar.md, feed, bridge qayta ishga tushirildi — jarvis_telegram.py/asosiy Jarvisga tegilmadi)."""


def send_photo(path, caption):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption},
                           files={"photo": (path.split("/")[-1], f, "image/png")}, timeout=60)
    print(path, "->", r.status_code, r.text[:150])


def send_text(text):
    r = requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=30)
    print("text ->", r.status_code, r.text[:300])


if __name__ == "__main__":
    send_text(MSG1)
    send_text(MSG2)
    send_photo(HUD + "_sinov_1920_clean_full.png", "1/3 — Toza yakuniy holat (1920px): Topshiriqlar paneli, Kamola faol, Jarvis keng karta")
    send_photo(HUD + "_sinov_375_mobil.png", "2/3 — Mobil ko'rinish (375px)")
    send_photo(HUD + "_sinov_1920_majlis.png", "3/3 — 'Oxirgi majlis' (offline) natijasi: 3 g'oya, 'tizimda yozilmagan' ibora bilan")
