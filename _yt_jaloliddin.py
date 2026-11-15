import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

QIDIRUV = "Jaloliddin Ahmadaliyev qo'shiq"

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

page.goto("https://www.youtube.com/results?search_query=" + QIDIRUV.replace(" ", "+"),
          wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(2500)

try:
    natija = page.locator("a#video-title").first
    natija.click(timeout=8000)
    print("BOSILDI:", natija.inner_text(timeout=2000))
except Exception as e:
    print("QIDIRUV NATIJASINI BOSISHDA XATO:", e)
    raise SystemExit(1)

page.wait_for_timeout(3000)
try:
    page.locator("button.ytp-large-play-button").click(timeout=3000)
except Exception:
    pass
try:
    page.evaluate(
        "var v=document.querySelector('video'); "
        "if(v){v.muted=false; v.volume=1; v.play();}"
    )
except Exception as e:
    print("JS XATO:", e)

print("IJRO HOLATI:", page.evaluate(
    "document.querySelector('video') ? "
    "{paused: document.querySelector('video').paused, "
    "muted: document.querySelector('video').muted, "
    "url: location.href} : 'video topilmadi'"
))
page.bring_to_front()
print("Brauzer ochiq qolmoqda, qo'shiq davom etadi...")
time.sleep(10800)
