# -*- coding: utf-8 -*-
"""HUD 'OXIRGI AMALLAR' panelining yangi vizual (rangli belgi, kattaroq
shrift, kirish-animatsiyasi) haqiqatan ishlayotganini real brauzerda
(Playwright) skrinshot bilan tasdiqlash uchun bir martalik sinov skripti.
Vaqtinchalik — ishlatib bo'lgach o'chirilishi kerak."""
import sys, time, threading, requests
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

TOKEN = "9674e2cdd2056ca60afd8e09e3658e5da869663e05a48d74"
HUD_URL = "http://localhost:8080/"
ASK_URL = "http://localhost:8090/ask"

def yangi_amal_yubor():
    # Sahifa ochilib, birinchi poll tugagandan keyin ishga tushadi (pastda kechiktirilgan)
    time.sleep(2.0)
    r = requests.post(
        ASK_URL,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={"text": "Bash orqali joriy papkadagi fayllar ro'yxatini ko'rsat (faqat o'qish, hech narsa o'zgartirma)."},
        timeout=90,
    )
    print("ASK javobi:", r.status_code, r.text[:200])

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(HUD_URL, wait_until="networkidle")
    time.sleep(1.5)  # birinchi /amallar poll tugashi uchun

    t = threading.Thread(target=yangi_amal_yubor)
    t.start()

    # Yangi yozuv paydo bo'lishini (4s pollda) kuzatib, DOMda ko'ringan zahoti
    # (animatsiya davom etayotgan/yangi tugagan paytda) skrinshot olamiz.
    oldin = page.inner_text("#oxirgiAmallar")
    yangi_topildi = False
    for i in range(30):  # ~15s gacha kutamiz
        time.sleep(0.5)
        hozir = page.inner_text("#oxirgiAmallar")
        if hozir != oldin:
            # DOM yangilangan zahoti — animatsiya .55s bo'lgani uchun darhol skrinshot
            page.screenshot(path="C:/Users/Dell/jarvis/sinov/hud_amal_yangi_animatsiya.png")
            print(f"[{i}] Yangi qator aniqlandi, skrinshot olindi (animatsiya paytida/darhol keyin).")
            yangi_topildi = True
            time.sleep(1.2)
            page.screenshot(path="C:/Users/Dell/jarvis/sinov/hud_amal_yangi_tinch.png")
            print("Ikkinchi skrinshot (tinch holat) ham olindi.")
            break

    if not yangi_topildi:
        page.screenshot(path="C:/Users/Dell/jarvis/sinov/hud_amal_topilmadi.png")
        print("OGOHLANTIRISH: yangi qator 15s ichida topilmadi.")

    t.join()
    # Panelning o'zini crop qilib ham saqlaymiz (aniqroq ko'rish uchun)
    el = page.query_selector("#oxirgiAmallar")
    if el:
        el.screenshot(path="C:/Users/Dell/jarvis/sinov/hud_amal_panel_crop.png")
        print("Panel crop skrinshoti olindi.")
    browser.close()
