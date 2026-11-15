import sys, time
sys.path.insert(0, '.')
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/results?search_query=Jaloliddin+Ahmadaliyev+Bir+umr", wait_until="load", timeout=60000)
page.wait_for_timeout(3000)

video = page.query_selector("ytd-video-renderer a#video-title")
if video:
    title = video.get_attribute("title")
    video.click()
    page.wait_for_timeout(4000)
    print(f"OYNATILMOQDA: {title}", flush=True)
    print(f"URL: {page.url}", flush=True)
else:
    print("Video topilmadi", flush=True)

# oyna ochiq va qo'shiq davom etsin uchun jarayonni ushlab turamiz
while True:
    time.sleep(30)
