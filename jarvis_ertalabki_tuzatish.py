"""
JARVIS OS -- Ertalabki tuzatish, har kuni soat 08:00 (2026-09-28, "1-bosqich"
band 3, Azizbek talabi: "ertasi kuni ertalab ❌ bo'lganlarni tuzat va nima
tuzatilganini yoz").

Kechagi (`jarvis_topshiriq_tarixi.py`) "xato" holatidagi topshiriqlarni
oladi va HAR BIRINI xuddi shu matn bilan qayta sinaydi (`/jamoa/savol` --
bir xil dispatch/AI mantig'i, FAQAT O'QISH -- hech qanday yozish/tasdiqsiz
bajarish yo'q, "production'ga yozish yo'q" qoidasi buzilmaydi). Natija:
  - ✅ tuzaldi -- qayta urinishda xato yo'q edi (odatda vaqtinchalik SSH/AI
    uzilishi bo'lgan)
  - ⏸ qayta tasdiq kerak -- matn "yozish" turiga tushib qoldi, AVTOMATIK
    tasdiqlanmaydi (xavfsizlik qoidasi), qo'lda ko'rib chiqish kerak
  - ❌ hali ham xato -- yangi sabab bilan ko'rsatiladi

Task Scheduler: "Jarvis Ertalabki Tuzatish", har kuni 08:00 (Sardor
backup-tekshiruvi 08:30'dan OLDIN, Ertalabki yig'ilish 09:00'dan OLDIN).
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "jarvis_hud"))

import jarvis_topshiriq_tarixi as jtt  # noqa: E402
import jarvis_jamoa_data as jjd  # noqa: E402
import jarvis_xodim_telegram as jxt  # noqa: E402
from jarvis_proaktiv import telegram_xabar_yubor  # noqa: E402


def _kecha() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def tuzatishni_bajar(sana: str | None = None) -> str:
    sana = sana or _kecha()
    xatolar = [y for y in jtt.yozuvlarni_oqi(sana) if y.get("holat") == "xato"]
    if not xatolar:
        return f"🔧 Ertalabki tuzatish ({sana}): kecha hech qanday ❌ xato topshiriq bo'lmagan, tuzatadigan narsa yo'q."

    qatorlar = [f"🔧 Ertalabki tuzatish ({sana}): kecha {len(xatolar)} ta xato topilgan, qayta tekshirildi:\n"]
    for i, y in enumerate(xatolar, start=1):
        xodim_id = y.get("xodim")
        ism = jjd.XODIMLAR.get(xodim_id, {}).get("name", xodim_id)
        matn = y.get("matn", "")
        eski_sabab = (y.get("sabab") or "")[:150]
        try:
            natija = jxt.bridge_savol(xodim_id, matn)
        except Exception as e:
            qatorlar.append(f"{i}. {ism} -- \"{matn[:50]}\": ⚠️ qayta tekshirib bo'lmadi (bridge javob bermadi: {e})")
            continue

        turi = natija.get("turi")
        if "error" in natija:
            qatorlar.append(f"{i}. {ism} -- \"{matn[:50]}\": ❌ hali ham xato: {natija['error'][:150]}")
        elif turi == "yozish":
            qatorlar.append(f"{i}. {ism} -- \"{matn[:50]}\": ⏸ qayta tasdiq talab qiladi -- avtomatik bajarilmadi (xavfsizlik qoidasi), qo'lda ko'rib chiqing.")
        else:
            qatorlar.append(f"{i}. {ism} -- \"{matn[:50]}\": ✅ tuzaldi (eski sabab: {eski_sabab[:80]})")

    return "\n".join(qatorlar)


def main():
    matn = tuzatishni_bajar()
    telegram_xabar_yubor(matn)
    print("Ertalabki tuzatish yuborildi.")


if __name__ == "__main__":
    main()
