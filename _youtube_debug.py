import sys
sys.path.insert(0, '.')
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/results?search_query=Jaloliddin+Ahmadaliyev+Biromir", wait_until="load", timeout=60000)
page.wait_for_timeout(5000)
print("TITLE:", page.title())
print("URL:", page.url)
page.screenshot(path="_yt_debug.png")
