import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1400})
    errs = []
    page.on("console", lambda m: errs.append(f"[{m.type}] {m.text}") if m.type=="error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto("http://localhost:8080/jamoa.html", wait_until="networkidle")
    time.sleep(2)

    btn = page.locator('#c-samandar [data-confirm]')
    btn.click()
    time.sleep(0.3)
    print("IMMEDIATELY_AFTER_CLICK hidden:", repr(page.locator("#tasdiqOverlay").get_attribute("hidden")))
    print("IMMEDIATELY_AFTER_CLICK text:", page.locator("#tasdiqMatn").inner_text())
    page.wait_for_function("document.getElementById('tasdiqMatn').innerText.includes('Rostdan')", timeout=8000)
    print("FINAL hidden:", repr(page.locator("#tasdiqOverlay").get_attribute("hidden")))
    print("FINAL text:", page.locator("#tasdiqMatn").inner_text())
    page.screenshot(path="_sinov_tasdiq_modal_ochiq.png", full_page=False)

    page.locator("#tasdiqYoq").click()
    time.sleep(1)
    print("HIDDEN_AFTER_YOQ:", repr(page.locator("#tasdiqOverlay").get_attribute("hidden")))
    page.screenshot(path="_sinov_tasdiq_yoq_keyin.png", full_page=False)
    print("ERRORS:", errs)
    browser.close()
