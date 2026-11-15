"""
JARVIS — brauzer (parolsiz)

Jarvis'ning o'z Chrome profili. Azizbek bir marta QO'LDA kiradi,
sessiya `brauzer_profil` papkasida saqlanadi. Keyin Jarvis o'sha
ochilgan hisobda ishlaydi — parolni ko'rmaydi, so'ramaydi.

O'rnatish (bir marta):
    pip install playwright
    playwright install chromium

Qo'lda kirish (Azizbek o'zi bajaradi):
    python jarvis_brauzer.py login
    python jarvis_brauzer.py login https://publish.buffer.com

Tekshirish:
    python jarvis_brauzer.py holat https://instagram.com

MUHIM: profil bir vaqtda faqat bitta jarayonda ochiladi.
Qo'lda ochilgan oynani yopmasdan Jarvis undan foydalana olmaydi.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import jarvis_brauzer_xavfsizlik as xavfsizlik
from jarvis_brauzer_xavfsizlik import BrauzerXavfsizlikXatosi

BASE_DIR = Path(__file__).parent
PROFIL = BASE_DIR / "brauzer_profil"
PROFIL.mkdir(exist_ok=True)


def ochish(headless: bool = False):
    """Doimiy profil bilan brauzer ochadi.
    Qaytaradi: (playwright, context) — ikkalasini ham yopish kerak."""
    pw = sync_playwright().start()
    kwargs = dict(
        user_data_dir=str(PROFIL),
        headless=headless,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        ctx = pw.chromium.launch_persistent_context(channel="chrome", **kwargs)
    except Exception:
        # Chrome topilmasa, Playwright'ning o'z chromium'i
        ctx = pw.chromium.launch_persistent_context(**kwargs)
    return pw, ctx


def login(url: str):
    """Ko'rinadigan brauzer ochadi. Azizbek qo'lda kiradi, Enter bosadi."""
    pw, ctx = ochish(headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, wait_until="domcontentloaded")
    print(f"\nBrauzer ochildi: {url}")
    print("Kerakli hisoblarga QO'LDA kiring (Google, Instagram, Buffer...).")
    print("Tugagach, shu yerga qaytib Enter bosing — sessiya saqlanadi.\n")
    input("Tayyor bo'lsangiz Enter: ")
    ctx.close()
    pw.stop()
    print(f"Sessiya saqlandi: {PROFIL}")


def holat(url: str):
    """Sahifani ochib, sarlavha va matnning boshini ko'rsatadi."""
    pw, ctx = ochish(headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    print(f"URL:      {page.url}")
    print(f"Sarlavha: {page.title()}")
    matn = page.inner_text("body")[:1500]
    print("\n--- sahifa matni (boshi) ---")
    print(matn)
    ctx.close()
    pw.stop()


def captchani_tekshir_va_toxtat(page):
    """Sahifada CAPTCHA bo'lsa, DARHOL `BrauzerXavfsizlikXatosi` ko'taradi —
    hech qachon "hal qilishga" urinilmaydi (Azizbek 2026-09-21 qoidasi).
    Har qanday harakat-oqimi (navigatsiyadan keyin, muhim tugma bosishdan
    oldin) shu funksiyani chaqirishi mumkin, `xavfsiz_bos`/`xavfsiz_toldir`
    buni AVTOMATIK ham qiladi."""
    izoh = xavfsizlik.captcha_holatini_tekshir(page)
    if izoh:
        raise BrauzerXavfsizlikXatosi(
            f"CAPTCHA aniqlandi ({izoh}) — hal qilishga URINILMADI, "
            "to'xtatildi. Azizbekka darhol xabar bering."
        )


def xavfsiz_bos(page, selector: str, *, izoh: str = "", hisob_yaratish_tasdiqlandi: bool = False, timeout: int = 5000) -> dict:
    """Playwright orqali bosishning YAGONA tavsiya etiladigan yo'li —
    xavfsizlik qatlami (CAPTCHA/to'lov/hisob-yaratish) BILAN BIRGA.

    - CAPTCHA aniqlansa: darhol to'xtaydi (hech qanday bypass yo'q).
    - Elementning matni/aria-label'i TO'LOV kalit so'ziga mos kelsa: darhol
      to'xtaydi (HECH QANDAY bypass parametri YO'Q — bu ataylab, parol
      qoidasi bilan bir xil qat'iylikda).
    - Elementning matni HISOB-YARATISH kalit so'ziga mos kelsa: faqat
      `hisob_yaratish_tasdiqlandi=True` berilgandagina bosadi. Bu flag
      FAQAT Jarvis (chaqiruvchi) Azizbekdan REAL chatda tasdiq olgandan
      keyin qo'lda berilishi kerak — funksiyaning o'zi hech kimdan
      so'ramaydi, faqat "so'ralmagan bo'lsa bloklaydi" qoidasini kod
      darajasida kafolatlaydi.
    - Aks holda (xavfsiz): oddiy bosadi.

    Muvaffaqiyatda {"toifa", "matn", "izoh"} lug'atini qaytaradi — chaqiruvchi
    nima sodir bo'lganini logga yozishi uchun."""
    captchani_tekshir_va_toxtat(page)

    loc = page.locator(selector).first
    try:
        elem_matn = loc.inner_text(timeout=timeout)
    except Exception:
        elem_matn = ""
    try:
        aria = loc.get_attribute("aria-label") or ""
    except Exception:
        aria = ""
    tekshiriladigan_matn = f"{elem_matn} {aria}".strip()

    toifa, kalit = xavfsizlik.harakat_toifasi(tekshiriladigan_matn)

    if toifa == "tolov":
        raise BrauzerXavfsizlikXatosi(
            f"TO'LOV/PUL HARAKATI bloklandi (kalit so'z: '{kalit}', "
            f"element: '{tekshiriladigan_matn[:80]}', selector: '{selector}'). "
            "Bu HECH QACHON avtomatik bosilmaydi — Azizbek o'zi bajarishi kerak."
        )
    if toifa == "hisob_yaratish" and not hisob_yaratish_tasdiqlandi:
        raise BrauzerXavfsizlikXatosi(
            f"HISOB YARATISHNI YAKUNLASH bloklandi (kalit so'z: '{kalit}', "
            f"element: '{tekshiriladigan_matn[:80]}', selector: '{selector}'). "
            "Bu tugmani bosishdan oldin Azizbekdan ANIQ tasdiq oling, keyin "
            "hisob_yaratish_tasdiqlandi=True bilan qayta chaqiring."
        )

    loc.click(timeout=timeout)
    return {"toifa": toifa, "matn": tekshiriladigan_matn, "izoh": izoh}


def xavfsiz_toldir(page, selector: str, qiymat: str, *, izoh: str = "", timeout: int = 5000) -> dict:
    """Playwright orqali matn kiritishning YAGONA tavsiya etiladigan yo'li.

    - Maydon parol/PIN/CVV/karta-raqami turidan bo'lsa (HTML type='password'
      ENG ishonchli signal, yoki selector nomida shunga o'xshash kalit so'z
      bo'lsa): darhol to'xtaydi — HECH QACHON bunday maydonga yozilmaydi.
    - CAPTCHA aniqlansa: darhol to'xtaydi.
    - Aks holda oddiy `fill` qiladi."""
    loc = page.locator(selector).first
    try:
        input_type = loc.get_attribute("type")
    except Exception:
        input_type = None

    if xavfsizlik.maydon_parolmi(selector, input_type):
        raise BrauzerXavfsizlikXatosi(
            f"PAROL/PIN/karta-raqami turidagi maydonga yozish bloklandi "
            f"(selector: '{selector}', type='{input_type}'). Bu HECH QACHON "
            "avtomatik to'ldirilmaydi."
        )

    captchani_tekshir_va_toxtat(page)

    loc.fill(qiymat, timeout=timeout)
    return {"selector": selector, "izoh": izoh}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    buyruq = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com"

    if buyruq == "login":
        login(url)
    elif buyruq == "holat":
        holat(url)
    else:
        print(__doc__)
        raise SystemExit(1)
