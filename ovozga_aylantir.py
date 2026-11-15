# -*- coding: utf-8 -*-
"""
Matnni ovozli xabarga aylantirish (Text-to-Speech).

Foydalanish:
    python ovozga_aylantir.py "Salom, bu Jarvis" chiqish.ogg
    yoki modul sifatida: from ovozga_aylantir import matnni_ovozga

Ovozlar (o'zbekcha, Microsoft Edge Neural TTS, bepul):
    uz-UZ-SardorNeural  — erkak ovoz (standart)
    uz-UZ-MadinaNeural  — ayol ovoz

Telegram voice-message sifatida yuborish uchun OGG/Opus formatida
chiqadi (ffmpeg orqali mp3'dan konvertatsiya qilinadi).
"""
import sys
import os
import asyncio
import subprocess
import tempfile

import edge_tts

STANDART_OVOZ = "uz-UZ-SardorNeural"


async def _mp3_yasash(matn, mp3_yol, ovoz):
    communicate = edge_tts.Communicate(matn, ovoz)
    await communicate.save(mp3_yol)


def matnni_ovozga(matn, chiqish_ogg, ovoz=STANDART_OVOZ):
    """Matnni berilgan audio fayliga ovozli xabar sifatida yozadi.

    Agar `chiqish_ogg` ".mp3" bilan tugasa — to'g'ridan-to'g'ri MP3 sifatida
    saqlanadi (ffmpeg shart emas, masalan Instagram audio-attachment uchun).
    Aks holda (masalan ".ogg") — Telegram voice-message uchun OGG/Opus
    formatiga o'tkaziladi (ffmpeg kerak, avvalgi xatti-harakat o'zgarmagan).
    """
    if chiqish_ogg.lower().endswith(".mp3"):
        asyncio.run(_mp3_yasash(matn, chiqish_ogg, ovoz))
        return chiqish_ogg

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_yol = tmp.name
    try:
        asyncio.run(_mp3_yasash(matn, mp3_yol, ovoz))

        # Telegram voice note uchun OGG/Opus formatiga o'tkazish
        natija = subprocess.run(
            [
                "ffmpeg", "-y", "-i", mp3_yol,
                "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1",
                chiqish_ogg,
            ],
            capture_output=True, text=True,
        )
        if natija.returncode != 0:
            raise RuntimeError(f"ffmpeg xatosi: {natija.stderr[-1000:]}")
        return chiqish_ogg
    finally:
        if os.path.exists(mp3_yol):
            os.remove(mp3_yol)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Foydalanish: python ovozga_aylantir.py \"matn\" chiqish.ogg [ovoz]")
        sys.exit(1)
    matn = sys.argv[1]
    chiqish = sys.argv[2]
    ovoz = sys.argv[3] if len(sys.argv) > 3 else STANDART_OVOZ
    yol = matnni_ovozga(matn, chiqish, ovoz)
    print(f"Tayyor: {yol}")
