import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.youtube.com/results?search_query=Ulug%27bek+Elchiyev+qo%27shiq", wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(2500)

video = page.locator("a#video-title").first
video.wait_for(timeout=10000)
sarlavha = video.get_attribute("title") or video.inner_text()
video.click()
page.wait_for_timeout(4000)

# ovoz balandligini tekshirish/tuzatish (mute bo'lsa ochish)
try:
    page.evaluate("""() => {
        const v = document.querySelector('video');
        if (v) { v.muted = false; v.volume = 1; v.play(); }
    }""")
except Exception:
    pass

print("QO'YILDI:", sarlavha)
print("URL:", page.url)
sys.stdout.flush()

# Brauzer ochiq qolishi uchun jarayonni tirik saqlaymiz (30 daqiqa)
time.sleep(1800)
