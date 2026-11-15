import sys
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/results?search_query=Ulug%27bek+Yo%27lchiyev+eng+yaxshi+qoshiqlari", wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(2500)
try:
    video = page.locator("ytd-video-renderer a#video-title").first
    href = video.get_attribute("href")
    title = video.inner_text()
    print("TOPILDI:", title, href)
    page.goto("https://www.youtube.com" + href, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    print("OCHILDI:", page.url, page.title())
except Exception as e:
    print("XATO:", e)
