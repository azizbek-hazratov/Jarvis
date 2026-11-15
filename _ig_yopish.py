import sys, time
sys.path.insert(0, ".")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.instagram.com/azizbekhazratov.ai/", wait_until="domcontentloaded")
page.wait_for_timeout(2500)
page.screenshot(path="_ig_tekshir_profil.png")
print("done - hech qanday post yuborilmadi, faqat sahifa yangilandi")
ctx.close()
pw.stop()
