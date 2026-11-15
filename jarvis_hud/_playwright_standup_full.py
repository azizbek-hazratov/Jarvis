# -*- coding: utf-8 -*-
"""To'liq "Ertalabki yig'ilish" (6 xodim + xulosa) oxirigacha ishlashini,
JS xatosiz va tugma holati to'g'ri tiklanishini tekshiradi (speakOne/
clearSpeaking/zal-highlight kodiga tegilgani uchun)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:8080/jamoa.html"
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    page.click("#standupBtn")
    print("Standup boshlandi, tugashini kutyapmiz (max 5 daqiqa)...")
    page.wait_for_selector('#standupBtn[aria-pressed="false"]', timeout=300000)
    print("Standup tugadi (tugma holati: to'xtatilgan/asl holatga qaytdi).")
    lbl = page.inner_text("#standupLbl")
    who = page.inner_text("#spWho")
    print("Tugma matni:", lbl, "| spWho:", who)
    ctx.close()
    browser.close()

print("Konsol xatolari:", errors or "(yo'q)")
