# 2-jonli sinov: ildiz sabab tuzatilgandan keyin (run_in_background majburan
# o'chirilgan). Tekshiramiz: (a) Bash haqiqatan sinxron ishladimi (vaqt bilan
# tasdiqlaymiz), (b) shu sabab fon vazifa boshqa turga "sizib chiqib" eski
# savolni qayta so'rash muammosi endi umuman yuz bermasligi kerak.
import asyncio
import time
from jarvis_core import Jarvis, auto_approve


async def main():
    async with Jarvis(confirm_fn=auto_approve, log=False) as j:
        boshlandi = time.monotonic()
        javob1 = await j.ask(
            "Bash orqali FONDA (run_in_background=true bilan) shu buyruqni ishga "
            "tushirishga harakat qil: `sleep 20 && echo TAYYOR`. Ishga tushirgach "
            "(fon rejimda ishlayapti deb o'ylab) menga darhol qisqa xabar ber va "
            "oxirida bitta ha/yo'q savol ber: 'Natija tayyor bo'lgach yana xabar "
            "beraymi?' shu jumla bilan tugat."
        )
        davomiylik = time.monotonic() - boshlandi
        print("=== 1-JAVOB ===\n" + javob1)
        print(f"\n[1-chaqiruv davomiyligi]: {davomiylik:.1f} soniya")
        print("[pending_question]:", j._pending_question)

        # Endi darhol (bg mavjud bo'lganida race yuzaga keladigan payt) yangi
        # savol beramiz — lekin endi fon vazifa YO'Q (sinxron tugagan), demak
        # hech qanday notification kelib qolmasligi kerak.
        javob2 = await j.ask("Ha")
        print("\n=== 2-JAVOB (darhol, 'Ha' deb yozdim) ===\n" + javob2)
        print("[pending_question]:", j._pending_question)

        sinxron_ishladimi = davomiylik >= 18  # 20s buyruq to'liq kutilgan bo'lsa
        eski_savol_qaytdimi = "natija tayyor bo'lgach yana xabar beraymi" in javob2.lower()
        print("\n=== XULOSA ===")
        print("Bash haqiqatan sinxron (bloklovchi) ishladimi:", sinxron_ishladimi)
        print("Javobda eski savol so'zma-so'z qaytarilganmi (BUG bo'lsa True):", eski_savol_qaytdimi)


asyncio.run(main())
