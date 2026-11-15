# -*- coding: utf-8 -*-
"""Jarvis o'z-o'zini tekshiruvi: tezlik, aniqlik, sifat.
Mijoz oldidagi demodan oldin asosiy vositalarni sinaydi."""
import sys, time, json, os, subprocess, traceback

sys.stdout.reconfigure(encoding="utf-8")
natija = {"vaqt": time.strftime("%Y-%m-%d %H:%M:%S"), "testlar": []}

def test(nom, fn):
    t0 = time.time()
    try:
        ok, tafsilot = fn()
    except Exception as e:
        ok, tafsilot = False, f"XATO: {e}\n{traceback.format_exc()[-500:]}"
    dt = round(time.time() - t0, 3)
    natija["testlar"].append({"nom": nom, "ok": ok, "sekund": dt, "tafsilot": tafsilot})
    print(f"[{'OK' if ok else 'XATO'}] {nom} - {dt}s - {tafsilot}")

# 1. Fayl yozish/o'qish (utf-8, o'zbekcha)
def t_fayl():
    p = "C:/Users/Dell/jarvis/_test_ozbekcha.txt"
    matn = "Salom, o'zbekcha matn: g'oz, sh, ch, oʻ ✅"
    with open(p, "w", encoding="utf-8") as f:
        f.write(matn)
    with open(p, "r", encoding="utf-8") as f:
        oqilgan = f.read()
    os.remove(p)
    return (oqilgan == matn), "mos" if oqilgan == matn else f"mos emas: {oqilgan!r}"
test("Fayl yozish/o'qish (UTF-8)", t_fayl)

# 2. Excel (openpyxl)
def t_excel():
    import openpyxl
    p = "C:/Users/Dell/jarvis/_test.xlsx"
    wb = openpyxl.Workbook(); ws = wb.active
    ws["A1"] = "Test"; ws["B1"] = 12345
    wb.save(p)
    wb2 = openpyxl.load_workbook(p)
    v = wb2.active["B1"].value
    os.remove(p)
    return v == 12345, f"o'qilgan qiymat: {v}"
test("Excel (openpyxl) yozish/o'qish", t_excel)

# 3. Word (python-docx)
def t_docx():
    from docx import Document
    p = "C:/Users/Dell/jarvis/_test.docx"
    d = Document(); d.add_paragraph("Sinov matni")
    d.save(p)
    d2 = Document(p)
    txt = d2.paragraphs[0].text
    os.remove(p)
    return txt == "Sinov matni", f"o'qilgan: {txt}"
test("Word (python-docx) yozish/o'qish", t_docx)

# 4. PDF o'qish kutubxonasi mavjudligi
def t_pdf():
    import pdfplumber
    return True, f"pdfplumber versiyasi mavjud"
test("PDF (pdfplumber) import", t_pdf)

# 5. Bash/subprocess tezligi
def t_bash():
    r = subprocess.run(["cmd", "/c", "echo test"], capture_output=True, text=True, timeout=10)
    return r.returncode == 0, f"chiqish: {r.stdout.strip()}"
test("Buyruq bajarish (subprocess)", t_bash)

# 6. Internet ulanish
def t_internet():
    import urllib.request
    r = urllib.request.urlopen("https://www.google.com", timeout=5)
    return r.status == 200, f"status: {r.status}"
test("Internet ulanish", t_internet)

# 7. config.py kalitlari mavjudligi (qiymatini chiqarmasdan)
def t_config():
    sys.path.insert(0, "C:/Users/Dell/jarvis")
    import config
    kerakli = ["TELEGRAM_TOKEN", "OWNER_ID"]
    mavjud = [k for k in kerakli if hasattr(config, k) and getattr(config, k)]
    yoq = [k for k in kerakli if k not in mavjud]
    return len(yoq) == 0, f"mavjud: {mavjud}, yo'q: {yoq}"
test("config.py kalitlari", t_config)

# 8. Playwright (brauzer) importi
def t_playwright():
    from playwright.sync_api import sync_playwright
    return True, "playwright import OK"
test("Playwright import", t_playwright)

# 9. Telethon (userbot) importi
def t_telethon():
    import telethon
    return True, "telethon import OK"
test("Telethon import", t_telethon)

# 10. Xotira fayllari o'qilishi (2026-09-12: loyihalar.md -> indeks.md + loyihalar/ papka)
def t_xotira():
    fayllar = ["profil.md", "indeks.md", "vazifalar.md", "eslatmalar.md"]
    yo_q = [f for f in fayllar if not os.path.exists(f"C:/Users/Dell/jarvis/xotira/{f}")]
    if not os.path.isdir("C:/Users/Dell/jarvis/xotira/loyihalar"):
        yo_q.append("loyihalar/ (papka)")
    return len(yo_q) == 0, f"yo'q fayllar: {yo_q}" if yo_q else "hammasi mavjud"
test("Xotira fayllari mavjudligi", t_xotira)

jami = len(natija["testlar"])
muvaffaqiyatli = sum(1 for t in natija["testlar"] if t["ok"])
umumiy_vaqt = round(sum(t["sekund"] for t in natija["testlar"]), 3)
natija["xulosa"] = {"jami": jami, "muvaffaqiyatli": muvaffaqiyatli, "umumiy_vaqt_sekund": umumiy_vaqt}

with open("C:/Users/Dell/jarvis/_ozini_tekshir_natija.json", "w", encoding="utf-8") as f:
    json.dump(natija, f, ensure_ascii=False, indent=2)

print(f"\nJAMI: {muvaffaqiyatli}/{jami} muvaffaqiyatli, umumiy vaqt: {umumiy_vaqt}s")
