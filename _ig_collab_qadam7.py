import sys, time
sys.path.insert(0, ".")
from jarvis_brauzer import ochish

pw, ctx = ochish(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
page.wait_for_timeout(3000)
page.mouse.click(36, 502)
page.wait_for_timeout(1000)
page.get_by_text("Публикация", exact=True).first.click()
page.wait_for_timeout(1500)

with page.expect_file_chooser() as fc_info:
    page.get_by_text("Выбрать на компьютере").click()
fc = fc_info.value
fc.set_files(r"C:\Users\Dell\jarvis\kiruvchi\IMG_0251.PNG")
page.wait_for_timeout(2500)

page.get_by_text("Далее", exact=True).click()
page.wait_for_timeout(1500)
page.get_by_text("Далее", exact=True).click()
page.wait_for_timeout(1500)

page.mouse.click(975, 471)
page.wait_for_timeout(1500)
page.screenshot(path="_ig_qadam_8_soavtor.png")
print("soavtor screen shot done")

page.keyboard.type("sohibsattorovich", delay=80)
page.wait_for_timeout(1800)
page.screenshot(path="_ig_qadam_9_soavtor_qidiruv.png")
print("qidiruv shot done")

# Postni yubormasdan yopamiz -- orqaga qaytish tugmasi (yuqori chapdagi strelka)
page.mouse.click(230, 109)
page.wait_for_timeout(700)
page.mouse.click(230, 109)
page.wait_for_timeout(700)
page.mouse.click(230, 109)
page.wait_for_timeout(700)
page.mouse.click(1397, 27)
page.wait_for_timeout(1000)
page.screenshot(path="_ig_qadam_10_yopildi.png")
print("yopildi")
ctx.close()
pw.stop()
