import sys
sys.path.insert(0, r"C:\Users\Dell\jarvis")
from jarvis_brauzer import ochish
import time

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/results?search_query=medina", wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(3000)
print("OCHILDI:", page.url, page.title())
# Oynani ochiq qoldirish uchun jarayonni tirik ushlab turamiz
time.sleep(3600)
