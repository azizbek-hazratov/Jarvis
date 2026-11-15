"""
Bir martalik sinov skripti — ChatPlace.io platformasini jarvis_brauzer profili orqali
o'rganish (ro'yxatdan o'tish, Instagram ulash oqimi, narxlash sahifasi).
PAROL HECH QAYERDA KIRITILMAYDI — faqat allaqachon ochiq Google sessiyasidan foydalaniladi.
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
PROFIL = BASE_DIR / "brauzer_profil"
SHOT_DIR = BASE_DIR / "kiruvchi" / "chatplace_screenshots"
SHOT_DIR.mkdir(exist_ok=True, parents=True)

sys.stdout.reconfigure(encoding="utf-8")

counter = [0]
def shot(page, name):
    counter[0] += 1
    fname = f"{counter[0]:02d}_{name}.png"
    path = SHOT_DIR / fname
    try:
        page.screenshot(path=str(path), full_page=True)
        print(f"[SHOT] {fname}  url={page.url}")
    except Exception as e:
        print(f"[SHOT XATO] {fname}: {e}")

def main():
    pw = sync_playwright().start()
    ctx = None
    try:
        try:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                headless=False,
                channel="chrome",
                viewport={"width": 1440, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as e:
            print("Chrome kanal xato, oddiy chromium bilan:", e)
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                headless=False,
                viewport={"width": 1440, "height": 900},
            )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print("\n=== 1) Bosh sahifa ===")
        page.goto("https://chatplace.io/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        shot(page, "bosh_sahifa")

        print("\n=== 2) Narxlash sahifasi ===")
        page.goto("https://chatplace.io/pricing/index.html", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        shot(page, "narxlash")

        print("\n=== 3) Ro'yxatdan o'tish / Sign up sahifasi ===")
        page.goto("https://app.chatplace.io/auth/sign-up/?locale=en", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        shot(page, "royxatdan_otish")

        print("\nSahifa matni (boshi):")
        try:
            print(page.inner_text("body")[:1500])
        except Exception:
            pass

        print("\nTugmalar/linklar:")
        try:
            btns = page.eval_on_selector_all("button, a", "els => els.map(e => (e.innerText||'').trim()).filter(x=>x)")
            for b in btns:
                print(" -", b)
        except Exception as e:
            print("xato:", e)

    finally:
        print("\nTayyor. Kontekst ochiq qoladimi yo'qmi tekshirilmoqda...")
        if ctx:
            ctx.close()
        pw.stop()

if __name__ == "__main__":
    main()
