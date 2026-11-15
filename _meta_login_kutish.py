# -*- coding: utf-8 -*-
"""Bir martalik yordamchi skript: ko'rinadigan brauzer ochadi, Azizbek Facebook/Meta
hisobiga qo'lda kirishini kutadi (URL o'zgarishini kuzatib), login bo'lgach
avtomatik yopadi (sessiya jarvis_brauzer.py profiliga saqlanadi)."""
import sys
from jarvis_brauzer import ochish

URL = "https://developers.facebook.com/apps/1096152019653495/"

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto(URL, wait_until="domcontentloaded")
print("Brauzer ochildi, login kutilmoqda...", flush=True)

max_urinish = 200  # ~200*3s = 10 daqiqa
muvaffaqiyat = False
for i in range(max_urinish):
    page.wait_for_timeout(3000)
    joriy = page.url
    if "loginpage" not in joriy and "login.php" not in joriy and "developers.facebook.com" in joriy:
        muvaffaqiyat = True
        break
    print(f"[{i}] hali login sahifasida: {joriy}", flush=True)

if muvaffaqiyat:
    print(f"LOGIN_OK: {page.url}", flush=True)
else:
    print(f"LOGIN_TIMEOUT: {page.url}", flush=True)

page.wait_for_timeout(1500)
ctx.close()
pw.stop()
print("Brauzer yopildi, sessiya saqlandi.", flush=True)
