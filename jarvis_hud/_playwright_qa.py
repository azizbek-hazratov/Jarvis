# -*- coding: utf-8 -*-
"""Yakuniy imtihon -- barcha savol/topshiriq/majlis stsenariylarini HAQIQIY
foydalanuvchi kabi panel orqali (Playwright) sinaydi, vaqtini o'lchaydi,
natijalarni JSON'ga yozadi (keyin hisobot jadvaliga ishlatiladi)."""
import json
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
URL = "http://localhost:8080/jamoa.html"
natijalar = []
console_errors = []


def savol_sina(page, matn, izoh=""):
    t0 = time.time()
    page.fill("#soraliqInput", matn)
    page.click("#soraliqBtn")
    page.wait_for_selector("#soraliqBtn:not([disabled])", timeout=90000)
    page.wait_for_timeout(400)
    ekran = page.inner_text("#spTxt")
    who = page.inner_text("#spWho")
    t1 = time.time()
    natijalar.append({"savol": matn, "izoh": izoh, "javob": ekran, "gapiruvchi": who, "soniya": round(t1 - t0, 1)})
    print(f"[{round(t1-t0,1)}s] {matn!r} -> ({who}) {ekran[:120]!r}")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()
        page.on("console", lambda m: console_errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"[pageerror] {e}"))
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        savollar = [
            ("Nozima, Orzu'da kim to'lamagan?", "real ism-ro'yxat, guruhlar bo'yicha"),
            ("Samandar, bugun nechta lid keldi?", "real lid soni"),
            ("Sardor, zaxira holati qanday?", "real backup holati"),
            ("Bekzod, botlar ishlayaptimi?", "real bot holati"),
            ("Malika, mijozlar nima so'radi?", "real son, halol javob (matn saqlanmaydi)"),
            ("Samandar, Grampus'da nechta faol sportchi bor?", "Nozimaga yo'naltirilishi kerak"),
            ("Nozima, kecha Jet Cafe'da nechta kofe sotildi?", "ma'lumot yo'q bo'lishi kerak"),
            ("Kamola, bu hafta nima post qilamiz?", "real qoralama reja"),
        ]
        for matn, izoh in savollar:
            savol_sina(page, matn, izoh)

        # ---- Topshiriqlar (panel formasi orqali) ----
        print("\n--- Topshiriq: Sardor SINOV_ zaxira hisobotini tayyorla (oqish) ---")
        page.select_option("#cmdWho", "sardor")
        page.fill("#cmdTxt", "SINOV_2 zaxira hisobotini tayyorla")
        page.click("#cmd .send")
        page.wait_for_timeout(4000)

        print("--- Topshiriq: Samandar SINOV_ Orzu ota-onalariga eslatma yubor (yozish, TASDIQLANMAYDI) ---")
        page.select_option("#cmdWho", "samandar")
        page.fill("#cmdTxt", "SINOV_2 Orzu ota-onalariga eslatma yubor")
        page.click("#cmd .send")
        page.wait_for_timeout(2500)

        tq_html = page.inner_text("#topshiriqlarJadval")
        natijalar.append({"savol": "[Topshiriqlar jadvali holati]", "izoh": "", "javob": tq_html[:800], "gapiruvchi": "", "soniya": 0})

        # ---- Jonli majlis ----
        print("\n--- Jonli majlis: Grampus'da o'quvchilarni qanday ko'paytiramiz? ---")
        t0 = time.time()
        page.fill("#majlisMavzu", "Grampus'da o'quvchilarni qanday ko'paytiramiz?")
        page.click("#majlisBoshlashBtn")
        page.wait_for_selector("#majlisNatija:not([hidden])", timeout=330000)
        t1 = time.time()
        gtoyalar_matn = page.inner_text("#majlisGtoyalar")
        natijalar.append({"savol": "Majlis: Grampus'da o'quvchilarni qanday ko'paytiramiz?", "izoh": "jonli AI majlis", "javob": gtoyalar_matn[:600], "gapiruvchi": "", "soniya": round(t1 - t0, 1)})
        print(f"[{round(t1-t0,1)}s] majlis tugadi, g'oyalar: {gtoyalar_matn[:200]!r}")

        page.screenshot(path=str(BASE / "_sinov_1920_majlis2.png"), full_page=True)

        print("--- Majlis g'oyasidan 'Topshiriq qilish' ---")
        before_count = len(page.query_selector_all(".topshiriq-row"))
        page.click('[data-gtoya="0"]')
        page.wait_for_timeout(2500)
        page.evaluate("loadJamoa()")
        page.wait_for_timeout(2000)
        after_html = page.inner_text("#topshiriqlarJadval")
        natijalar.append({"savol": "[Majlis g'oyasi -> Topshiriq qilish natijasi]", "izoh": "", "javob": after_html[:800], "gapiruvchi": "", "soniya": 0})

        # ---- Yakuniy skrinshotlar ----
        page.screenshot(path=str(BASE / "_sinov_1920_yakuniy.png"), full_page=True)
        ctx.close()

        ctx2 = browser.new_context(viewport={"width": 375, "height": 812})
        page2 = ctx2.new_page()
        page2.on("console", lambda m: console_errors.append(f"[mobil:{m.type}] {m.text}") if m.type == "error" else None)
        page2.goto(URL, wait_until="networkidle", timeout=30000)
        page2.wait_for_timeout(1500)
        page2.screenshot(path=str(BASE / "_sinov_375_yakuniy.png"), full_page=True)
        ctx2.close()
        browser.close()

    (BASE / "_sinov_qa_natija.json").write_text(json.dumps(natijalar, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== KONSOL XATOLARI ===")
    print(console_errors or "(yo'q)")


if __name__ == "__main__":
    run()
