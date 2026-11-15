"""
JARVIS DESKTOP BOSHQARUVI — Bosqich 2 (Windows UI Automation, `pywinauto`).

Brauzerdan tashqaridagi (Explorer, Notepad, Excel va h.k.) dasturlarni
sichqoncha/klaviatura orqali boshqarish uchun. `jarvis_brauzer.py` bilan
BIR XIL xavfsizlik falsafasi: harakat-funksiyalari (`xavfsiz_bos`,
`xavfsiz_toldir`) xom pywinauto chaqiruvlari o'rniga ISHLATILISHI SHART,
chunki CAPTCHA/to'lov/hisob-yaratish/parol bloklari FAQAT shu funksiyalar
ichida ishlaydi. Kalit-so'z ro'yxatlari `jarvis_brauzer_xavfsizlik.py`dan
qayta ishlatiladi (bitta joyda saqlanadi, ikki marta yozilmaydi).

Azizbek tasdiqlagan qoidalar (2026-09-21, brauzer bosqichi bilan bir xil):
(a) CAPTCHA — hech qachon hal qilishga urinilmaydi, darhol to'xtaydi;
(b) "to'lov" bloki — har qanday pul o'tkazmasi/obuna/kripto, bypass YO'Q;
(c) "hisob yaratishni yakunlash" — yakuniy tugma har safar aniq tasdiq
    talab qiladi (`hisob_yaratish_tasdiqlandi=True`, faqat Jarvis real
    tasdiqdan keyin qo'lda beradi).
Qo'shimcha (desktop-xos): parol/PIN maydoniga HECH QACHON yozilmaydi —
avtomatika-ID/nom bo'yicha kalit-so'z tekshiruvi (brauzerdagi kabi).

Hozircha FAQAT sinovdan o'tgan: dastur ochish, oyna/element matnini
o'qish, matn yozish (saqlamasdan). Fayl saqlash/o'chirish, Excel/real
hujjatlarga tegish HALI SINALMAGAN — alohida, Azizbek tasdig'i bilan.
"""

import sys
import time

from pywinauto import Application

import jarvis_brauzer_xavfsizlik as xavfsizlik
from jarvis_brauzer_xavfsizlik import DesktopXavfsizlikXatosi


def ochish(dastur_buyrugi: str, *, kutish: float = 1.5) -> Application:
    """Dasturni ishga tushiradi (masalan 'notepad.exe') va Application
    obyektini qaytaradi. `kutish` — oyna paydo bo'lishi uchun soddagina
    pauza (pywinauto ba'zan process ID borligicha oynani topa olmaydi)."""
    app = Application(backend="uia").start(dastur_buyrugi)
    time.sleep(kutish)
    return app


def bosh_oynani_top(app: Application, *, oyna_sarlavha_re: str | None = None, timeout: float = 10):
    """Dasturning eng yuqori (asosiy) oynasini qaytaradi.

    Ba'zi zamonaviy Windows dasturlari (masalan Win11 Notepad) PAKETLANGAN
    (packaged/MSIX) bo'lib, `Application.start()` orqali ishga tushirilgan
    process haqiqiy oynani o'zi egallamaydi (haqiqiy oyna boshqa host
    process'da ochiladi) — shu sabab avval oddiy `app.top_window()`
    sinaladi, muvaffaqiyatsiz bo'lsa Desktop darajasida sarlavha bo'yicha
    qidiriladi (`oyna_sarlavha_re` berilmasa `.*` — birinchi ko'ringan
    oyna olinadi, aniqroq moslash uchun chaqiruvchi nom bersin)."""
    try:
        oyna = app.top_window()
        oyna.wait("exists enabled visible", timeout=timeout)
        return oyna
    except Exception:
        pass

    from pywinauto import Desktop

    naqsh = oyna_sarlavha_re or ".*"
    muddat = time.time() + timeout
    while time.time() < muddat:
        try:
            for w in Desktop(backend="uia").windows(title_re=naqsh, visible_only=True):
                try:
                    if w.is_visible():
                        return w
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError(
        "Oyna topilmadi — dastur paketlangan (packaged) bo'lishi mumkin, "
        "aniqroq `oyna_sarlavha_re` bilan qayta urining."
    )


def oyna_matnini_ol(oyna) -> str:
    """Oynadagi BARCHA elementlarning ko'rinadigan matnini bitta satrga
    yig'ib beradi — CAPTCHA/to'lov/hisob-yaratish kalit-so'z tekshiruvi
    shu matn ustida ishlaydi (brauzerdagi `page.inner_text("body")`ga
    desktop ekvivalenti)."""
    boluklar = []
    try:
        sarlavha = oyna.window_text()
        if sarlavha:
            boluklar.append(sarlavha)
    except Exception:
        pass
    try:
        for elem in oyna.descendants():
            try:
                matn = elem.window_text()
                if matn:
                    boluklar.append(matn)
            except Exception:
                continue
    except Exception:
        pass
    return " ".join(boluklar)


def captchani_tekshir_va_toxtat(oyna):
    """Oynada CAPTCHA belgisi bo'lsa, DARHOL `DesktopXavfsizlikXatosi`
    ko'taradi — hech qachon "hal qilishga" urinilmaydi. `xavfsiz_bos`/
    `xavfsiz_toldir` buni AVTOMATIK ham qiladi."""
    matn = oyna_matnini_ol(oyna)
    izoh = xavfsizlik.captcha_holatini_tekshir_matn(matn)
    if izoh:
        raise DesktopXavfsizlikXatosi(
            f"CAPTCHA aniqlandi ({izoh}) — hal qilishga URINILMADI, "
            "to'xtatildi. Azizbekka darhol xabar bering."
        )


def _tekshiriladigan_matn(control) -> str:
    try:
        matn = control.window_text() or ""
    except Exception:
        matn = ""
    try:
        avtomatika_id = control.element_info.automation_id or ""
    except Exception:
        avtomatika_id = ""
    return f"{matn} {avtomatika_id}".strip()


def _oyna_topib_captcha_tekshir(control):
    """Berilgan controldan asosiy oynani topib, CAPTCHA tekshiruvini
    ishga tushiradi. Oyna topilmasa (masalan duck-typed sinov obyekti)
    jim o'tkazib yuboradi — bu ixtiyoriy qo'shimcha qatlam, asosiy
    kalit-so'z tekshiruvini bloklamasligi kerak."""
    try:
        oyna = control.top_level_parent()
    except Exception:
        return
    try:
        captchani_tekshir_va_toxtat(oyna)
    except DesktopXavfsizlikXatosi:
        raise
    except Exception:
        pass


def xavfsiz_bos(control, *, izoh: str = "", hisob_yaratish_tasdiqlandi: bool = False) -> dict:
    """pywinauto orqali bosishning YAGONA tavsiya etiladigan yo'li —
    xavfsizlik qatlami (CAPTCHA/to'lov/hisob-yaratish) BILAN BIRGA.
    Xatti-harakat `jarvis_brauzer.xavfsiz_bos` bilan bir xil (qarang: shu
    fayl docstring'i), faqat manba HTML emas — control.window_text()/
    automation_id.

    Muvaffaqiyatda {"toifa", "matn", "izoh"} lug'atini qaytaradi."""
    _oyna_topib_captcha_tekshir(control)

    tekshiriladigan_matn = _tekshiriladigan_matn(control)
    toifa, kalit = xavfsizlik.harakat_toifasi(tekshiriladigan_matn)

    if toifa == "tolov":
        raise DesktopXavfsizlikXatosi(
            f"TO'LOV/PUL HARAKATI bloklandi (kalit so'z: '{kalit}', "
            f"element: '{tekshiriladigan_matn[:80]}'). Bu HECH QACHON "
            "avtomatik bosilmaydi — Azizbek o'zi bajarishi kerak."
        )
    if toifa == "hisob_yaratish" and not hisob_yaratish_tasdiqlandi:
        raise DesktopXavfsizlikXatosi(
            f"HISOB YARATISHNI YAKUNLASH bloklandi (kalit so'z: '{kalit}', "
            f"element: '{tekshiriladigan_matn[:80]}'). Bu tugmani bosishdan "
            "oldin Azizbekdan ANIQ tasdiq oling, keyin "
            "hisob_yaratish_tasdiqlandi=True bilan qayta chaqiring."
        )

    # Desktop-xos qo'shimcha qatlam (brauzer/Bosqich 1'ga tegilmadi):
    # FAYL SAQLASH/YOZISH tugmalari — bypass YO'Q, to'lov kabi qat'iy.
    # Sabab: hujjat-avtomatlash (Excel va h.k.) haqiqiy fayllarni
    # tasodifan/muddatidan oldin o'zgartirib qo'yishi mumkin.
    saqlash_kalit = xavfsizlik.saqlash_harakatimi(tekshiriladigan_matn)
    if saqlash_kalit:
        raise DesktopXavfsizlikXatosi(
            f"FAYL SAQLASH/YOZISH harakati bloklandi (kalit so'z: "
            f"'{saqlash_kalit}', element: '{tekshiriladigan_matn[:80]}'). "
            "Bu HECH QACHON avtomatik bosilmaydi — Azizbek o'zi bajarishi "
            "kerak (yoki hujjat maqsadli o'zgarishsiz yopilsin)."
        )

    control.click_input()
    return {"toifa": toifa, "matn": tekshiriladigan_matn, "izoh": izoh}


def xavfsiz_toldir(control, qiymat: str, *, izoh: str = "") -> dict:
    """pywinauto orqali matn kiritishning YAGONA tavsiya etiladigan yo'li.

    - Maydon parol/PIN/CVV/karta-raqami turidan bo'lsa (nom yoki
      avtomatika-ID'da kalit so'z topilsa): darhol to'xtaydi.
    - CAPTCHA aniqlansa: darhol to'xtaydi.
    - Aks holda oddiy `set_edit_text` qiladi."""
    tekshiriladigan_matn = _tekshiriladigan_matn(control)

    if xavfsizlik.maydon_parolmi(tekshiriladigan_matn):
        raise DesktopXavfsizlikXatosi(
            f"PAROL/PIN/karta-raqami turidagi maydonga yozish bloklandi "
            f"(element: '{tekshiriladigan_matn[:80]}'). Bu HECH QACHON "
            "avtomatik to'ldirilmaydi."
        )

    _oyna_topib_captcha_tekshir(control)

    # Ba'zi control turlari (masalan zamonaviy Notepad'ning "Document"
    # matn maydoni) klassik "Edit" emas — `set_edit_text` yo'q, shu
    # sabab avval shu tezroq yo'l sinaladi, bo'lmasa bosib-yozish bilan
    # (haqiqiy klaviatura hodisalari) orqaga qaytiladi.
    try:
        control.set_edit_text(qiymat)
    except AttributeError:
        control.click_input()
        control.type_keys(qiymat, with_spaces=True)
    return {"izoh": izoh, "element": tekshiriladigan_matn[:80]}


# ============================================================
# ELEKTRON JADVAL (Excel/LibreOffice Calc) — Bosqich 2 kengaytmasi (2026-09-21)
# ============================================================
# MUHIM: bu mashinada MS Excel O'RNATILMAGAN (Office 2013 ro'yxatdan
# o'tgan, lekin EXCEL.EXE fayli yo'q — buzilgan/qisman o'rnatish). Shu
# sabab LibreOffice Calc ishlatiladi (xavfsiz, bepul, xuddi shu .xlsx
# formatini ochadi). Funksiyalar dastur nomiga bog'liq emas — real MS
# Excel o'rnatilsa `dastur_yoli`ni almashtirish kifoya.
#
# XAVFSIZLIK QOIDASI (bu bo'lim uchun qat'iy, Azizbek 2026-09-21 talabi):
# ASL FAYLGA HECH QACHON TO'G'RIDAN-TO'G'RI TEGILMAYDI. `nusxada_och()`
# FAQAT nusxa yaratadi va O'SHA NUSXANI ochadi — asl fayl yo'lini ochish
# funksiyasiga ATAYLAB berish YO'LI YO'Q (parametr nomi ham buni aks
# ettiradi). Saqlash — yuqoridagi `xavfsiz_bos()`dagi SAQLASH bloki
# orqali ANIQ tasdiqsiz umuman mumkin emas; yopish esa HAR DOIM
# `nusxani_yop()` orqali majburiy process-kill bilan (hech qachon
# "Saqlash?" dialogiga duch kelmasdan).

import shutil
import uuid
from pathlib import Path

NUSXALAR_PAPKASI = Path(__file__).parent / "sinov" / "_edj_nusxalar"
LIBREOFFICE_YOLI = r"C:\Program Files\LibreOffice\program\soffice.exe"


def nusxada_och(asl_fayl_yoli: str, *, dastur_yoli: str = LIBREOFFICE_YOLI, timeout: float = 30):
    """Berilgan hujjatning NUSXASINI (`NUSXALAR_PAPKASI` ichida, tasodifiy
    nom bilan — asl nom bilan ATAYLAB bir xil emas, chalkashmasin) yaratadi
    va O'SHA NUSXANI ochadi. Asl fayl HECH QACHON ochilmaydi/o'zgartirilmaydi
    — bu funksiya orqali unga yo'l umuman yo'q.

    Qaytaradi: (oyna, nusxa_yoli, pid) — `pid` yopish uchun kerak (Win11'da
    ba'zi dasturlar paketlangan bo'lib, boshlang'ich process haqiqiy oyna
    process'i bilan bir xil bo'lmasligi mumkin, shuning uchun oyna orqali
    olingan pid ishonchli)."""
    asl = Path(asl_fayl_yoli)
    if not asl.is_file():
        raise FileNotFoundError(f"Asl fayl topilmadi: {asl_fayl_yoli}")

    NUSXALAR_PAPKASI.mkdir(parents=True, exist_ok=True)
    nusxa_yoli = NUSXALAR_PAPKASI / f"nusxa_{uuid.uuid4().hex[:8]}_{asl.name}"
    shutil.copy2(asl, nusxa_yoli)
    # O'zini-o'zi tekshirish: nusxa asl fayl bilan BIR XIL YO'L bo'lishi
    # MUTLAQO mumkin emas (aks holda keyingi yozish/saqlash-bloklari
    # asl faylni himoya qila olmay qoladi).
    if nusxa_yoli.resolve() == asl.resolve():
        raise RuntimeError("Xavfsizlik: nusxa yo'li asl fayl bilan bir xil chiqdi — to'xtatildi.")

    cmd = f'"{dastur_yoli}" --calc "{nusxa_yoli}"'
    Application(backend="uia").start(cmd)

    from pywinauto import Desktop

    oyna = None
    muddat = time.time() + timeout
    while time.time() < muddat and oyna is None:
        time.sleep(0.5)
        _tosiq_oynalarni_yop()  # Welcome/Document-Recovery to'siqlarini har aylanishda tozalab boradi
        for w in Desktop(backend="uia").windows(visible_only=True):
            try:
                if nusxa_yoli.stem in (w.window_text() or ""):
                    oyna = w
                    break
            except Exception:
                continue
    if oyna is None:
        raise RuntimeError(f"'{nusxa_yoli.name}' oynasi {timeout}s ichida topilmadi.")

    time.sleep(0.5)
    _tosiq_oynalarni_yop()  # hujjat yuklangandan keyin ham Welcome infobar chiqishi mumkin
    oyna.set_focus()
    time.sleep(0.3)
    return oyna, str(nusxa_yoli), oyna.process_id()


def _tosiq_oynalarni_yop():
    """LibreOffice ba'zan asosiy hujjat oynasidan OLDIN/ustida ikkita
    to'siq oyna chiqarishi mumkin, ikkalasi ham hujjat MAZMUNIGA aloqasi
    yo'q, faqat avtomatlashtirishga xalaqit beradi:
    1) "Добро пожаловать..." (Welcome) infobar — klaviatura fokusini
       tortib oladi, Name Box'ga yuborilgan tugmalar yo'qoladi.
    2) "Восстановление документа" (Document Recovery) — `nusxani_yop()`
       process-kill ishlatgani sabab (saqlash dialogisiz majburiy
       to'xtatish), LibreOffice buni "yiqilish" deb hisoblab KEYINGI
       ishga tushishda tiklash-master'ini ko'rsatadi. "Отклонить все"/
       "Discard All" bosiladi — HECH QANDAY tiklash/saqlash qilinmaydi,
       aksincha eski (chiqindi) holatni butunlay rad etadi. Bitta
       "supurish" — chaqiruvchi (odatda kutish tsikli ichida) o'zi
       qayta-qayta chaqiradi."""
    from pywinauto import Desktop
    import win32gui
    import win32con

    topildi = False
    for w in Desktop(backend="uia").windows():
        try:
            sarlavha = w.window_text() or ""
        except Exception:
            continue
        if "обро пожаловать" in sarlavha or "Welcome to LibreOffice" in sarlavha:
            try:
                hwnd = win32gui.FindWindow(None, sarlavha)
                if hwnd:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    topildi = True
            except Exception:
                pass
        elif "осстановлен" in sarlavha or "Document Recovery" in sarlavha:
            # "Отклонить все" bosilgandan keyin QO'SHIMCHA tasdiq
            # so'raladi ("Да/Нет" — "shu rostdan rad etilsinmi?") —
            # avval SHUNI tekshiramiz, bo'lmasa "Отклонить все"ni bosamiz.
            # `click_input()` chinakam sichqoncha hodisasi bo'lgani sabab
            # oyna OLDIN fokusga keltirilishi SHART (aks holda klik
            # ba'zan boshqa oynaga tushib ketadi/yo'qoladi).
            try:
                w.set_focus()
                time.sleep(0.3)
            except Exception:
                pass
            tugmalar = {}
            for b in w.descendants(control_type="Button"):
                try:
                    matn = b.window_text() or ""
                except Exception:
                    continue
                tugmalar[matn] = b
            bosiladigan = tugmalar.get("Да") or tugmalar.get("Yes")
            if not bosiladigan:
                bosiladigan = tugmalar.get("Отклонить все") or tugmalar.get("Discard All")
            if bosiladigan:
                bosiladigan.click_input()
                time.sleep(0.3)
            else:
                try:
                    hwnd = win32gui.FindWindow(None, sarlavha)
                    if hwnd:
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                except Exception:
                    pass
            topildi = True
    return topildi


def _nom_qutisini_top(oyna):
    """Name Box (joriy katak/diapazon manzilini ko'rsatuvchi/qabul
    qiluvchi Edit) — manzil naqshiga ('F6', 'A1:I1' kabi) mos keladigan
    BIRINCHI Edit control sifatida topiladi (LibreOffice'da alohida
    avtomatika-ID yo'q, shu sabab qiymat naqshi bo'yicha aniqlanadi)."""
    import re

    naqsh = re.compile(r"^[A-Z]+\d+(:[A-Z]+\d+)?$")
    for e in oyna.descendants(control_type="Edit"):
        try:
            if naqsh.match(e.window_text() or ""):
                return e
        except Exception:
            continue
    raise RuntimeError("Name Box (katak-manzil maydoni) topilmadi.")


def katakka_ot(oyna, katak_manzili: str):
    """Name Box orqali berilgan katakka (masalan 'F6') o'tadi — real
    klaviatura hodisalari bilan (UIA SetValue emas, chunki Calc buni
    har doim ham qabul qilmaydi)."""
    _oyna_topib_captcha_tekshir_yoki_ott(oyna)
    nb = _nom_qutisini_top(oyna)
    nb.click_input()
    time.sleep(0.2)
    nb.type_keys("^a", pause=0.05)
    nb.type_keys(katak_manzili, pause=0.03)
    nb.type_keys("{ENTER}", pause=0.1)
    time.sleep(0.4)


def _oyna_topib_captcha_tekshir_yoki_ott(oyna):
    try:
        captchani_tekshir_va_toxtat(oyna)
    except DesktopXavfsizlikXatosi:
        raise
    except Exception:
        pass


def katakni_oqi(oyna, katak_manzili: str) -> str:
    """Berilgan katakka o'tib, Ctrl+C bilan nusxalab, Windows clipboard'dan
    O'QISH orqali qiymatini qaytaradi (UI-harakat bilan olingan real
    qiymat — fayl to'g'ridan-to'g'ri o'qilmaydi/parse qilinmaydi)."""
    import win32clipboard

    katakka_ot(oyna, katak_manzili)
    oyna.set_focus()
    oyna.type_keys("^c")
    time.sleep(0.4)
    win32clipboard.OpenClipboard()
    try:
        qiymat = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except Exception:
        qiymat = ""
    finally:
        win32clipboard.CloseClipboard()
    return (qiymat or "").strip()


def katakka_yoz(oyna, katak_manzili: str, qiymat: str) -> dict:
    """Berilgan (BO'SH deb taxmin qilingan) katakka klaviatura orqali
    qiymat yozadi va Enter bosadi — HECH QACHON saqlamaydi. Parol-xil
    maydon tushunchasi jadval katagiga tegishli emas, lekin CAPTCHA
    tekshiruvi baribir ishlaydi (izchillik uchun)."""
    _oyna_topib_captcha_tekshir_yoki_ott(oyna)
    katakka_ot(oyna, katak_manzili)
    oyna.type_keys(qiymat, with_spaces=True)
    oyna.type_keys("{ENTER}")
    time.sleep(0.3)
    return {"katak": katak_manzili, "yozilgan_qiymat": qiymat}


def nusxani_yop(pid: int):
    """Nusxa oynasini MAJBURAN (process-kill) yopadi — HECH QACHON
    "Saqlash?" dialogiga duch kelmaydi, hech qanday holatda diskka
    yozilmaydi. `pid` — `nusxada_och()` qaytargan qiymat."""
    import psutil

    try:
        psutil.Process(pid).kill()
    except psutil.NoSuchProcess:
        pass


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(__doc__)
