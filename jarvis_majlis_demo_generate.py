"""
Bugungi (2026-09-27 kecha) MAJBURIY demo majlisni BIR MARTA generatsiya
qiladi: matnni jarvis_majlis.demo_orzu_majlis_matni()dan oladi, har bir
gap uchun edge-tts orqali xodimning O'Z ovozida mp3 yasaydi va hammasini
jarvis_hud/majlislar/oxirgi.json + oxirgi_audio/*.mp3 ga saqlaydi.

Ishga tushirish: `python jarvis_majlis_demo_generate.py`
Natija butunlay OFFLINE qayta ishlatiladi ("Oxirgi majlis" tugmasi) --
bu skript faqat BIR MARTA (yoki ma'lumot yangilansa qayta) ishga tushadi.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import edge_tts  # noqa: E402
import jarvis_jamoa_data as jjd  # noqa: E402
import jarvis_majlis as jm  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SINTEZ_TIMEOUT_S = 30
AUDIO_DIR = jm.MAJLIS_DIR / "oxirgi_audio"


async def _sintez(matn: str, voice: str, rate: str, pitch: str, chiqish_mp3: Path):
    for urinish in (1, 2):
        try:
            communicate = edge_tts.Communicate(matn, voice, rate=rate, pitch=pitch)
            await asyncio.wait_for(communicate.save(str(chiqish_mp3)), timeout=SINTEZ_TIMEOUT_S)
            return
        except Exception as e:
            if urinish == 2:
                raise
            print(f"  ...qayta urinilmoqda ({e!r})")


def _bir_gap_ovoz(fayl_nomi: str, xodim_id: str, matn: str) -> str:
    meta = jjd.XODIMLAR[xodim_id]
    ovoz_matni = jjd.ovoz_uchun_tayyorla(matn)
    yol = AUDIO_DIR / fayl_nomi
    try:
        asyncio.run(_sintez(ovoz_matni, meta["voice"], meta["rate"], meta["pitch"], yol))
        print(f"  OK  {fayl_nomi} ({yol.stat().st_size} bayt)")
        return fayl_nomi
    except Exception as e:
        print(f"  XATO {fayl_nomi}: {e!r}")
        return ""


def asosiy():
    print("1) Matn tayyorlanmoqda (real raqamlar bilan)...")
    data = jm.demo_orzu_majlis_matni()
    print(f"   Mavzu: {data['mavzu']}")

    print("2) Ovoz generatsiya qilinmoqda (edge-tts)...")
    for i, gap in enumerate(data["tur1"]):
        fn = f"tur1_{i}_{gap['xodim']}.mp3"
        gap["audio"] = _bir_gap_ovoz(fn, gap["xodim"], gap["matn"])
    for i, gap in enumerate(data["tur2"]):
        fn = f"tur2_{i}_{gap['xodim']}.mp3"
        gap["audio"] = _bir_gap_ovoz(fn, gap["xodim"], gap["matn"])
    data["xulosa_audio"] = _bir_gap_ovoz("xulosa_jarvis.mp3", "jarvis", data["xulosa"])

    print("3) JSON saqlanmoqda...")
    jm.demo_saqla(data)
    print(f"   Saqlandi: {jm.demo_fayl_yoli()}")
    print("TUGADI.")


if __name__ == "__main__":
    asosiy()
