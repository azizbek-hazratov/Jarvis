"""
Faqat /stop sinovini ishga tushiradi (kopri_sinov.py'dagi test_stop),
heartbeat va fon-ishlar testlarisiz. Jonli Jarvis (jarvis_fon.py
pythonw + uning claude.exe'si) bilan HECH QANDAY aloqasi yo'q — bu
skript o'zining ALOHIDA Jarvis()/claude.exe nusxasini ishga tushiradi.
"""
import asyncio
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from jarvis_core import Jarvis, auto_approve  # noqa: E402
import sinov.kopri_sinov as ks  # noqa: E402

NATIJA_FAYL = Path(__file__).resolve().parent / "stop_yolgiz_natija.json"


async def main():
    async with Jarvis(log=False, confirm_fn=auto_approve) as jarvis:
        await ks.test_stop(jarvis)
    ks.natija["tugadi"] = ks.datetime.now().isoformat()
    NATIJA_FAYL.write_text(
        json.dumps(ks.natija, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ks.log(f"Yolg'iz /stop sinovi tugadi. Natija: {NATIJA_FAYL}")


if __name__ == "__main__":
    asyncio.run(main())
