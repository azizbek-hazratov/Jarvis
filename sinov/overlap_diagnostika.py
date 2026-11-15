import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:8080/", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1000)

    def olchov(izoh):
        pl = page.locator(".panel-left").bounding_box()
        pj = page.locator(".panel-jarayonlar").bounding_box()
        overlap = None
        if pl and pj:
            overlap = not (pl["y"] + pl["height"] <= pj["y"] or pj["y"] + pj["height"] <= pl["y"])
        print(f"{izoh}: panel-left height={pl['height']:.0f}, y={pl['y']:.0f}-{pl['y']+pl['height']:.0f} | panel-jarayonlar y={pj['y']:.0f}-{pj['y']+pj['height']:.0f} | OVERLAP={overlap}")

    olchov("HOZIRGI (xavfsizlik jurnali BOR)")

    # Xavfsizlik jurnali bo'limini (divider+h3+list) vaqtinchalik DOM'dan olib tashlaymiz
    page.evaluate("""
        () => {
            const el = document.getElementById('xavfsizlikJurnali');
            if (el) {
                const h3 = el.previousElementSibling; // <h3>XAVFSIZLIK JURNALI</h3>
                const divider = h3 ? h3.previousElementSibling : null; // <div class="divider">
                el.remove();
                if (h3) h3.remove();
                if (divider && divider.classList.contains('divider')) divider.remove();
            }
        }
    """)
    page.wait_for_timeout(300)
    olchov("XAVFSIZLIK JURNALI OLIB TASHLANGANDA (taxminiy #7'dan OLDINGI holat)")

    browser.close()
