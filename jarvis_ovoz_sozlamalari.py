# -*- coding: utf-8 -*-
"""
Telegram'dagi "ovozli javob" sozlamasi -- yoqilgan/o'chirilgan holatni
diskka saqlaydi (2026-10-11, Azizbek buyrug'i: "sozlamada ovozli javobni
yoqish va o'chirish imkoni bo'lsin"). Bot qayta ishga tushsa ham holat
saqlanib qoladi.
"""
import json
from pathlib import Path

_FAYL = Path(__file__).parent / "jarvis_ovoz_sozlamalari.json"
_STANDART = True  # birinchi marta (fayl hali yo'q bo'lsa) -- yoqilgan


def ovozli_javob_yoqilganmi() -> bool:
    try:
        return bool(json.loads(_FAYL.read_text(encoding="utf-8")).get("yoqilgan", _STANDART))
    except Exception:
        return _STANDART


def ovozli_javobni_ornat(yoqilgan: bool) -> None:
    _FAYL.write_text(
        json.dumps({"yoqilgan": bool(yoqilgan)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
