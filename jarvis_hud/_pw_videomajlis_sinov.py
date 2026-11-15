# -*- coding: utf-8 -*-
"""Video-majlis UI imtihoni (2026-09-29) — jamoa.html'dagi yangi 6-oynali
video-call grid, to'liq ekran qo'ng'iroq oynasi va majlis-ramka rejimini
ESKI (hozir ishlab turgan) bridge bilan sinaydi. 3 ta skrinshot oladi,
brauzer konsol xatolarini yig'adi, va ask+speak (savol->javob->ovoz)
kechikishini HAQIQIY o'lchaydi (performance.now() farqi bilan).
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
URL = "http://localhost:8080/jamoa.html"

console_errors = []
page_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # ---- 1) GRID: 6 kartochka bormi? ----
    grid_count = page.eval_on_selector_all("#vcallGrid .vcall-card", "els => els.length")
    grid_ids = page.eval_on_selector_all("#vcallGrid .vcall-card", "els => els.map(e => e.dataset.id)")
    print("GRID_COUNT:", grid_count, grid_ids)
    page.screenshot(path=str(BASE / "_videomajlis_grid.png"), full_page=True)

    # ---- 2) QO'NG'IROQ OYNASI: ochish, ovoz+halqa+kechikish, yopish ----
    page.click('#vcallGrid [data-vcall="samandar"]')
    page.wait_for_selector("#callwin:not([hidden])", timeout=5000)
    page.wait_for_timeout(400)

    speaking_class_during = page.evaluate(
        """
        async () => {
          const id = currentCallId;
          const t0 = performance.now();
          const sResp = await fetch(BRIDGE + '/jamoa/savol', {
            method:'POST', headers:{...HUD_AUTH_HEADER,'Content-Type':'application/json'},
            body: JSON.stringify({xodim:id, matn:'Bugun nechta suhbat bo\\'ldi?'}),
          });
          const sData = await sResp.json();
          const javob = sData.javob || 'Sinov javobi, ovoz tekshiruvi uchun.';
          vcallSuhbatEkla(id, javob);
          callwinTranscriptEkla(id, javob);
          window._callP = callwinJavobniAytish(id, javob, t0);  // await QILMAYMIZ -- sinxron qism darhol ishga tushadi
          await new Promise(r => setTimeout(r, 50));
          return document.getElementById('callwinAvatarWrap').classList.contains('speaking');
        }
        """
    )
    print("SPEAKING_CLASS_DURING_PLAYBACK:", speaking_class_during)
    page.screenshot(path=str(BASE / "_videomajlis_qongiroq.png"), full_page=True)

    latency_text, speaking_class_after = page.evaluate(
        """
        async () => {
          await window._callP;
          return [document.getElementById('callwinLatency').textContent,
                  document.getElementById('callwinAvatarWrap').classList.contains('speaking')];
        }
        """
    )
    print("LATENCY_TEXT:", latency_text, "SPEAKING_CLASS_AFTER:", speaking_class_after)

    # Yopish
    page.click("#callwinEnd")
    page.wait_for_function("document.getElementById('callwin').hidden === true", timeout=5000)

    # ---- 3) MAJLIS: saqlangan ("oxirgi") majlisni ijro etib, aktiv ramka va
    #    Natijalar tabini tekshiramiz. ----
    page.click("#majlisOxirgiBtn")
    # Ijro davomida gridda kamida bitta .vcall-card.active paydo bo'lishini kutamiz.
    page.wait_for_selector(".vcall-card.active", timeout=60000)
    active_id = page.eval_on_selector(".vcall-card.active", "el => el.dataset.id")
    print("ACTIVE_DURING_MAJLIS:", active_id)
    page.screenshot(path=str(BASE / "_videomajlis_majlis.png"), full_page=True)

    page.wait_for_selector("#majlisNatija:not([hidden])", timeout=240000)
    page.wait_for_timeout(1000)
    natija_html_len = page.eval_on_selector("#vcallNatijaList", "el => el.innerHTML.length")
    natija_tab_visible = page.eval_on_selector("#vcallNatijaPanel", "el => !el.hidden")
    print("NATIJA_HTML_LEN:", natija_html_len, "TAB_VISIBLE:", natija_tab_visible)

    result = {
        "grid_count": grid_count,
        "grid_ids": grid_ids,
        "speaking_class_during_playback": speaking_class_during,
        "speaking_class_after_playback": speaking_class_after,
        "latency_text": latency_text,
        "active_during_majlis": active_id,
        "natija_html_len": natija_html_len,
        "natija_tab_visible": natija_tab_visible,
        "console_errors": console_errors,
        "page_errors": page_errors,
    }
    (BASE / "_pw_videomajlis_natija.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    ctx.close()
    browser.close()
