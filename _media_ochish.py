import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)

# 1-tab: musiqa
p1 = ctx.pages[0] if ctx.pages else ctx.new_page()
p1.goto("https://www.youtube.com/watch?v=hfx5hI8Au-A", wait_until="domcontentloaded", timeout=60000)
p1.wait_for_timeout(2500)
try:
    p1.locator("button.ytp-large-play-button").click(timeout=2000)
except Exception:
    pass
try:
    p1.evaluate("var v=document.querySelector('video'); if(v){v.muted=false; v.volume=1; v.play();}")
except Exception as e:
    print("MUSIQA JS XATO:", e)

# 2-tab: hujjat
p2 = ctx.new_page()
p2.goto("file:///C:/Users/Dell/jarvis/_bem_baraka.html", wait_until="domcontentloaded", timeout=30000)
p2.bring_to_front()

print("MUSIQA HOLATI:", p1.evaluate("var v=document.querySelector('video'); v? {paused:v.paused, muted:v.muted, volume:v.volume}:'yoq'"))
print("HUJJAT SARLAVHA:", p2.title())
print("IKKALASI HAM OCHIQ, jarayon tirik qoladi.")
time.sleep(10800)
