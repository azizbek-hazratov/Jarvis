"""
Restart-oldi xavfsizlik tekshiruvi (2026-09-27, Azizbek talabi -- egasi-kabinasi
fon-agenti ishlab turganda rejalashtirilgan restart uni deyarli o'ldirib
qo'yayotgan holatdan keyin).

Har qanday Jarvis restart skripti (`qayta.ps1`, `qayta_asosiy.ps1`,
`restart_bot.ps1` va h.k.) haqiqiy o'ldirish/qayta ishga tushirish
qadamlaridan OLDIN shu skriptni chaqirishi SHART.

Qoida:
- `jarvis_fon_ishlar.py` (`fon-ishlar.json`) da holat="ishlayapti" bo'lgan
  kamida bitta yozuv bo'lsa -- restart TAQIQLANADI: Telegram orqali
  "N ta fon agent ishlayapti: [nomlari]. Restart kechiktirildi." xabari
  yuboriladi, skript EXIT CODE 2 bilan chiqadi.
- Faol yozuv bo'lmasa -- EXIT CODE 0 (restart davom etishi mumkin).
- `--majburan` argumenti bilan chaqirilsa -- tekshiruv CHETLAB O'TILADI
  (EXIT CODE 0), LEKIN agar haqiqatan faol ish bo'lsa, buni Azizbekka
  Telegram orqali OCHIQ aytadi (chetlab o'tish "sezilmasdan" bo'lmasin --
  shaffoflik uchun).

Chaqiruvchi PowerShell skript $LASTEXITCODE ni tekshirib, 2 bo'lsa
o'zi ham darhol to'xtashi kerak.
"""

import sys

sys.path.insert(0, r"C:\Users\Dell\jarvis")

import jarvis_fon_ishlar as fon_ishlar  # noqa: E402
from jarvis_proaktiv import telegram_xabar_yubor  # noqa: E402


def main():
    majburan = "--majburan" in sys.argv
    faollar = fon_ishlar.faol_ishlar()

    if majburan:
        if faollar:
            nomlar = ", ".join(x.get("agent", "?") for x in faollar)
            telegram_xabar_yubor(
                f"⚠️ MAJBURAN RESTART: {len(faollar)} ta fon agent ishlayotgan bo'lsa ham "
                f"({nomlar}) himoya qoidasi chetlab o'tildi, restart baribir bajarilmoqda."
            )
        print("MAJBURAN -- fon-ishlar tekshiruvi chetlab o'tildi, restart davom etadi.")
        sys.exit(0)

    if not faollar:
        print("Fon-ishlar tekshiruvi: faol fon-agent yo'q, restart davom etishi mumkin.")
        sys.exit(0)

    nomlar = ", ".join(x.get("agent", "?") for x in faollar)
    xabar = f"{len(faollar)} ta fon agent ishlayapti: {nomlar}. Restart kechiktirildi."
    print(f"RESTART TAQIQLANDI: {xabar}")
    telegram_xabar_yubor(xabar)
    sys.exit(2)


if __name__ == "__main__":
    main()
