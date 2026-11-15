# -*- coding: utf-8 -*-
"""
Bitta skript ikkala vazifani bajaradi:
1) MAJBURIY demo video (1920x1080): panel ochiladi -> 2 ta xodim standup
   hisobot beradi -> "Nozima, Orzu'da kim to'lamagan?" -> oxirgi majlis.
2) Sifat skrinshotlari (1920 va 375).

Natijalar:
  kiruvchi/demo/ai_xodimlar_demo.mp4  (Playwright video, keyin nomlanadi)
  jarvis_hud/_sinov_1920_asosiy.png
  jarvis_hud/_sinov_1920_majlis.png
  jarvis_hud/_sinov_375_mobil.png
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
DEMO_DIR = BASE.parent / "kiruvchi" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR = BASE / "_pw_video_tmp"
VIDEO_DIR.mkdir(exist_ok=True)

URL = "http://localhost:8080/jamoa.html"
console_errors = []


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])

        # ---- 1) DESKTOP + VIDEO ----
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=str(VIDEO_DIR), record_video_size={"width": 1920, "height": 1080})
        page = ctx.new_page()
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))

        print("Sahifa ochilmoqda...")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(BASE / "_sinov_1920_asosiy.png"))
        print("OK asosiy skrinshot")

        print("Standup boshlanmoqda (2 xodim kutiladi)...")
        page.click("#standupBtn")
        # Birinchi va ikkinchi xodim gapirib bo'lguncha kutamiz (spWho o'zgarishini kuzatamiz)
        seen = []
        t0 = time.time()
        last_who = None
        while time.time() - t0 < 90 and len(seen) < 2:
            who = page.inner_text("#spWho")
            if who and who != "Jamoa tayyor" and who != last_who:
                seen.append(who)
                last_who = who
                print("  gapiryapti:", who)
            page.wait_for_timeout(500)
        # ikkinchisi tugab, uchinchisi boshlanguncha ozgina kutamiz, keyin to'xtatamiz
        page.wait_for_timeout(3000)
        page.click("#standupBtn")  # to'xtatish (toggle)
        page.wait_for_timeout(1500)
        print("Standup to'xtatildi (2 xodim eshittirildi).")

        print("Ismga murojaat: 'Nozima, Orzu'da kim to'lamagan?'")
        page.fill("#soraliqInput", "Nozima, Orzu'da kim to'lamagan?")
        page.click("#soraliqBtn")
        # javob tugaguncha kutamiz (tugma qayta yoqilguncha)
        page.wait_for_selector("#soraliqBtn:not([disabled])", timeout=60000)
        page.wait_for_timeout(1500)
        print("Ismga murojaat javobi tugadi.")

        print("Oxirgi majlis ijro etilmoqda (bir necha daqiqa davom etishi mumkin)...")
        page.click("#majlisOxirgiBtn")
        page.wait_for_selector("#majlisNatija:not([hidden])", timeout=240000)
        page.wait_for_timeout(2000)
        print("Majlis tugadi, g'oyalar ko'rindi.")
        page.screenshot(path=str(BASE / "_sinov_1920_majlis.png"), full_page=True)
        print("OK majlis skrinshot")

        # bitta g'oyani "Topshiriq qilish" bilan sinaymiz -- tugma matni
        # haqiqatan o'zgarganini ANIQ tekshiramiz (screenshot taxminiga
        # tayanmasdan).
        try:
            before = page.inner_text('[data-gtoya="0"]')
            page.click('[data-gtoya="0"]')
            page.wait_for_function(
                "document.querySelector('[data-gtoya=\"0\"]').textContent.includes('Qo')",
                timeout=15000,
            )
            after = page.inner_text('[data-gtoya="0"]')
            print(f"Topshiriq tugmasi: '{before.strip()}' -> '{after.strip()}' (OK, o'zgardi)")
        except Exception as e:
            print("XATO: Topshiriq tugmasi matni o'zgarmadi:", e)

        page.wait_for_timeout(1000)
        ctx.close()  # video shu yerda yakunlanadi

        # ---- 2) MOBIL SKRINSHOT (video kerak emas, tezroq) ----
        ctx2 = browser.new_context(viewport={"width": 375, "height": 812})
        page2 = ctx2.new_page()
        page2.on("console", lambda msg: console_errors.append(f"[mobil:{msg.type}] {msg.text}") if msg.type == "error" else None)
        page2.goto(URL, wait_until="networkidle", timeout=30000)
        page2.wait_for_timeout(2500)
        page2.screenshot(path=str(BASE / "_sinov_375_mobil.png"), full_page=True)
        print("OK mobil skrinshot")
        ctx2.close()

        browser.close()

        # video faylni topib, nomini o'zgartirib demo papkaga ko'chiramiz
        vids = list(VIDEO_DIR.glob("*.webm"))
        if vids:
            vid = max(vids, key=lambda p: p.stat().st_mtime)
            target = DEMO_DIR / "ai_xodimlar_demo.webm"
            vid.replace(target)
            print("Video saqlandi:", target)
        else:
            print("OGOHLANTIRISH: video fayl topilmadi!")


if __name__ == "__main__":
    try:
        run()
    finally:
        print("\n--- KONSOL XATOLARI ---")
        if console_errors:
            for e in console_errors:
                print(e)
        else:
            print("(yo'q)")
