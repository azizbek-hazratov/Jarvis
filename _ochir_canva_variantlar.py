import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from jarvis_brauzer import ochish

urls = [
    "https://www.canva.com/d/JxU0ZHqAS4usoU_",
    "https://www.canva.com/d/xj1pXtdy77Xt7ar",
    "https://www.canva.com/d/dqqdEewTA1lrQnr",
    "https://www.canva.com/d/jBdV4kDtpxvqKdd",
]

pw, ctx = ochish(headless=False)
first = ctx.pages[0] if ctx.pages else ctx.new_page()
first.goto(urls[0], wait_until="domcontentloaded")
for u in urls[1:]:
    p = ctx.new_page()
    p.goto(u, wait_until="domcontentloaded")

print("4 ta variant brauzerda ochildi.")
import time
time.sleep(3600)
