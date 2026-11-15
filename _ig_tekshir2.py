import sys
sys.path.insert(0, ".")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.instagram.com/azizbekhazratov.ai/", wait_until="networkidle")
page.wait_for_timeout(2000)
page.mouse.wheel(0, 0)
page.wait_for_timeout(1000)
page.screenshot(path="_ig_tekshir2.png")
ctx.close()
pw.stop()
