"""Vaqtinchalik runner: kopri_sinov.py dagi faqat test_stop() ni ishga
tushiradi (heartbeat va fon_ishlar testlarisiz), diagnostika maqsadida.
kopri_sinov.py ning o'ziga tegilmagan — undan faqat test_stop() import
qilinadi."""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jarvis_core import Jarvis, auto_approve  # noqa: E402
import kopri_sinov  # noqa: E402

NATIJA_FAYL = Path(__file__).resolve().parent / "_faqat_stop_natija.json"


async def main():
    async with Jarvis(log=False, confirm_fn=auto_approve) as jarvis:
        await kopri_sinov.test_stop(jarvis)
    natija = kopri_sinov.natija["testlar"].get("stop", {})
    NATIJA_FAYL.write_text(
        json.dumps(natija, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Natija: {NATIJA_FAYL}")


if __name__ == "__main__":
    asyncio.run(main())
