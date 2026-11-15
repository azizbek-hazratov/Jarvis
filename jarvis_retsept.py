"""
JARVIS RETSEPT — "bir marta ko'rsataman, keyin o'zi takrorlaydi" (Record →
Generalize → Replay), Excel/LibreOffice uchun birinchi amalga oshirish.

G'OYA (2026-09-21, Azizbek bilan kelishilgan reja asosida):
1. RECORD — Azizbek "birga bajarish" rejimida qaysi katakka nima yozishni
   aytadi, Jarvis `jarvis_desktop.katakka_yoz/katakni_oqi` orqali bajaradi
   VA har qadamni shu paytning o'zida JSON qadamlar ro'yxatiga yozadi.
2. GENERALIZE — qaysi qiymatlar "har safar o'zgaradi" (sana, summa va h.k.)
   ekanini BELGILAB (parametr nomi berib) yozamiz — JSON'da o'sha qadamning
   qiymati `{{parametr_nomi}}` shabloniga aylanadi.
3. REPLAY — retsept JSON + yangi parametrlar bilan chaqirilганda, HAR BIR
   qadam yana AYNAN `jarvis_desktop.katakka_yoz`/`katakni_oqi` orqali
   bajariladi — ya'ni Bosqich 1/2'dagi xavfsizlik qatlami (CAPTCHA/to'lov/
   hisob-yaratish/parol/saqlash bloklari) AVTOMATIK ishlaydi, alohida
   qoida yozish shart emas. Parametr qiymati faqat "nima yoziladi"ga
   ta'sir qiladi, xavfsizlik tekshiruvi esa har doim runtime'dagi element
   matni ustida ishlaganidan — parametr orqali bypass qilib bo'lmaydi.

Retsept format (JSON):
{
  "nom": "...",
  "parametrlar": ["sana", "summa"],
  "qadamlar": [
    {"amal": "yoz", "katak": "Z90", "qiymat": "{{sana}}"},
    {"amal": "yoz", "katak": "Z91", "qiymat": "{{summa}}"},
    {"amal": "yoz", "katak": "Z92", "qiymat": "=Z91*1.12"},
    {"amal": "oqi", "katak": "Z92", "natija_nomi": "hisoblangan_summa"}
  ]
}
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jarvis_desktop as jd

PLACEHOLDER_RE = re.compile(r"^\{\{(\w+)\}\}$")


class Retseptchi:
    """RECORD bosqichi — "birga bajarish" paytida chaqiriladi. Har chaqiriq
    HAQIQIY harakatni (jarvis_desktop orqali, xavfsizlik qatlami bilan)
    bajaradi VA parallel qadamlar ro'yxatiga yozadi."""

    def __init__(self, nom: str):
        self.nom = nom
        self.qadamlar: list[dict] = []
        self.parametrlar: list[str] = []

    def yoz(self, oyna, katak: str, qiymat, *, parametr_nomi: str | None = None):
        """Katakka real qiymatni yozadi (demo qiymat sifatida) va qadamni
        qayd etadi. `parametr_nomi` berilsa, JSON'da qiymat o'rniga
        `{{parametr_nomi}}` shabloni saqlanadi (lekin RECORD paytida
        haqiqatan yozilgan narsa — berilgan `qiymat`, ya'ni demo)."""
        natija = jd.katakka_yoz(oyna, katak, str(qiymat))
        if parametr_nomi:
            if parametr_nomi not in self.parametrlar:
                self.parametrlar.append(parametr_nomi)
            saqlanadigan_qiymat = f"{{{{{parametr_nomi}}}}}"
        else:
            saqlanadigan_qiymat = str(qiymat)
        self.qadamlar.append({"amal": "yoz", "katak": katak, "qiymat": saqlanadigan_qiymat})
        return natija

    def oqi(self, oyna, katak: str, *, natija_nomi: str):
        """Katakdan o'qiydi va qadamni qayd etadi (replay paytida bu qadam
        natijalar lug'atiga yoziladi, boshqa hech narsaga yozilmaydi)."""
        qiymat = jd.katakni_oqi(oyna, katak)
        self.qadamlar.append({"amal": "oqi", "katak": katak, "natija_nomi": natija_nomi})
        return qiymat

    def saqla(self, fayl_yoli: str):
        retsept = {"nom": self.nom, "parametrlar": self.parametrlar, "qadamlar": self.qadamlar}
        Path(fayl_yoli).write_text(json.dumps(retsept, ensure_ascii=False, indent=2), encoding="utf-8")
        return retsept


def _shablonni_toldir(qiymat: str, parametrlar: dict) -> str:
    m = PLACEHOLDER_RE.match(qiymat)
    if not m:
        return qiymat
    nom = m.group(1)
    if nom not in parametrlar:
        raise KeyError(f"Retsept parametri '{nom}' berilmagan (replay chaqiruvida yetishmayapti).")
    return str(parametrlar[nom])


def retseptni_ishga_tushir(retsept: dict, oyna, parametrlar: dict) -> dict:
    """REPLAY bosqichi. `retsept` — `Retseptchi.saqla()` yozgan JSON
    (yuklab olingan dict). Har bir qadam AYNAN `jarvis_desktop`ning
    xavfsiz funksiyalari orqali bajariladi — bypass yo'q.

    Qaytaradi: {"oqi" qadamlarining natija_nomi -> qiymat} lug'ati."""
    kerakli = set(retsept.get("parametrlar", []))
    yetmagan = kerakli - set(parametrlar.keys())
    if yetmagan:
        raise KeyError(f"Yetishmayotgan parametrlar: {sorted(yetmagan)}")

    natijalar = {}
    for qadam in retsept["qadamlar"]:
        if qadam["amal"] == "yoz":
            qiymat = _shablonni_toldir(qadam["qiymat"], parametrlar)
            jd.katakka_yoz(oyna, qadam["katak"], qiymat)
        elif qadam["amal"] == "oqi":
            natijalar[qadam["natija_nomi"]] = jd.katakni_oqi(oyna, qadam["katak"])
        else:
            raise ValueError(f"Noma'lum amal turi: {qadam['amal']!r}")
    return natijalar


def retseptni_fayldan_ishga_tushir(retsept_fayl_yoli: str, oyna, parametrlar: dict) -> dict:
    retsept = json.loads(Path(retsept_fayl_yoli).read_text(encoding="utf-8"))
    return retseptni_ishga_tushir(retsept, oyna, parametrlar)
