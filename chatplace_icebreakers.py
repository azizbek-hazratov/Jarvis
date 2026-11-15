"""
Ice breakers qidiruv/sozlash skripti — ChatPlace.io (app.chatplace.io) uchun.
jarvis_brauzer.py andozasi: doimiy profil, headless=False, channel=chrome.
PAROL HECH QAYERDA KIRITILMAYDI. Login sahifasiga tushib qolsa, screenshot olib to'xtaydi.

Ishlatish (STEPS ro'yxatini har safar tahrirlab, keyin ishga tushiring):
    python chatplace_icebreakers.py
"""
import sys
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
PROFIL = BASE_DIR / "brauzer_profil"
SHOT_DIR = BASE_DIR / "kiruvchi" / "chatplace_screenshots"
SHOT_DIR.mkdir(exist_ok=True, parents=True)

sys.stdout.reconfigure(encoding="utf-8")

# ============ SHU YERNI HAR SAFAR TAHRIRLANG ============
START_URL = "https://app.chatplace.io/"
START_URL = "https://www.instagram.com/"
STEPS = [
    {"type": "click_text", "text": "Переключиться"},
    {"type": "wait", "ms": 1500},
]
SHOT_PREFIX = "ib"
# ==========================================================

counter_file = SHOT_DIR / "_counter.txt"
if counter_file.exists():
    n = int(counter_file.read_text().strip() or "0")
else:
    n = 0

def shot(page, name):
    global n
    n += 1
    counter_file.write_text(str(n))
    fname = f"{n:03d}_{SHOT_PREFIX}_{name}.png"
    path = SHOT_DIR / fname
    try:
        page.screenshot(path=str(path), full_page=True)
        print(f"[SHOT] {fname}  url={page.url}")
    except Exception as e:
        print(f"[SHOT XATO] {fname}: {e}")

def dump_clickables(page, limit=200):
    try:
        items = page.eval_on_selector_all(
            "button, a, [role=button], [role=tab], li, .menu-item, nav *",
            """els => els.map(e => ({
                tag: e.tagName,
                text: (e.innerText||'').trim().slice(0,80),
                href: e.getAttribute('href')||''
            })).filter(x => x.text)"""
        )
        seen = set()
        print("\n--- Klik qilinadigan elementlar (unikal) ---")
        cnt = 0
        for it in items:
            key = (it['tag'], it['text'])
            if key in seen:
                continue
            seen.add(key)
            print(f" [{it['tag']}] {it['text']!r} href={it['href']}")
            cnt += 1
            if cnt >= limit:
                break
    except Exception as e:
        print("dump_clickables xato:", e)

def check_login_wall(page):
    url = page.url.lower()
    text = ""
    try:
        text = page.inner_text("body")[:500].lower()
    except Exception:
        pass
    if re.search(r"\blogin\b|\bsign-in\b|\bsign-up\b", url):
        print("\n!!! DIQQAT: LOGIN/SIGN-IN SAHIFASIGA TUSHIB QOLDI. TO'XTATILDI. !!!")
        shot(page, "LOGIN_WALL")
        return True
    if re.search(r"\bpassword\b|\bparol\b", text) and ("log in" in text or "sign in" in text or "kirish" in text):
        print("\n!!! DIQQAT: SAHIFADA PAROL SO'RALMOQDA BO'LISHI MUMKIN. TO'XTATILDI. !!!")
        shot(page, "PASSWORD_WALL")
        return True
    return False

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

        print(f"\n=== GOTO {START_URL} ===")
        page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(7000)

        if check_login_wall(page):
            return

        shot(page, "start")
        dump_clickables(page)

        try:
            sidebar_html = page.eval_on_selector_all(
                "nav a, nav button, aside a, aside button, [class*=Sidebar] a, [class*=Sidebar] button, [class*=Nav] a, [class*=Nav] button",
                """els => els.map(e => ({
                    tag: e.tagName,
                    cls: e.className,
                    aria: e.getAttribute('aria-label')||'',
                    title: e.getAttribute('title')||'',
                    href: e.getAttribute('href')||'',
                    text: (e.innerText||'').trim()
                }))"""
            )
            print("\n--- Sidebar elementlari ---")
            for it in sidebar_html:
                print(it)
        except Exception as e:
            print("sidebar dump xato:", e)

        for i, step in enumerate(STEPS):
            print(f"\n=== STEP {i+1}: {step} ===")
            try:
                if step["type"] == "click_text":
                    page.get_by_text(step["text"], exact=step.get("exact", False)).first.click(timeout=10000)
                elif step["type"] == "click_selector":
                    page.locator(step["selector"]).first.click(timeout=10000)
                elif step["type"] == "fill":
                    page.locator(step["selector"]).first.fill(step["text"], timeout=10000)
                elif step["type"] == "wait":
                    page.wait_for_timeout(step.get("ms", 2000))
                elif step["type"] == "goto":
                    page.goto(step["url"], wait_until="domcontentloaded", timeout=60000)
                elif step["type"] == "click_coord":
                    page.mouse.click(step["x"], step["y"])
                else:
                    print("Noma'lum step turi:", step["type"])
            except Exception as e:
                print(f"STEP XATO: {e}")

            page.wait_for_timeout(1500)
            if check_login_wall(page):
                return
            shot(page, f"step{i+1}")
            dump_clickables(page)

        print("\nTayyor. Sahifa matni (to'liq body, 3000 belgi):")
        try:
            print(page.inner_text("body")[:3000])
        except Exception:
            pass

    finally:
        print("\nBrauzer yopilmoqda...")
        if ctx:
            ctx.close()
        pw.stop()

if __name__ == "__main__":
    main()
