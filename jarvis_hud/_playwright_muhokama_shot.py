# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
URL = "http://localhost:8080/jamoa.html"
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)
    page.click("#majlisOxirgiBtn")
    page.wait_for_selector("#majlisNatija:not([hidden])", timeout=240000)
    page.click("#majlisMuhokama summary")
    page.wait_for_timeout(500)
    page.screenshot(path=str(BASE / "_sinov_1920_muhokama.png"), full_page=True)
    ctx.close()
    browser.close()

print("Xatolar:", errors or "(yo'q)")
