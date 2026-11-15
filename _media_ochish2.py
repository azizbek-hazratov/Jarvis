import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)

p1 = ctx.pages[0] if ctx.pages else ctx.new_page()
p1.goto("https://www.youtube.com/watch?v=hfx5hI8Au-A", wait_until="domcontentloaded", timeout=60000)
p1.wait_for_timeout(2500)
try:
    p1.locator("button.ytp-large-play-button").click(timeout=2000)
except Exception:
    pass
try:
    p1.evaluate("var v=document.querySelector('video'); if(v){v.muted=false; v.volume=1; v.play();}")
except Exception:
    pass
p1.bring_to_front()

p2 = ctx.new_page()
p2.goto("file:///C:/Users/Dell/jarvis/_bem_baraka.html", wait_until="domcontentloaded", timeout=30000)

time.sleep(10800)
