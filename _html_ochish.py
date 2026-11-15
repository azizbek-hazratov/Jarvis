import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.new_page()
page.goto("file:///C:/Users/Dell/jarvis/_bem_baraka.html", wait_until="domcontentloaded", timeout=30000)
print("OCHILDI:", page.title())
page.bring_to_front()
time.sleep(3600)
