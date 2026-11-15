# -*- coding: utf-8 -*-
"""
Telegram orqali AI Expert botiga (mijoz sifatida) real xabar yuborilganda,
pixel-ofis sahifasidagi AI Expert belgisi "band"ga o'tishini va keyin
"bosh"ga qaytishini Playwright bilan skrinshot orqali qayd qiladi.

Ishlatish: bu skript ishga tushgach, Azizbek Telegram orqali
@samandarakajonbot ga (AI Expert bot) oddiy savol yuborishi kerak —
skript shuni kutib, holat o'zgarishini skrinshotga oladi.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

BASE_DIR = Path(r"C:\Users\Dell\jarvis")
SAHIFA = BASE_DIR / "kiruvchi" / "ai_ofis_pixel.html"
CHIQISH_DIR = BASE_DIR / "jarvis_hud"
LOG_FAYL = BASE_DIR / "sinov" / "ai_expert_holati_natija.txt"

MAKS_KUTISH_S = 180
TEKSHIRISH_INTERVAL_S = 0.3


def log(fayl, matn):
    vaqt = datetime.now().strftime("%H:%M:%S")
    qator = f"[{vaqt}] {matn}"
    print(qator)
    with open(fayl, "a", encoding="utf-8") as f:
        f.write(qator + "\n")


def main():
    LOG_FAYL.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FAYL, "w", encoding="utf-8") as f:
        f.write("")

    log(LOG_FAYL, "Boshlandi — Telegram orqali AI Expert botiga (@samandarakajonbot) xabar yuborilishini kutmoqda...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 950})
        page.goto(f"file:///{SAHIFA.as_posix()}")
        page.wait_for_timeout(1000)

        el = page.locator("#agent-expert1")

        korilgan_band = False
        korilgan_bosh_qaytish = False
        boshlanish = time.time()

        while time.time() - boshlanish < MAKS_KUTISH_S:
            klass = el.get_attribute("class") or ""
            band = "expert1-band" in klass

            if band and not korilgan_band:
                korilgan_band = True
                yol = CHIQISH_DIR / f"ai_expert_sinov_1_band_{datetime.now():%Y%m%d_%H%M%S}.png"
                page.screenshot(path=str(yol))
                log(LOG_FAYL, f"BAND holatga o'tdi — skrinshot: {yol.name}")

            if korilgan_band and not band and not korilgan_bosh_qaytish:
                korilgan_bosh_qaytish = True
                yol = CHIQISH_DIR / f"ai_expert_sinov_2_bosh_{datetime.now():%Y%m%d_%H%M%S}.png"
                page.screenshot(path=str(yol))
                log(LOG_FAYL, f"BOSH holatga qaytdi — skrinshot: {yol.name}")
                break

            page.wait_for_timeout(int(TEKSHIRISH_INTERVAL_S * 1000))

        if not korilgan_band:
            log(LOG_FAYL, f"XATO: {MAKS_KUTISH_S}s ichida 'band' holati umuman ko'rinmadi.")
        elif not korilgan_bosh_qaytish:
            log(LOG_FAYL, f"OGOHLANTIRISH: band ko'rindi, lekin {MAKS_KUTISH_S}s ichida 'bosh'ga qaytishi ko'rinmadi.")
        else:
            log(LOG_FAYL, "MUVAFFAQIYATLI: band->bosh o'tishi to'liq qayd qilindi.")

        browser.close()


if __name__ == "__main__":
    main()
