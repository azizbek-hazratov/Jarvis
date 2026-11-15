# -*- coding: utf-8 -*-
"""2026-09-28 kechqurun — Kamola/Instagram voqeasidan keyingi tuzatishni
panelda tasdiqlash uchun bitta martalik sinov skripti (mavjud
_playwright_qa.py naqshiga o'xshash, lekin faqat bitta savolga qaratilgan).
jamoa.html file:// orqali ochiladi (bridge CORS'da "null" origin ruxsat
etilgan) — alohida frontend server (8080) ishga tushirish shart emas."""
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
URL = "file:///" + str((BASE / "jamoa.html").resolve()).replace("\\", "/")
console_errors = []


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()
        page.on("console", lambda m: console_errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"[pageerror] {e}"))
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        matn = "Kamola, instagramda ahvol qanday tekshir"
        print(f"Savol yuborilmoqda: {matn!r}")
        t0 = time.time()
        page.fill("#soraliqInput", matn)
        page.click("#soraliqBtn")
        page.wait_for_selector("#soraliqBtn:not([disabled])", timeout=100000)
        page.wait_for_timeout(600)
        t1 = time.time()

        sp_txt = page.inner_text("#spTxt")
        sp_who = page.inner_text("#spWho")
        batafsil_hidden = page.get_attribute("#spBatafsilWrap", "hidden")
        print(f"[{round(t1-t0,1)}s] gapiruvchi={sp_who!r}")
        print(f"subtitr matni: {sp_txt!r}")
        print(f"batafsil blok hidden attributi: {batafsil_hidden!r}")

        shot = str(BASE / "_sinov_kamola_panel.png")
        page.screenshot(path=shot, full_page=False)
        print(f"Skrinshot saqlandi: {shot}")

        ctx.close()
        browser.close()

    print("\n=== KONSOL XATOLARI ===")
    print(console_errors or "(yo'q)")


if __name__ == "__main__":
    run()
