"""
JARVIS OS -- topshiriqlarning DOIMIY (bridge qayta ishga tushsa ham
o'chmaydigan) tarixi (2026-09-28, "1-bosqich" band 3 uchun asos).

`jarvis_hud_bridge.py`dagi `_topshiriqlar` lug'ati FAQAT xotirada (panel
tez ko'rsatishi uchun) -- bridge restart bo'lsa yo'qoladi. Kunlik hisobot
(soat 21:00) va ertalabki tuzatish (soat 08:00) uchun BUTUN kun davomidagi
yozuv kerak, shuning uchun har bir topshiriq TUGAGANDA (tayyor/xato/
bekor_qilindi) shu faylga ham (JSONL, `jarvis_bildirishnoma.py`/
`jarvis_holati_signal.py` bilan bir xil falsafa -- oddiy append, hech qachon
xato ko'tarmaydi) bitta qator qo'shiladi.
"""

import json
import os
from datetime import datetime
from pathlib import Path

FAYL = Path(__file__).parent / "jarvis_hud" / "topshiriqlar_tarixi.jsonl"


def yozuv_qoshish(*, xodim: str, matn: str, holat: str, natija: str | None,
                   davomiyligi_s: float | None, sabab: str | None = None,
                   manba: str | None = None) -> None:
    try:
        FAYL.parent.mkdir(parents=True, exist_ok=True)
        yozuv = {
            "vaqt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "xodim": xodim,
            "matn": (matn or "")[:300],
            "holat": holat,  # "tayyor" | "xato" | "bekor_qilindi"
            "natija": (natija or "")[:800] if natija else None,
            "davomiyligi_s": round(davomiyligi_s, 1) if davomiyligi_s is not None else None,
            "sabab": (sabab or "")[:300] if sabab else None,
            "manba": manba,
        }
        with open(FAYL, "a", encoding="utf-8") as f:
            f.write(json.dumps(yozuv, ensure_ascii=False) + "\n")
    except Exception:
        pass


def yozuvlarni_oqi(sana: str | None = None, sinovlarni_ham_qoshib: bool = False) -> list:
    """`sana` "YYYY-MM-DD" -- berilmasa BUGUN. Fayl yo'q/buzuq qator bo'lsa
    ham xato ko'tarmaydi (buzuq qatorlar shunchaki o'tkazib yuboriladi).

    Sukut bo'yicha matni "SINOV" bilan boshlangan (imtihon/qo'lda test)
    yozuvlar chiqarib tashlanadi -- kunlik hisobot/ertalabki tuzatish
    Azizbekka FAQAT haqiqiy topshiriqlarni ko'rsatishi kerak, `jarvis_imtihon.py`
    har ishga tushishda qoldiradigan test-yozuvlar bilan aralashmasin."""
    if sana is None:
        sana = datetime.now().strftime("%Y-%m-%d")
    natija = []
    if not FAYL.exists():
        return natija
    try:
        with open(FAYL, "r", encoding="utf-8") as f:
            for qator in f:
                qator = qator.strip()
                if not qator:
                    continue
                try:
                    y = json.loads(qator)
                except Exception:
                    continue
                if not y.get("vaqt", "").startswith(sana):
                    continue
                if not sinovlarni_ham_qoshib and y.get("matn", "").strip().upper().startswith("SINOV"):
                    continue
                natija.append(y)
    except Exception:
        pass
    return natija
