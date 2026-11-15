# -*- coding: utf-8 -*-
"""
"Azizbek AI Agent" Telegram kanali uchun UMUMIY kunlik post-limiti.

2026-09-15, Azizbek aniq shikoyat qildi: "juda ko'p post qo'yayapsan,
obunachilar zerikib qolyapti, kuniga 3 ta yetarli, faqat eng foydali
bo'lsin". Sabab: ai_yangiliklar.py (har 3 daqiqada tekshiradi, yangi
maqola topilsa darhol bir necha post qiladi) va portfolio_postlar.py
(kuniga 1 marta) o'rtasida umumiy kunlik chegara yo'q edi.

Bu modul ikkala skript uchun UMUMIY (jami) kunlik hisoblagich. Post
qo'yishdan OLDIN `limitga_yetdimi()` bilan tekshiriladi, muvaffaqiyatli
qo'yilgandan KEYIN `postni_hisobla()` chaqiriladi. Kun almashganda
(sana solishtirish orqali) hisoblagich avtomatik nolga tushadi.
"""
import json
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOLAT_PATH = os.path.join(BASE_DIR, "kanal_post_limiti.json")

KUNLIK_LIMIT = 3  # 2026-09-15, Azizbek talabi: kuniga JAMI 3 tadan oshmasin


def _holatni_ukish():
    bugun = date.today().isoformat()
    if os.path.exists(HOLAT_PATH):
        try:
            with open(HOLAT_PATH, "r", encoding="utf-8") as f:
                holat = json.load(f)
            if holat.get("sana") == bugun:
                return holat
        except Exception:
            pass
    return {"sana": bugun, "son": 0}


def limitga_yetdimi():
    """True -- bugun allaqachon KUNLIK_LIMIT ta post qo'yilgan, yangisi
    qo'yilmasligi kerak (keyingi kunga qoldiriladi)."""
    return _holatni_ukish()["son"] >= KUNLIK_LIMIT


def postni_hisobla():
    """Kanalga muvaffaqiyatli post qo'yilgandan KEYIN chaqiriladi."""
    holat = _holatni_ukish()
    holat["son"] += 1
    with open(HOLAT_PATH, "w", encoding="utf-8") as f:
        json.dump(holat, f, ensure_ascii=False, indent=2)
    return holat["son"]
