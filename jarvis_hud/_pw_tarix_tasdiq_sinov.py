# -*- coding: utf-8 -*-
"""2026-09-29 (backend tuzatishi javobida) — qo'shimcha sinov:
1) Xotira izolatsiyasi: Kamolaga maxfiy so'z aytiladi, keyin Nozimaga
   boshqa savol beriladi -- Nozima javobida Kamolaning maxfiy so'zi
   BO'LMASLIGI kerak (avvalgi "doimiy sessiya" bugi tuzatilganini tasdiqlaydi).
2) Qo'ng'iroq-ichi Tasdiqlash/Bekor UI ("yozish" turi javobida).
Ikkalasi ham mikrofon/STT o'rniga to'g'ridan-to'g'ri production
funksiyalarini (vcallSuhbatEkla/callwinJavobniAytish/callwinTasdiqKorsat)
chaqirib sinaydi -- headless muhitda haqiqiy mikrofon yo'qligi sababli.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
URL = "http://localhost:8080/jamoa.html"

JS_SAVOL = """
async (args) => {
  const { xodim, matn } = args;
  const sResp = await fetch(BRIDGE + '/jamoa/savol', {
    method:'POST', headers:{...HUD_AUTH_HEADER,'Content-Type':'application/json'},
    body: JSON.stringify({xodim, matn, tarix: callHistory.slice(-6)}),
  });
  const sData = await sResp.json();
  if (sData.turi === 'yozish' && sData.id){
    vcallSuhbatEkla(xodim, sData.javob); callwinTranscriptEkla(xodim, sData.javob);
    callwinTasdiqKorsat(xodim, sData.id, matn);  // await qilinmaydi -- tugma bosilguncha ochiq turadi
    return {turi: sData.turi, javob: sData.javob, id: sData.id};
  } else {
    const javob = sData.javob || 'javob yoq';
    vcallSuhbatEkla(xodim, javob); callwinTranscriptEkla(xodim, javob);
    callHistory.push({savol: matn, javob});
    return {turi: sData.turi, javob};
  }
}
"""

console_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    import time

    # ---- A) Xotira izolatsiyasi (haqiqiy AI-yo'nalgan savol, tarix bo'sh) ----
    t_a0 = time.monotonic()
    page.click('#vcallGrid [data-vcall="kamola"]')
    page.wait_for_selector("#callwin:not([hidden])", timeout=5000)
    r1 = page.evaluate(JS_SAVOL, {
        "xodim": "kamola",
        "matn": "Sen eng yoqtirgan mevang behi ekanini eslab qolasanmi? Agar shunday bosa, javobingda behi sozini ishlat.",
    })
    t_a1 = time.monotonic()
    print("KAMOLA_JAVOB:", json.dumps(r1, ensure_ascii=False))
    page.click("#callwinEnd")
    page.wait_for_function("document.getElementById('callwin').hidden === true", timeout=5000)

    page.click('#vcallGrid [data-vcall="nozima"]')
    page.wait_for_selector("#callwin:not([hidden])", timeout=5000)
    r2 = page.evaluate(JS_SAVOL, {"xodim": "nozima", "matn": "Sizningcha jamoa ruhi uchun eng muhim narsa nima, bitta gap bilan ayt?"})
    t_a2 = time.monotonic()
    print("NOZIMA_JAVOB:", json.dumps(r2, ensure_ascii=False))
    leaked = "behi" in (r2.get("javob") or "").lower() or "kamola" in (r2.get("javob") or "").lower()
    print("XOTIRA_ARALASHDIMI (kutilgan False):", leaked)
    page.click("#callwinEnd")
    page.wait_for_function("document.getElementById('callwin').hidden === true", timeout=5000)

    # ---- B) "Yozish" turi -- avval BEKOR yo'li (tez, deterministik) ----
    page.click('#vcallGrid [data-vcall="nozima"]')
    page.wait_for_selector("#callwin:not([hidden])", timeout=5000)
    r3 = page.evaluate(JS_SAVOL, {"xodim": "nozima", "matn": "Menga tabrik xati yoz"})
    print("YOZISH_JAVOB_1(bekor uchun):", json.dumps(r3, ensure_ascii=False))
    page.wait_for_selector("#callwinTasdiq:not([hidden])", timeout=5000)
    page.screenshot(path=str(BASE / "_videomajlis_tasdiq.png"))
    page.click("#callwinBekorBtn")
    page.wait_for_function("document.getElementById('callwinTasdiq').hidden === true", timeout=5000)
    page.wait_for_timeout(600)
    transcript_after_bekor = page.eval_on_selector("#callwinTranscript", "el => el.innerText")
    print("BEKOR_TRANSKRIPT_OXIRI:", transcript_after_bekor[-300:])
    page.click("#callwinEnd")
    page.wait_for_function("document.getElementById('callwin').hidden === true", timeout=5000)

    # ---- C) TASDIQLASH (haqiqiy ijro) yo'li -- 2026-09-29 Azizbek buyrug'i
    # bilan HOZIRCHA TO'XTATILGAN (bridge SINOV_REJIM=1 bilan qayta ishga
    # tushirilguncha) -- shu sababli bu bo'lim ATAYLAB o'chirilgan/sinalmagan.

    result = {
        "kamola_javob": r1, "kamola_kechikish_s": round(t_a1 - t_a0, 1),
        "nozima_javob": r2, "nozima_kechikish_s": round(t_a2 - t_a1, 1),
        "xotira_aralashdimi": leaked,
        "yozish_javob_bekor": r3, "bekor_transkript_oxiri": transcript_after_bekor[-300:],
        "tasdiqlash_ijro_sinovi": "SINALMADI (Azizbek so'roviga ko'ra to'xtatilgan, SINOV_REJIM=1 qayta ishga tushirilguncha)",
        "console_errors": console_errors,
    }
    (BASE / "_pw_tarix_tasdiq_natija.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CONSOLE_ERRORS:", console_errors)
    ctx.close()
    browser.close()
