import sys
import jarvis_brauzer as jb

qidiruv = "Jaloliddin Ahmadaliyev qo'shiq"
url = "https://www.youtube.com/results?search_query=" + qidiruv.replace(" ", "+").replace("'", "%27")

pw, ctx = jb.ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto(url, wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(2500)

# Birinchi video natijasini bosish
try:
    page.click("ytd-video-renderer a#video-title", timeout=8000)
except Exception:
    try:
        page.click("a#video-title", timeout=8000)
    except Exception as e:
        print("Video topilmadi:", e)
        sys.exit(0)

page.wait_for_timeout(3000)
print("Ochildi:", page.url)
print("Sarlavha:", page.title())
# Brauzer ochiq turishi uchun jarayonni tirik saqlaymiz
import time
while True:
    time.sleep(3600)
