# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
URL = "http://localhost:8080/jamoa.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    page.click("#majlisOxirgiBtn")
    page.wait_for_selector("#majlisNatija:not([hidden])", timeout=240000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(BASE / "_sinov_1920_majlis.png"), full_page=True)
    print("OK")
    ctx.close()
    browser.close()
