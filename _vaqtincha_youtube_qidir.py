import sys
sys.path.insert(0, r"C:\Users\Dell\jarvis")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/results?search_query=Madina", wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(3000)
print(f"URL: {page.url}")
print(f"Sarlavha: {page.title()}")
# Kontekst/brauzerni ATAYLAB yopmaymiz — oyna ochiq qolishi uchun
# (bu python jarayoni tugasa ham, chrome alohida process sifatida ochiq qoladi)
