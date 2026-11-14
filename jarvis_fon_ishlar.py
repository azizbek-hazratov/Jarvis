"""
JARVIS FON-ISHLAR — barcha fon-agentlar/uzoq ishlarning umumiy, jonli ro'yxati
(2026-09-26, Azizbek so'radi: AzizEdu duplikat-o'quvchi voqeasidan keyin —
d9 sessiyasi va uning 2 subagenti hech qanday iz qoldirmasdan "o'lib qoldi",
keyingi sessiya buni bilmadi).

Maqsad: `jarvis_holati_signal.py`dagi "har manba o'ziga tegishli faylga
yozadi" naqshiga o'xshab, LEKIN bu safar BITTA umumiy ro'yxat (JSON fayl) —
har qanday Jarvis sessiyasi/subagent uzoq/production ishni boshlaganda o'zini
shu yerga yozib qo'yishi, tugaganda o'chirib tashlashi kerak. Har yangi
sessiya ishni boshlashdan oldin `royxatni_oqi()`/`ogohlantirish_matni()`ni
o'qib, "boshqa kim nima qilyapti" degan kontekstni olishi mumkin.

Yozish funksiyalari (jarvis_bildirishnoma.py/jarvis_holati_signal.py bilan
bir xil falsafa) HECH QACHON xato ko'tarmaydi — bu faqat QO'SHIMCHA kuzatuv
qatlami, chaqiruvchining asosiy vazifasini buzmasligi kerak.

MUHIM CHEKLOV: bu FAQAT convention (kelishilgan qoida) — hech qanday kod bu
yozuvni MAJBURIY qilmaydi. Amalda faqat shu funksiyalarni chaqirgan
kod (`jarvis_core.py`ning `Jarvis.ask()`i, va kelajakda shu naqshni
qabul qilgan boshqa sessiyalar/skriptlar) ro'yxatga tushadi.
"""

import json
import os
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FAYL = BASE_DIR / "jarvis_hud" / "fon-ishlar.json"


def _oqi() -> list:
    try:
        if FAYL.exists():
            data = json.loads(FAYL.read_text(encoding="utf-8"))
            return data.get("ishlar", [])
    except Exception:
        pass
    return []


def _yoz(ishlar: list) -> None:
    try:
        FAYL.parent.mkdir(parents=True, exist_ok=True)
        tmp = FAYL.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"ishlar": ishlar}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, FAYL)  # atomik almashtirish
    except Exception:
        pass


def royxatga_ol(agent: str, vazifa: str, papka: str, ish_id: str | None = None) -> str:
    """Yangi fon-ish/uzoq so'rov boshlanganda chaqiriladi.
    Keyinroq holatni_yangila()/royxatdan_ochir() uchun kerak bo'ladigan
    ID qaytaradi. Xato bo'lsa ham bo'sh string emas, tasodifiy ID qaytaradi
    (chaqiruvchi kodni murakkablashtirmaslik uchun — yozish jim
    muvaffaqiyatsiz bo'lishi mumkin, lekin chaqiruvchi doim ID bilan davom
    eta oladi).

    `ish_id` (2026-09-27, avtomatik fon-agent kuzatuvi uchun) -- berilsa
    o'zi ID generatsiya qilmaydi, CHAQIRUVCHI bergan ID'ni ishlatadi (masalan
    SDK'ning SubagentStart hook'idagi `agent_id` -- shu bilan keyinchalik
    SubagentStop hook'i AYNAN shu ID bilan `royxatdan_ochir()` chaqira oladi,
    alohida moslashtirish kerak bo'lmaydi)."""
    if ish_id is None:
        ish_id = uuid.uuid4().hex[:12]
    try:
        ishlar = _oqi()
        ishlar.append(
            {
                "id": ish_id,
                "agent": agent,
                "vazifa": (vazifa or "")[:300],
                "papka": papka,
                "boshlangan_vaqt": time.strftime("%Y-%m-%d %H:%M:%S"),
                "holat": "ishlayapti",
            }
        )
        _yoz(ishlar)
    except Exception:
        pass
    return ish_id


def holatni_yangila(ish_id: str, holat: str) -> None:
    try:
        ishlar = _oqi()
        for x in ishlar:
            if x.get("id") == ish_id:
                x["holat"] = holat
        _yoz(ishlar)
    except Exception:
        pass


def royxatdan_ochir(ish_id: str) -> None:
    """Ish tugagach (muvaffaqiyatli yoki xato bilan) ro'yxatdan butunlay
    olib tashlaydi — bu ro'yxat FAQAT "hozir nima ishlayapti" uchun, doimiy
    tarix uchun emas (tarix suhbatlar/*.md va diagnostika.log'da bor)."""
    try:
        ishlar = [x for x in _oqi() if x.get("id") != ish_id]
        _yoz(ishlar)
    except Exception:
        pass


def royxatni_oqi() -> list:
    """Har yangi sessiya ishni boshlashdan oldin shuni chaqirib, boshqa kim
    nima ustida ishlayotganini bilishi mumkin."""
    return _oqi()


# 2026-09-27 (Azizbek talabi bilan restart-himoyasi qo'shilganda topildi):
# jarayon O'ZI (ungraceful -- masalan tashqi kill/qulash) o'chib qolsa,
# `royxatdan_ochir()` (finally blok) ISHGA TUSHMAYDI -- yozuv "ishlayapti"
# holatda ABADIY qolib ketadi. Bunday "chirigan" yozuv haqiqiy fon-agent
# yo'q bo'lsa ham restartni CHEKSIZ bloklab qo'yishi mumkin edi (aynan shu
# fayl darajasida sinov paytida haqiqiy misoli topildi: 18:28'dan qolgan
# yozuv). Shu sabab: `jarvis_core.py`dagi MAX_ASK_TIMEOUT_S (2 soat) hech
# qachon oshmasligi kerak bo'lgan qattiq zaxira chegara -- shundan 1.5x
# ko'proq (3 soat) "ishlayapti" bo'lib turgan yozuv ANIQ chirigan deb
# hisoblanadi va "faol" deb hisoblanmaydi (lekin fayldan o'chirilmaydi --
# ko'rinib turishi, keyin qo'lda tekshirilishi mumkin).
ESKIRISH_CHEGARASI_SONIYA = 3 * 60 * 60  # 3 soat


def faol_ishlar() -> list:
    natija = []
    for x in _oqi():
        if x.get("holat") != "ishlayapti":
            continue
        # 2026-09-27 (sinov paytida topilgan xato): "telegram" -- Jarvisning
        # ASOSIY jarayoni har bir ask() paytida shu yerga o'zini yozadi
        # (jarvis_core.py:1163), demak deyarli DOIM "ishlayapti" bo'ladi --
        # bu esa restart-himoyasini har doim ishga tushirib qo'yardi (chunki
        # ayni restart buyrug'ini yuborayotgan SUHBATNING O'ZI ham shu yozuv
        # hisoblanadi). Restart-himoyasi faqat HAQIQIY fon-agentlarni
        # (subagent:*) sanashi kerak -- asosiy telegram yozuvi bloklamasin.
        if x.get("agent") == "telegram":
            continue
        try:
            boshlangan = time.mktime(time.strptime(x["boshlangan_vaqt"], "%Y-%m-%d %H:%M:%S"))
            if time.time() - boshlangan > ESKIRISH_CHEGARASI_SONIYA:
                continue  # chirigan yozuv -- faol deb hisoblanmaydi
        except Exception:
            pass  # sana parse bo'lmasa -- ehtiyot bo'lib baribir faol deb hisoblaymiz
        natija.append(x)
    return natija


def ogohlantirish_matni() -> str:
    """Ko'prik/jarayon reset yoki restart qilinishidan OLDIN ko'rsatiladigan
    qisqa ogohlantirish — 'N ta fon-agent ishlayapti, ular to'xtaydi'."""
    faollar = faol_ishlar()
    if not faollar:
        return "Hozir boshqa fon-agent/uzoq ish ro'yxatda yo'q."
    qatorlar = [
        f"- {x.get('agent', '?')}: {x.get('vazifa', '')[:80]} "
        f"({x.get('papka', '?')}, {x.get('boshlangan_vaqt', '?')}dan beri)"
        for x in faollar
    ]
    return (
        f"{len(faollar)} ta fon-agent/uzoq ish ro'yxatda FAOL ko'rinadi, "
        "ular to'xtaydi:\n" + "\n".join(qatorlar)
    )
