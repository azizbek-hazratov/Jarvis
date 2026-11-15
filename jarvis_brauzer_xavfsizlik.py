"""
JARVIS BRAUZER XAVFSIZLIK QATLAMI (2026-09-21).

Bu fayl `jarvis_brauzer.py`dagi harakat-funksiyalari (`xavfsiz_bos`,
`xavfsiz_toldir`) ISHLATADIGAN sof-mantiq (side-effect'siz) qatlam —
ataylab ALOHIDA faylga chiqarilgan, shunda Azizbek "nima bloklanadi"ni
BITTA kichik faylni o'qib to'liq audit qila oladi, brauzer-avtomatlash
kodi bilan aralashmaydi.

Azizbek tasdiqlagan qoidalar (2026-09-21):
(a) CAPTCHA — hech qachon "hal qilishga urinilmaydi", DARHOL to'xtatiladi.
(b) "To'lov" bloki — checkout'dan tashqari HAR QANDAY pul o'tkazmasi/
    obuna/kripto ham qamraladi. QATTIQ BLOK — hech qanday bypass parametri
    yo'q (parol qoidasi bilan bir xil darajada qat'iy).
(c) "Hisob yaratishni yakunlash" (Ro'yxatdan o'tish/Yarat tugmasi) — forma
    to'ldirish erkin, lekin YAKUNIY tugmani bosishdan oldin HAR SAFAR aniq
    tasdiq kerak — shuning uchun bu funksiya `tasdiqlandi=True` parametri
    ANIQ berilmasa har doim rad etadi. `tasdiqlandi=True`ni FAQAT Jarvis
    (chaqiruvchi kod) Azizbekdan chatda REAL tasdiq olgandan keyin
    qo'lda beradi — bu qatlam o'zi hech kimdan so'ramaydi, faqat
    "so'ralmagan bo'lsa bloklaydi" tamoyilini kod darajasida kafolatlaydi.

Umumiy dizayn: GUI/brauzer harakatlari uchun ALLOWLIST mantiqi (nima xavfli
ekanini oldindan bilib bo'lmaydi — ekranda ertaga boshqa narsa chiqishi
mumkin), Bashning XAVFLI_BUYRUQLAR blocklist'idan FARQLI — bu ataylab, reja
bosqichida Azizbekka tushuntirilgan va tasdiqlangan.
"""

import re


class JarvisXavfsizlikXatosi(Exception):
    """Umumiy asos-xato — brauzer VA desktop (UI Automation) xavfsizlik
    qatlamlari ikkalasi ham shundan meros oladi, shu bilan Jarvis (yoki
    Azizbek) ikkalasini ham BITTA `except JarvisXavfsizlikXatosi` bilan
    ushlashi mumkin, kerak bo'lsa turini (`isinstance`) aniqlashtirib."""


class BrauzerXavfsizlikXatosi(JarvisXavfsizlikXatosi):
    """Xavfsizlik qatlami bir harakatni bloklasa shu xato ko'tariladi.
    Chaqiruvchi kod (Jarvis) buni ushlab, Azizbekka ANIQ sabab bilan
    xabar berishi kerak — jim yutib yubormasin."""


class DesktopXavfsizlikXatosi(JarvisXavfsizlikXatosi):
    """Desktop (Windows UI Automation / pywinauto, Bosqich 2) xavfsizlik
    qatlami bir harakatni bloklasa shu xato ko'tariladi — brauzer bilan bir
    xil qoidalar (CAPTCHA/to'lov/hisob-yaratish/parol), faqat manba oyna
    matni (HTML emas)."""


# ---------------------------------------------------------------- CAPTCHA ----

CAPTCHA_IFRAME_BELGILARI = [
    "recaptcha", "hcaptcha", "turnstile", "captcha", "arkoselabs", "funcaptcha",
]

CAPTCHA_MATN_BELGILARI = [
    "i'm not a robot", "i am not a robot", "verify you are human",
    "verify that you are human", "select all images", "select all squares",
    "roborsiz ekanligingizni tasdiqlang", "robot emasligingizni tasdiqlang",
    "captcha",
]


def captcha_holatini_tekshir(page) -> str | None:
    """Sahifada (asosiy frame + barcha iframe'lar) captcha belgisi bor-yo'qligini
    tekshiradi. Topilsa QISQA IZOH (nima topilgani) qaytaradi, topilmasa None.
    Playwright `page` (sync_api) obyekti kutiladi."""
    try:
        for frame in page.frames:
            url = (frame.url or "").lower()
            for belgi in CAPTCHA_IFRAME_BELGILARI:
                if belgi in url:
                    return f"iframe manzilida '{belgi}' aniqlandi ({frame.url})"
    except Exception:
        pass

    try:
        matn = page.inner_text("body").lower()
    except Exception:
        matn = ""
    for belgi in CAPTCHA_MATN_BELGILARI:
        if belgi in matn:
            return f"sahifa matnida '{belgi}' iborasi topildi"

    return None


def captcha_holatini_tekshir_matn(matn: str) -> str | None:
    """`captcha_holatini_tekshir()` bilan bir xil kalit-so'z ro'yxatidan
    foydalanadi, lekin Playwright `page` emas — TAYYOR matn (masalan
    desktop oynadan yig'ilgan) qabul qiladi. Ikkala qatlam (brauzer/
    desktop) bir xil CAPTCHA_MATN_BELGILARI'ga tayanadi, natijada ikkovi
    ham bir xil qat'iylikda."""
    matn_kichik = (matn or "").lower()
    for belgi in CAPTCHA_MATN_BELGILARI:
        if belgi in matn_kichik:
            return f"oyna matnida '{belgi}' iborasi topildi"
    return None


# ------------------------------------------------------------- saqlash ----

SAQLASH_KALIT_SOZLAR = [
    # Ingliz
    "save", "save as", "overwrite", "replace existing", "export", "keep current format",
    "yes" ,  # "Save?/Keep changes?" dialogidagi "Yes" alohida ehtiyot bo'lish uchun emas,
             # umumiy "yes" juda keng — shuning uchun quyida o'chiramiz (izoh uchun qoldirilgan)
    # O'zbek/rus
    "saqlash", "saqla", "yozib qo'yish", "fayl sifatida saqlash",
    "сохранить", "сохранение", "заменить", "перезаписать",
]
# "yes" kabi haddan tashqari keng so'zni chiqarib tashlaymiz — false-positive
# xavfi (masalan oddiy tasdiq dialogida "Yes" tugmasi doim saqlash emas).
SAQLASH_KALIT_SOZLAR = [s for s in SAQLASH_KALIT_SOZLAR if s != "yes"]


def saqlash_harakatimi(matn: str) -> str | None:
    """Element matni FAYL SAQLASH/YOZISH harakatiga (Save/Save As/
    Overwrite/Сохранить va h.k.) mos kelsa topilgan kalit so'zni qaytaradi,
    aks holda None. Desktop (Bosqich 2, `jarvis_desktop.py`) uchun —
    "faqat non-destruktiv, hech qachon saqlamasdan" qoidasini kod
    darajasida ta'minlash uchun ATAYLAB ALOHIDA, `harakat_toifasi()`ni
    (brauzer bosqichi allaqachon sinalgan/tasdiqlangan) o'zgartirmasdan
    qo'shilgan — shu bilan Bosqich 1 xatti-harakati buzilmaydi."""
    return _matnda_kalit_sozlar_bormi(matn, SAQLASH_KALIT_SOZLAR)


# -------------------------------------------------------- harakat toifasi ----

TOLOV_KALIT_SOZLAR = [
    # Ingliz
    "pay", "payment", "checkout", "buy now", "purchase", "subscribe",
    "subscription", "donate", "deposit", "withdraw", "invest", "top up",
    "add funds", "billing", "card number", "cvv", "credit card", "debit card",
    "crypto", "bitcoin", "wallet address", "send money", "transfer funds",
    "place order", "confirm order", "complete purchase", "renew subscription",
    # O'zbek/rus (real saytlarda ko'p uchraydi)
    "to'lov", "tolov", "to'lash", "tolash", "to'lang", "pul o'tkazish",
    "obuna bo'lish", "obuna", "chegirma bilan sotib olish", "sotib olish",
    "karta raqami", "kartadan yechish", "hisobni to'ldirish",
    "оплата", "оплатить", "купить", "подписка", "перевод денег",
    "пополнить", "снять средства", "картой", "заказ оформить",
]

HISOB_YARATISH_KALIT_SOZLAR = [
    "sign up", "signup", "register", "create account", "get started",
    "join now", "join free", "start free trial", "create your account",
    "ro'yxatdan o'tish", "royxatdan otish", "hisob yaratish",
    "hisob oching", "hisob ochish", "boshlash",
    "регистрация", "зарегистрироваться", "создать аккаунт",
]

# Parol-turidagi maydonlarga XAVFSIZ_TOLDIR ORQALI umuman yozilmaydi (mavjud
# umumiy "parol so'ramaydi/saqlamaydi" qoidasi bilan mos, GUI'da ham amal
# qiladi).
PAROL_MAYDON_BELGILARI = [
    "password", "parol", "pin", "cvv", "cvc", "card-number", "cardnumber",
    "card_number", "otp", "one-time-code", "security-code", "securitycode",
]


def _matnda_kalit_sozlar_bormi(matn: str, royxat: list[str]) -> str | None:
    matn_kichik = (matn or "").strip().lower()
    for kalit in royxat:
        if kalit in matn_kichik:
            return kalit
    return None


def harakat_toifasi(matn: str) -> tuple[str, str | None]:
    """Bosiladigan elementning ko'rinadigan matni (yoki aria-label)ga qarab
    toifasini aniqlaydi. Qaytaradi: (toifa, topilgan_kalit_soz).
    Toifa — "tolov" | "hisob_yaratish" | "xavfsiz"."""
    kalit = _matnda_kalit_sozlar_bormi(matn, TOLOV_KALIT_SOZLAR)
    if kalit:
        return "tolov", kalit
    kalit = _matnda_kalit_sozlar_bormi(matn, HISOB_YARATISH_KALIT_SOZLAR)
    if kalit:
        return "hisob_yaratish", kalit
    return "xavfsiz", None


def maydon_parolmi(selector_yoki_nom: str, input_type: str | None = None) -> bool:
    """Fill qilinmoqchi bo'lgan maydon parol/PIN/karta-raqami turidan
    ekanini aniqlaydi — selector matni VA (bo'lsa) haqiqiy HTML input type
    ikkalasi ham tekshiriladi (type='password' ENG ishonchli signal)."""
    if input_type and input_type.strip().lower() == "password":
        return True
    matn = (selector_yoki_nom or "").lower()
    return any(belgi in matn for belgi in PAROL_MAYDON_BELGILARI)
