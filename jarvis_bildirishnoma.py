"""
JARVIS BILDIRISHNOMA — HUD roadmap #9 (MVP, 2026-09-21) uchun umumiy,
fayl-asosidagi bildirishnoma navbati.

MUAMMO: HUD bridge (`jarvis_hud/jarvis_hud_bridge.py`, 8090-port) va fon
xizmatlar (`jarvis_proaktiv.py`, `watchdog.py`, kuzatuv skriptlari va h.k.)
ATAYLAB mustaqil, bir-biridan izolyatsiyalangan jarayonlar (bu loyihaning
doimiy qoidasi — har biri alohida ishlab, bir-birini buzmasin). Shuning
uchun fon skriptlar hozir faqat Telegram'ga xabar yuboradi — HUD ochiq
turgan bo'lsa ham bundan bexabar qoladi.

YECHIM (eng past invaziv): jarayonlar orasida umumiy XOTIRA emas, umumiy
FAYL (`jarvis_hud/bildirishnomalar.jsonl`, JSON Lines) ishlatiladi. Har bir
fon skript Telegram xabar yuborgandan KEYIN shu faylga bitta qator
qo'shishi kifoya (`bildirishnoma_yoz()`) — bridge FAQAT o'qiydi (`GET
/bildirishnomalar`), HUD esa buni davriy so'rab, yangilarini push-style
toast sifatida ko'rsatadi.

MVP ko'lami (2026-09-21): hozircha faqat `jarvis_proaktiv.py`
(`telegram_xabar_yubor()`) shu yerga ulangan — boshqa manbalar (watchdog,
kuzatuv skriptlari) kelajakda xohlansa xuddi shu bitta funksiyani chaqirib
ulanishi mumkin (kod takrorlanmaydi, bitta manba).
"""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BILDIRISHNOMA_FAYL = BASE_DIR / "jarvis_hud" / "bildirishnomalar.jsonl"
BILDIRISHNOMA_MAX = 50  # fayl shundan ko'p qatorga yetsa, eskilari kesiladi


def bildirishnoma_yoz(matn: str, manba: str = "jarvis") -> None:
    """Bitta bildirishnoma qatorini qo'shadi. HECH QACHON xato ko'tarmaydi —
    bu faqat QO'SHIMCHA kanal, chaqiruvchi skriptning asosiy vazifasini
    (masalan Telegram xabar yuborishni) hech qanday holatda buzmasligi
    kerak."""
    try:
        BILDIRISHNOMA_FAYL.parent.mkdir(parents=True, exist_ok=True)
        yozuv = {
            "vaqt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "matn": matn,
            "manba": manba,
        }
        qatorlar = []
        if BILDIRISHNOMA_FAYL.exists():
            qatorlar = BILDIRISHNOMA_FAYL.read_text(encoding="utf-8").splitlines()
        qatorlar.append(json.dumps(yozuv, ensure_ascii=False))
        qatorlar = qatorlar[-BILDIRISHNOMA_MAX:]
        BILDIRISHNOMA_FAYL.write_text("\n".join(qatorlar) + "\n", encoding="utf-8")
    except Exception:
        pass


def bildirishnomalarni_oqi(maks: int = BILDIRISHNOMA_MAX) -> list[dict]:
    """Bridge shu funksiyani chaqiradi — faylni O'QIYDI, hech qachon
    yozmaydi (yagona yozuvchi yo'l `bildirishnoma_yoz()`)."""
    try:
        if not BILDIRISHNOMA_FAYL.exists():
            return []
        qatorlar = BILDIRISHNOMA_FAYL.read_text(encoding="utf-8").splitlines()[-maks:]
        natija = []
        for q in qatorlar:
            try:
                natija.append(json.loads(q))
            except Exception:
                continue
        return natija
    except Exception:
        return []
