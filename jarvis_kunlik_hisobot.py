"""
JARVIS OS -- Kunlik hisobot, har kuni soat 21:00 (2026-09-28, "1-bosqich"
band 3, Azizbek talabi).

Bugun bajarilgan/bekor qilingan BARCHA topshiriqlarni (`jarvis_topshiriq_
tarixi.py`, bridge har bir tugagan topshiriqda shu yerga yozadi) jadval
ko'rinishida Telegramga yuboradi:
  № | kimga | topshiriq | natija | soniya | ✅/❌ | sabab (faqat ❌ bo'lsa)

Task Scheduler: "Jarvis Kunlik Hisobot", har kuni 21:00.
AI ISHLATILMAYDI -- sof matn formatlash, tezkor va ishonchli.
"""

import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

import jarvis_topshiriq_tarixi as jtt  # noqa: E402
import jarvis_jamoa_data as jjd  # noqa: E402
from jarvis_proaktiv import telegram_xabar_yubor  # noqa: E402

HOLAT_BELGI = {"tayyor": "✅", "xato": "❌", "bekor_qilindi": "⏸"}


def _qisqart(matn, n):
    # backtick olib tashlanadi -- xabar BITTA backtick-kod-blokka o'raladi,
    # matn ichida backtik bo'lsa blok muddatidan oldin yopilib qolar edi.
    matn = (matn or "").replace("\n", " ").replace("`", "'").strip()
    return matn if len(matn) <= n else matn[: n - 1] + "…"


def hisobot_matni(sana=None) -> str:
    yozuvlar = jtt.yozuvlarni_oqi(sana)
    if not yozuvlar:
        return "📋 Kunlik hisobot: bugun hech qanday topshiriq bajarilmadi/bekor qilinmadi."

    qatorlar = []
    for i, y in enumerate(yozuvlar, start=1):
        ism = jjd.XODIMLAR.get(y.get("xodim"), {}).get("name", y.get("xodim", "?"))
        topshiriq = _qisqart(y.get("matn"), 28)
        natija = _qisqart(y.get("natija") or y.get("sabab"), 28)
        soniya = f"{y['davomiyligi_s']:.0f}s" if y.get("davomiyligi_s") is not None else "-"
        belgi = HOLAT_BELGI.get(y.get("holat"), "?")
        qator = f"{i:>2} | {ism:<9} | {topshiriq:<28} | {natija:<28} | {soniya:>5} | {belgi}"
        if y.get("holat") == "xato" and y.get("sabab"):
            qator += f"\n     sababi: {_qisqart(y['sabab'], 60)}"
        qatorlar.append(qator)

    muvaffaqiyat = sum(1 for y in yozuvlar if y.get("holat") == "tayyor")
    xato = sum(1 for y in yozuvlar if y.get("holat") == "xato")
    bekor = sum(1 for y in yozuvlar if y.get("holat") == "bekor_qilindi")

    sarlavha = (
        f"📋 Kunlik hisobot ({sana or 'bugun'}): {len(yozuvlar)} ta topshiriq — "
        f"✅{muvaffaqiyat} ❌{xato} ⏸{bekor}"
    )
    # telegram_xabar_yubor() faqat **qalin**/`kod` (backtick) qo'llab-quvvatlaydi
    # -- HTML <pre> teg TO'G'RIDAN-TO'G'RI berilsa escape bo'lib xom ko'rinadi.
    # Shuning uchun jadval BITTA backtick-blok ichida (<code> monospace, ko'p
    # qatorli ham ishlaydi) yuboriladi.
    sarlavha_qator = f"{'№':>2} | {'kimga':<9} | {'topshiriq':<28} | {'natija':<28} | {'soniya':>5} | ✅/❌"
    jadval = "\n".join(qatorlar)
    kod_blok = f"`{sarlavha_qator}\n{'-' * len(sarlavha_qator)}\n{jadval}`"
    return f"{sarlavha}\n\n{kod_blok}"


def main():
    matn = hisobot_matni()
    telegram_xabar_yubor(matn)
    print(f"Kunlik hisobot yuborildi ({len(matn)} belgi).")


if __name__ == "__main__":
    main()
