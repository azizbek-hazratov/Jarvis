# -*- coding: utf-8 -*-
"""Faqat toza (SINOV izlarisiz) yakuniy skrinshotlar uchun tezkor skript."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
URL = "http://localhost:8080/jamoa.html"
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(BASE / "_sinov_1920_asosiy.png"))
    print("OK 1920 asosiy")
    ctx.close()

    ctx2 = browser.new_context(viewport={"width": 375, "height": 812})
    page2 = ctx2.new_page()
    page2.on("console", lambda m: errors.append(f"[mobil:{m.type}] {m.text}") if m.type == "error" else None)
    page2.goto(URL, wait_until="networkidle", timeout=30000)
    page2.wait_for_timeout(2000)
    page2.screenshot(path=str(BASE / "_sinov_375_mobil.png"), full_page=True)
    print("OK 375 mobil")
    ctx2.close()
    browser.close()

print("Xatolar:", errors or "(yo'q)")
