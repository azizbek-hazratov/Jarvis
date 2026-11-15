import sys
sys.path.insert(0, '.')
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/results?search_query=Jaloliddin+Ahmadaliyev+Biromir", wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(4000)

# birinchi video natijasini bosish
video = page.query_selector("ytd-video-renderer a#video-title")
if video:
    title = video.get_attribute("title")
    video.click()
    page.wait_for_timeout(5000)
    print(f"OYNATILMOQDA: {title}")
    print(f"URL: {page.url}")
else:
    print("Video topilmadi, sahifa holati:")
    print(page.title())

# ctx.close() qilmaymiz - oyna ochiq qolsin, qo'shiq davom etsin
