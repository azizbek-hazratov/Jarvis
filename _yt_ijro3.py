import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/watch?v=hfx5hI8Au-A", wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(3000)
try:
    # unmute va play tugmasini bosishga harakat
    page.locator("button.ytp-large-play-button").click(timeout=3000)
except Exception:
    pass
try:
    page.evaluate("document.querySelector('video') && (document.querySelector('video').muted=false, document.querySelector('video').volume=1, document.querySelector('video').play())")
except Exception as e:
    print("JS XATO:", e)
print("IJRO HOLATI:", page.evaluate("document.querySelector('video') ? {paused: document.querySelector('video').paused, muted: document.querySelector('video').muted, volume: document.querySelector('video').volume, currentTime: document.querySelector('video').currentTime} : 'video topilmadi'"))
print("Brauzer ochiq qolmoqda, jarayon uxlab turadi...")
time.sleep(10800)  # 3 soat ochiq turadi, musiqa davom etadi
