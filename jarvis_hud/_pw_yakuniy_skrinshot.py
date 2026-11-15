import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1400})
    page.goto("http://localhost:8080/jamoa.html", wait_until="networkidle")
    time.sleep(2.5)
    page.screenshot(path="_yakuniy_panel_toza_holat.png", full_page=True)
    browser.close()
