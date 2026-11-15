from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:6060"
ACCOUNTS = [
    ("admin", "admin@testfc.uz", "fc_admin_2026"),
    ("murabbiy", "murabbiy@testfc.uz", "murabbiy_2026"),
    ("ota-ona", "ota@testfc.uz", "ota_2026"),
    ("super-admin", "superadmin@nishon.uz", "super_dev_2026"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    for rol, email, parol in ACCOUNTS:
        for tag, vw in [("mobil375", {"width": 375, "height": 812}), ("desktop", {"width": 1440, "height": 900})]:
            page = browser.new_page(viewport=vw)
            page.goto(f"{BASE}/login.html", wait_until="networkidle")
            page.fill("#login", email)
            page.fill("#parol", parol)
            page.click("button[type=submit]")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1200)
            page.screenshot(path=f"C:/Users/Dell/jarvis/_bug_{rol}_{tag}.png", full_page=True)
            print(rol, tag, "->", page.url)
            page.close()
    browser.close()
print("TUGADI")
