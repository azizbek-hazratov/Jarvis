"""
JARVIS HOLATI SIGNAL — Jarvis'ning band/bo'sh holatini jarayonlar orasida
ulashish uchun eng past invaziv mexanizm (2026-09-22, pixel-ofis "AI
Xodimlarim" #Jarvis-belgisi, ikkinchi bosqich — Telegram integratsiyasi).

MUAMMO: jarvis_telegram.py (Telegram bot) va jarvis_hud_bridge.py (HUD
bridge) ikkita BUTUNLAY ALOHIDA Python jarayoni — har birining o'z
jarvis_core.Jarvis obyekti, o'z asyncio.Lock()i bor. Shuning uchun bittasi
band bo'lsa, ikkinchisi bundan bexabar (avvalgi /jarvis_holati faqat
bridge'ning o'z lock'ini ko'rardi).

YECHIM (jarvis_bildirishnoma.py'dagi "umumiy fayl" naqshiga o'xshab, LEKIN
jarvis_core.py'ga tegilmaydi — har bir chaqiruvchi fayl o'zi belgilaydi):
umumiy XOTIRA/qulf EMAS — har bir manba (masalan "telegram", "bridge") o'z
holatini FAQAT O'ZIGA tegishli kichik faylga yozadi
(jarvis_hud/jarvis_holati_<manba>.json). Har bir fayl bitta yozuvchiga
tegishli — shuning uchun ikkita jarayon bitta faylga bir vaqtda yozib
to'qnashishi (race condition) mumkin emas. O'qish (band_holatlarini_oqi)
barcha ma'lum manbalarni yig'adi, istalgan BITTASI band bo'lsa ham umumiy
holat "band" bo'ladi.

ESKIRISH HIMOYASI: agar jarayon "band" deb yozib qo'yib, keyin kutilmaganda
to'xtab qolsa (masalan Windows majburan yopsa), "band" holati abadiy osilib
qolmasin deb, yozuv ESKIRISH_S dan eski bo'lsa "bosh" deb hisoblanadi.

Yozish funksiyalari (band_belgila/bosh_belgila) — xuddi bildirishnoma_yoz()
kabi — HECH QACHON xato ko'tarmaydi: bu faqat QO'SHIMCHA signal kanali,
chaqiruvchining asosiy vazifasini (Jarvisga savol berish) hech qanday
holatda buzmasligi kerak.
"""

import json
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HOLATI_DIR = BASE_DIR / "jarvis_hud"
MA_LUM_MANBALAR = ("telegram", "bridge")
ESKIRISH_S = 650  # shuncha soniyadan eski "band" yozuvi "bosh" deb hisoblanadi — Jarvis
# so'rovlari (jarvis_core.py'dagi ASK_TIMEOUT_S=600) qonuniy ravishda 10 daqiqagacha
# cho'zilishi mumkin, shuning uchun bu chegara shundan biroz katta bo'lishi shart
# (2026-09-22 tuzatildi: avval 120s edi — bu haqiqiy uzoq so'rov hali tugamasdan
# "bosh" deb noto'g'ri ko'rsatib qo'yardi, faqat jarayon chindan qotib qolganda
# ishlashi kerak bo'lgan zaxira himoya endi shunga mos qilindi)


def _fayl(manba: str) -> Path:
    return HOLATI_DIR / f"jarvis_holati_{manba}.json"


def _yoz(manba: str, band: bool) -> None:
    try:
        HOLATI_DIR.mkdir(parents=True, exist_ok=True)
        yozuv = {"band": band, "vaqt": time.time()}
        fayl = _fayl(manba)
        tmp = fayl.with_suffix(".tmp")
        tmp.write_text(json.dumps(yozuv), encoding="utf-8")
        os.replace(tmp, fayl)  # atomik almashtirish — o'qiyotgan tomon yarim yozuvni ko'rmaydi
    except Exception:
        pass


def band_belgila(manba: str) -> None:
    """Berilgan manba (masalan "telegram" yoki "bridge") hozir bitta so'rovni
    ishlab turibdi deb belgilaydi."""
    _yoz(manba, True)


def bosh_belgila(manba: str) -> None:
    """Berilgan manba so'rovni tugatdi — bo'sh holatga qaytdi deb belgilaydi."""
    _yoz(manba, False)


def band_holatlarini_oqi() -> dict:
    """Har bir ma'lum manba uchun {manba: bool} lug'at qaytaradi. Fayl
    yo'q/o'qib bo'lmasa yoki yozuv ESKIRISH_S dan eski bo'lsa — False."""
    natija = {}
    hozir = time.time()
    for manba in MA_LUM_MANBALAR:
        band = False
        try:
            fayl = _fayl(manba)
            if fayl.exists():
                data = json.loads(fayl.read_text(encoding="utf-8"))
                if data.get("band") and (hozir - float(data.get("vaqt", 0))) < ESKIRISH_S:
                    band = True
        except Exception:
            band = False
        natija[manba] = band
    return natija


def biror_joyda_bandmi() -> bool:
    """Telegram YOKI bridge — ikkalasidan istalgan birida hozir so'rov
    ishlanayotgan bo'lsa True."""
    return any(band_holatlarini_oqi().values())


def manba_bandmi(manba: str) -> bool:
    """Berilgan BITTA manbaning (istalgan nom — MA_LUM_MANBALAR ro'yxatiga
    BOG'LIQ EMAS) band/bo'sh holatini o'qiydi. Boshqa mustaqil botlar
    (masalan "ai_expert" — mijozlar/ai_expert_bot) uchun ishlatiladi, shu
    sabab ATAYLAB `band_holatlarini_oqi()`/`biror_joyda_bandmi()`dan ALOHIDA:
    ular faqat asosiy Jarvis (telegram/bridge) uchun ishlatiladi, bu yerga
    yangi manba qo'shish ULARNING natijasiga TA'SIR QILMASLIGI kerak (pixel-
    ofisdagi boshqa belgilar aralashib ketmasin). Fayl yo'q/o'qib bo'lmasa
    yoki yozuv ESKIRISH_S dan eski bo'lsa — False."""
    try:
        fayl = _fayl(manba)
        if fayl.exists():
            data = json.loads(fayl.read_text(encoding="utf-8"))
            if data.get("band") and (time.time() - float(data.get("vaqt", 0))) < ESKIRISH_S:
                return True
    except Exception:
        pass
    return False
