import sys, time
sys.path.insert(0, '.')
from jarvis_brauzer import ochish

LOG = "C:/Users/Dell/jarvis/_yt_log2.txt"

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

open(LOG, "w", encoding="utf-8").close()

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/watch?v=vOUVaddfjwk", wait_until="load", timeout=60000)
page.wait_for_timeout(2500)

try:
    page.keyboard.press("Escape")
except Exception:
    pass
page.wait_for_timeout(500)

try:
    page.eval_on_selector("video", "v => { v.muted = false; v.volume = 1.0; v.play(); }")
    page.wait_for_timeout(1500)
    is_paused = page.eval_on_selector("video", "v => v.paused")
    is_muted = page.eval_on_selector("video", "v => v.muted")
    vol = page.eval_on_selector("video", "v => v.volume")
    log(f"paused={is_paused} muted={is_muted} volume={vol}")
    if is_paused:
        # ba'zan birinchi play() brauzer siyosati bilan bloklanadi, yana urinamiz
        page.eval_on_selector("video", "v => v.play()")
        page.wait_for_timeout(1500)
        is_paused2 = page.eval_on_selector("video", "v => v.paused")
        log(f"ikkinchi urinishdan keyin paused={is_paused2}")
except Exception as e:
    log(f"xato: {e}")

log(f"URL: {page.url}")
log(f"TITLE: {page.title()}")
log("TAYYOR")

while True:
    time.sleep(20)
