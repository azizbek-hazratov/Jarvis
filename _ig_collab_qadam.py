import sys, time
sys.path.insert(0, ".")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
page.wait_for_timeout(3000)

shots = []

def shot(name):
    p = f"_ig_qadam_{len(shots)+1}_{name}.png"
    page.screenshot(path=p)
    shots.append(p)
    print("SHOT:", p)

shot("boshlangich")

# "Create" tugmasini topish
try:
    create_btn = page.get_by_role("link", name="New post").first
    if create_btn.count() == 0:
        create_btn = page.locator("svg[aria-label='New post']").first.locator("xpath=ancestor::a | ancestor::div[@role='button']").first
    create_btn.click(timeout=5000)
except Exception as e:
    print("Create tugma xato:", e)

page.wait_for_timeout(1500)
shot("create_menu")
