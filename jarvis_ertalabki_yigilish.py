"""
"Ertalabki yig'ilish" — Jarvis OS 5-bosqich (2026-09-27).

Har kuni 09:00 (Toshkent) — har bir "AI xodim" (Kamola'dan tashqari, u hali
"tez orada") o'z holati haqida QISQA ovozli hisobot beradi (haqiqiy edge-tts,
`jarvis_jamoa_data.py`dagi BIR XIL umumiy ma'lumot-yig'uvchi funksiyalardan —
HUD paneli va shu skript aynan bir xil "say" matnlarini ishlatadi), oxirida
Jarvis umumiy xulosa beradi. Hammasi BITTA ovozli xabar (voice note) sifatida
birlashtirilib, Telegram'ga (Azizbekka) yuboriladi.

AI (Claude) UMUMAN ishlatilmaydi — faqat jarvis_jamoa_data'dagi tayyor
matn/shablonlar va edge-tts. Tez va ishonchli bo'lishi kerak.

Ishga tushirish: python jarvis_ertalabki_yigilish.py
Task Scheduler: "Jarvis Ertalabki Yigilish" (har kuni 09:00).
"""

import asyncio
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import edge_tts
import requests

import config
import jarvis_jamoa_data as jamoa

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "jarvis_ertalabki_yigilish.log"
YIGILISH_DIR = BASE_DIR / "jarvis_hud" / "yigilishlar"

TASHKENT_OFFSET = timedelta(hours=5)

# Jarvis o'z shaxsiy hisobotini bermaydi (u moderator/xulosachi) -- HUD
# frontend'dagi standup() bilan BIR XIL tartib (jamoa.html).
GAPIRUVCHI_TARTIB = ["samandar", "malika", "sardor", "bekzod", "nozima"]

SILENCE_S = 0.5  # har ikki xodim gapi orasida qisqa tin olish


def _tashkent_hozir() -> datetime:
    return datetime.utcnow() + TASHKENT_OFFSET


def _logga_yoz(matn: str):
    vaqt = _tashkent_hozir().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{vaqt}] {matn}\n")
    except Exception:
        pass
    print(f"[{vaqt}] {matn}")


SINTEZ_TIMEOUT_S = 30  # edge-tts ba'zan tarmoq sababli osilib qolishi kuzatilgan (sinovda)


async def _sintez(matn: str, voice: str, rate: str, pitch: str, chiqish_mp3: Path):
    """1 marta muvaffaqiyatsiz/osilib qolsa (timeout) -- BIR MARTA qayta
    urinadi, ikkinchisida ham bo'lmasa xato ko'taradi (chaqiruvchi shu
    xodimni o'tkazib yuboradi, butun yig'ilish abadiy to'xtab qolmasin)."""
    for urinish in (1, 2):
        try:
            communicate = edge_tts.Communicate(matn, voice, rate=rate, pitch=pitch)
            await asyncio.wait_for(communicate.save(str(chiqish_mp3)), timeout=SINTEZ_TIMEOUT_S)
            return
        except Exception as e:
            if urinish == 2:
                raise
            _logga_yoz(f"Ovoz sintezida vaqtinchalik xato ({e!r}), qayta urinilmoqda...")


def _segmentlarni_yasa(bugungi_papka: Path) -> list[tuple[str, Path]]:
    """Har bir gapiruvchi uchun alohida mp3 fayl yaratadi (tekshirish uchun
    ham saqlanadi). (xodim_id, mp3_yol) juftliklari ro'yxatini qaytaradi."""
    xodimlar = {x["id"]: x for x in jamoa.barcha_xodimlar(force=True)}
    natija = []
    for xid in GAPIRUVCHI_TARTIB:
        x = xodimlar.get(xid)
        if not x or not x.get("say"):
            _logga_yoz(f"OGOHLANTIRISH: '{xid}' uchun 'say' matni yo'q, o'tkazib yuborildi.")
            continue
        meta = jamoa.XODIMLAR[xid]
        mp3_yol = bugungi_papka / f"{xid}.mp3"
        # Talaffuz: HUD'dagi bilan BIR XIL funksiya (jarvis_jamoa_data.py) --
        # ekranda ko'ringan "say" matni o'zgarmaydi, faqat ovoz uchun
        # talaffuz.json + raqam->so'z orqali tayyorlanadi.
        ovoz_matni = jamoa.ovoz_uchun_tayyorla(x["say"])
        try:
            asyncio.run(_sintez(ovoz_matni, meta["voice"], meta["rate"], meta["pitch"], mp3_yol))
        except Exception as e:
            _logga_yoz(f"OGOHLANTIRISH: '{xid}' uchun ovoz sintez qilinmadi ({e!r}), o'tkazib yuborildi.")
            continue
        _logga_yoz(f"'{xid}' uchun ovoz tayyor: {mp3_yol.name} ({mp3_yol.stat().st_size} bayt)")
        natija.append((xid, mp3_yol))

    # Yakuniy xulosa -- Jarvis o'zi (bir xil funksiya, jamoa.html'dagi bilan bir xil)
    xulosa_matn = jamoa.yakuniy_xulosa(list(xodimlar.values()))
    jarvis_meta = jamoa.XODIMLAR["jarvis"]
    xulosa_mp3 = bugungi_papka / "jarvis_xulosa.mp3"
    xulosa_ovoz_matni = jamoa.ovoz_uchun_tayyorla(xulosa_matn)
    try:
        asyncio.run(_sintez(xulosa_ovoz_matni, jarvis_meta["voice"], jarvis_meta["rate"], jarvis_meta["pitch"], xulosa_mp3))
        _logga_yoz(f"Yakuniy xulosa ovozi tayyor: {xulosa_mp3.name} ({xulosa_mp3.stat().st_size} bayt)")
        natija.append(("jarvis", xulosa_mp3))
    except Exception as e:
        _logga_yoz(f"OGOHLANTIRISH: yakuniy xulosa ovozi sintez qilinmadi ({e!r}), xulosasiz davom etiladi.")
    return natija


def _birlashtir(segmentlar: list[tuple[str, Path]], chiqish_mp3: Path):
    """ffmpeg filter_complex orqali barcha segmentlarni (orasida qisqa
    tin bilan) BITTA mp3 faylga birlashtiradi. Turli ovoz/tezlikdagi
    edge-tts chiqishlarini xavfsiz birlashtirish uchun ataylab qayta
    kodlaydigan (re-encode) usul ishlatiladi ("-c copy" EMAS) -- shunda
    formatlar biroz farq qilsa ham (masalan namuna chastotasi) xato
    bermaydi."""
    inputs = []
    filter_parts = []
    idx = 0
    for i, (_xid, mp3_yol) in enumerate(segmentlar):
        inputs += ["-i", str(mp3_yol)]
        filter_parts.append(f"[{idx}:a]")
        idx += 1
        if i != len(segmentlar) - 1:
            inputs += ["-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono:d={SILENCE_S}"]
            filter_parts.append(f"[{idx}:a]")
            idx += 1
    filter_complex = "".join(filter_parts) + f"concat=n={idx}:v=0:a=1[aout]"

    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[aout]", str(chiqish_mp3)]
    natija = subprocess.run(cmd, capture_output=True, text=True)
    if natija.returncode != 0:
        raise RuntimeError(f"ffmpeg (birlashtirish) xatosi: {natija.stderr[-1500:]}")


def _ogg_ga_otkaz(mp3_yol: Path, ogg_yol: Path):
    natija = subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_yol), "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1", str(ogg_yol)],
        capture_output=True, text=True,
    )
    if natija.returncode != 0:
        raise RuntimeError(f"ffmpeg (ogg) xatosi: {natija.stderr[-1500:]}")


def _telegram_ovoz_yubor(ogg_yol: Path, izoh: str) -> bool:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendVoice"
    try:
        with open(ogg_yol, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": config.OWNER_ID, "caption": izoh[:1024]},
                files={"voice": (ogg_yol.name, f, "audio/ogg")},
                timeout=60,
            )
        ok = resp.status_code == 200 and resp.json().get("ok")
        if not ok:
            _logga_yoz(f"Telegram sendVoice kutilmagan javob: {resp.status_code} {resp.text[:300]}")
        return bool(ok)
    except Exception as e:
        _logga_yoz(f"Telegram sendVoice xatosi: {e!r}")
        return False


def yigilishni_otkaz() -> Path:
    """Butun oqimni bajaradi va yaratilgan papka yo'lini qaytaradi (sinov
    uchun ham, kunlik ishga tushirish uchun ham qo'llaniladi)."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg topilmadi (PATH'da yo'q) -- ovoz birlashtirib bo'lmaydi.")

    bugun = _tashkent_hozir().strftime("%Y-%m-%d")
    papka = YIGILISH_DIR / bugun
    papka.mkdir(parents=True, exist_ok=True)

    _logga_yoz("Ishga tushdi -- ertalabki yig'ilish boshlanmoqda.")
    segmentlar = _segmentlarni_yasa(papka)
    if not segmentlar:
        raise RuntimeError("Birorta ham ovoz segmenti yaratilmadi.")

    birlashgan_mp3 = papka / "yigilish_birlashgan.mp3"
    _birlashtir(segmentlar, birlashgan_mp3)
    _logga_yoz(f"Birlashgan mp3 tayyor: {birlashgan_mp3.name} ({birlashgan_mp3.stat().st_size} bayt)")

    ogg_yol = papka / "yigilish.ogg"
    _ogg_ga_otkaz(birlashgan_mp3, ogg_yol)
    _logga_yoz(f"Telegram uchun ogg tayyor: {ogg_yol.name} ({ogg_yol.stat().st_size} bayt)")

    izoh = f"🗣️ Ertalabki yig'ilish — {bugun} (Jarvis OS, {len(segmentlar)} ta ovozli segment)"
    yuborildimi = _telegram_ovoz_yubor(ogg_yol, izoh)
    _logga_yoz("Telegram'ga yuborildi." if yuborildimi else "OGOHLANTIRISH: Telegram'ga yuborilmadi.")

    try:
        import jarvis_bildirishnoma
        jarvis_bildirishnoma.bildirishnoma_yoz(
            f"🗣️ Ertalabki yig'ilish o'tkazildi ({len(segmentlar)} ta xodim gapirdi), ovozli xabar Telegram'ga yuborildi.",
            manba="ertalabki_yigilish",
        )
    except Exception:
        pass

    return papka


def main():
    try:
        papka = yigilishni_otkaz()
        _logga_yoz(f"Yakunlandi. Fayllar: {papka}")
    except Exception as e:
        _logga_yoz(f"XATO: {e!r}")
        try:
            from jarvis_proaktiv import telegram_xabar_yubor
            telegram_xabar_yubor(f"⚠️ Ertalabki yig'ilishda xato: {e}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
