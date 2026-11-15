import sys
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
print("Joriy URL:", page.url)

try:
    holat = page.evaluate("""() => {
        const v = document.querySelector('video');
        if (!v) return 'video topilmadi';
        return JSON.stringify({paused: v.paused, muted: v.muted, volume: v.volume, currentTime: v.currentTime, readyState: v.readyState, error: v.error ? v.error.message : null});
    }""")
    print("Video holati:", holat)
except Exception as e:
    print("Xato:", e)

page.screenshot(path="_yt_holat.png")
print("Skrinshot saqlandi")

ctx.close()
pw.stop()
