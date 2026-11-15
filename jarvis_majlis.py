"""
JARVIS OS — "Majlis" (ko'p-xodimli video-qo'ng'iroq uslubidagi muhokama)
mexanizmi (5-bosqich davomi, 2026-09-27/28 kechasi).

Ikki xil majlis bor:
1) DEMO/SAQLANGAN majlis — bugun kechasi Orzu Akademy mavzusida BIR MARTA
   generatsiya qilinadi, matni VA ovozi diskka saqlanadi
   (`jarvis_hud/majlislar/oxirgi.json` + `oxirgi_audio/*.mp3`). "Oxirgi
   majlis" tugmasi buni FAQAT diskdan o'qiydi — AI ham, internet ham,
   edge-tts ham kerak emas (butunlay offline ishlaydi).
2) JONLI majlis (ixtiyoriy mavzu) — bridge orqali AI'dan (mavjud, sinalgan
   `_ask_jarvis_doimiy`/`_ask_jarvis`) BITTA so'rovda butun majlis matnini
   (1-tur, 2-tur, 3 ta g'oya) strukturaviy JSON sifatida so'raydi — real
   raqamlar promptga oldindan kontekst sifatida beriladi (AI fayl/DB
   qidirmasin, tezroq va ishonchliroq bo'lsin). AI ishlamasa/vaqt tugasa/
   JSON buzuq chiqsa — DETERMINISTIK zaxira (fallback) shu yerda, real
   joriy ko'rsatkichlar bilan, HECH QACHON butunlay muvaffaqiyatsiz
   bo'lmaydi.

Ovoz alohida (bridge orqali /jamoa/speak yoki oldindan saqlangan mp3),
bu modulda faqat MATN va vazifalar.md yozuvi bor.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import jarvis_jamoa_data as jjd

BASE = Path(__file__).parent
MAJLIS_DIR = BASE / "jarvis_hud" / "majlislar"
MAJLIS_DIR.mkdir(parents=True, exist_ok=True)
(MAJLIS_DIR / "oxirgi_audio").mkdir(parents=True, exist_ok=True)

# Kamola (soon) va Jarvis (u boshqaruvchi/yakunlovchi, ishtirokchi emas)
# majlis ISHTIROKCHILARIGA kirmaydi — Jarvis oxirida xulosa+g'oyalarni beradi.
MAJLIS_XODIM_TARTIBI = ["nozima", "sardor", "samandar", "bekzod", "malika"]


def _hozir():
    return datetime.utcnow() + timedelta(hours=5)


# ---------------------------------------------------------------------------
# 1) BUGUNGI DEMO MAJLIS — Orzu Akademy to'lovlari (template asosida, AI'siz,
#    100% ishonchli — faqat REAL joriy raqamlar jarvis_jamoa_data'dan olinadi).
# ---------------------------------------------------------------------------
def demo_orzu_majlis_matni() -> dict:
    bugun = jjd._bugun_str()
    nozima_m = jjd._nozima_malumot(bugun)
    natija = nozima_m.get("natija") or {}
    matn = natija.get("matn", "") or ""
    m = jjd._NOZIMA_RAQAM_RE.search(matn)
    if m:
        a_jami, a_tolagan, a_qolgan = int(m.group(1)), int(m.group(2)), int(m.group(3))
        g_jami, g_tolagan, g_qolgan = int(m.group(4)), int(m.group(5)), int(m.group(6))
    else:
        # Zaxira: hisobot hali yo'q bo'lsa ham demo to'xtab qolmasin.
        a_jami, a_tolagan, a_qolgan = 199, 28, 171
        g_jami, g_tolagan, g_qolgan = 154, 3, 151

    mavzu = (
        f"Orzu Akademy'da {a_jami} o'quvchidan {a_qolgan} tasining to'lovi "
        f"tizimda yozilmagan. Nima qilamiz?"
    )

    tur1 = [
        {
            "xodim": "nozima",
            "matn": (
                f"Jamoa, vaziyat shunday: Orzu Akademy'da {a_jami} faol o'quvchidan "
                f"faqat {a_tolagan} tasi joriy oy to'lovini amalga oshirgan, "
                f"{a_qolgan} tasi hali tizimda to'lov sifatida qayd etilmagan. "
                f"Bu deyarli har to'rtta o'quvchidan uchtasi degani — juda katta ko'rsatkich."
            ),
        },
        {
            "xodim": "sardor",
            "matn": (
                "Men ma'lumotlar bazasini va zaxira nusxalarni har kuni tekshiraman — "
                "texnik tomondan hech qanday nosozlik yo'q, baza toza ishlayapti. "
                "Demak bu haqiqiy to'lov muammosi, dastur xatosi emas."
            ),
        },
        {
            "xodim": "samandar",
            "matn": (
                "Men har kuni mijozlar bilan yozishaman va lidlarni yig'aman. "
                "Agar xohlasangiz, tizimda to'lovi yozilmagan ota-onalarga eslatma xabar "
                "yuborish jarayonini ham xuddi shu tarzda men orqali avtomatlashtirsak bo'ladi."
            ),
        },
        {
            "xodim": "bekzod",
            "matn": (
                "Tizim tomondan hech qanday uzilish yoki xatolik qayd etmadim — "
                "bot va server tinch ishlayapti. Demak bu operatsion masala, "
                "avtomatik eslatma funksiyasini qo'shsak muammoni erta ushlaymiz."
            ),
        },
        {
            "xodim": "malika",
            "matn": (
                "Mening sohamda — restoranda — bunday oylik to'lov nazorati yo'q, "
                "shuning uchun to'g'ridan-to'g'ri yordam bera olmayman. "
                "Lekin kelajakda JetCafe uchun ham shunga o'xshash hisobot tizimi "
                "kerak bo'lsa, naqshni ko'rib chiqamiz."
            ),
        },
    ]

    tur2 = [
        {
            "xodim": "samandar",
            "matn": (
                f"Nozima aytgan {a_qolgan} kishi juda katta raqam — men buni "
                "guruhlarga bo'lib, eng uzoq muddatdan beri tizimda to'lovi yozilmaganlardan "
                "boshlab birma-bir bog'lanishni taklif qilaman."
            ),
        },
        {
            "xodim": "nozima",
            "matn": (
                "Sardor to'g'ri aytdi — texnik muammo yo'q ekan, demak bu chindan "
                "ham eslatma va nazorat masalasi. Men hisobotni haftalik o'rniga "
                "tezroq berishga tayyorman."
            ),
        },
        {
            "xodim": "bekzod",
            "matn": (
                "Samandarning avtomatik eslatma g'oyasini texnik jihatdan "
                "qo'llab-quvvatlayman — buni xavfsiz, faqat o'qish rejimida, "
                "sizning tasdig'ingiz bilan qo'shsak bo'ladi."
            ),
        },
    ]

    gtoyalar = [
        {
            "matn": "To'lov holatini haftalik o'rniga har 3 kunda tekshirib, yangilangan hisobot berish",
            "xodim": "nozima",
            "muddat": "shu haftadan boshlab",
        },
        {
            "matn": "To'lamagan ota-onalarga avtomatik eslatma xabar oqimini tayyorlash (ishga tushishi sizning tasdig'ingiz bilan)",
            "xodim": "samandar",
            "muddat": "3 kun ichida",
        },
        {
            "matn": "Tizimga to'lov muddati o'tganda avtomatik ogohlantirish qo'shish",
            "xodim": "bekzod",
            "muddat": "1 hafta ichida",
        },
    ]

    xulosa = (
        f"Xulosa qilsam, Azizbek aka: Orzu Akademy'da {a_qolgan} o'quvchining to'lovi "
        "hali tizimda yo'q, lekin texnik tomondan hammasi sog'lom — demak bu nazorat "
        "va eslatma masalasi. Uchta aniq qadam tayyorladik: Nozima tezroq hisobot "
        "beradi, Samandar eslatma yuborish oqimini tayyorlaydi, Bekzod avtomatik "
        "ogohlantirish qo'shadi. Tasdig'ingizni kutamiz."
    )

    return {
        "mavzu": mavzu,
        "sana": bugun,
        "tur1": tur1,
        "tur2": tur2,
        "gtoyalar": gtoyalar,
        "xulosa": xulosa,
    }


def demo_fayl_yoli() -> Path:
    return MAJLIS_DIR / "oxirgi.json"


def demo_saqlangan_bormi() -> bool:
    return demo_fayl_yoli().exists()


def demo_saqlanganini_oqi() -> dict | None:
    try:
        return json.loads(demo_fayl_yoli().read_text(encoding="utf-8"))
    except Exception:
        return None


def demo_saqla(data: dict) -> None:
    demo_fayl_yoli().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 2) JONLI majlis — AI promptini tayyorlash + parse + zaxira (fallback).
# ---------------------------------------------------------------------------
def _real_kontekst_matni() -> str:
    """AI'ga beriladigan qisqa, real ko'rsatkichlar konteksti — AI o'zi
    fayl/DB qidirmasin (sekin va xato-ehtimolli), shu tayyor raqamlarga
    tayansin."""
    bugun = jjd._bugun_str()
    qatorlar = []
    for xid in MAJLIS_XODIM_TARTIBI:
        try:
            karta = jjd.xodim_kartasi(xid, bugun)
            qatorlar.append(f"- {karta['name']} ({karta['role']}): {karta.get('batafsil', karta.get('hozir', ''))}")
        except Exception:
            continue
    return "\n".join(qatorlar)


def live_ai_prompt(mavzu: str) -> str:
    kontekst = _real_kontekst_matni()
    xodim_royxati = ", ".join(jjd.XODIMLAR[x]["name"] for x in MAJLIS_XODIM_TARTIBI)
    return f"""Sen "Jarvis OS" AI xodimlar jamoasi majlisini yozayotgan yordamchisan. Vazifang — FAQAT quyida so'ralgan JSON'ni qaytarish, boshqa hech qanday matn yozma (izoh, markdown fence ham yo'q).

Majlis mavzusi: "{mavzu}"

Ishtirokchilar va ularning BUGUNGI REAL ko'rsatkichlari (shu raqamlarga tayan, o'zing raqam to'qima):
{kontekst}

Har ishtirokchi ID'lari (JSON'da xodim maydoni uchun): nozima, sardor, samandar, bekzod, malika.

Quyidagi aniq JSON strukturasini qaytar:
{{
  "tur1": [ {{"xodim": "<id>", "matn": "<2-3 gap, birinchi shaxsda, oddiy so'zlashuv o'zbek tilida, real raqamga tayangan>"}}, ... (5 ta, MAJLIS_XODIM_TARTIBI tartibida) ],
  "tur2": [ {{"xodim": "<id>", "matn": "<oldingi fikrlardan biriga qisqa javob/rozillik/tanqid, 1-2 gap>"}}, ... (2-3 ta) ],
  "gtoyalar": [ {{"matn": "<aniq, bajarsa bo'ladigan g'oya>", "xodim": "<mas'ul id>", "muddat": "<masalan '3 kun ichida'>"}}, ... (ANIQ 3 ta) ],
  "xulosa": "<Jarvisning yakuniy xulosasi, 2-3 gap, Azizbek akaga murojaat bilan>"
}}

Qoidalar: texnik jargon (SQL, API, kod, fayl nomi) ishlatma, biznes tilida yoz. Har bir "matn" 25 soniyalik ovozdan uzun bo'lmasin (taxminan 60 so'zdan kam).

MUHIM (2026-09-28 tuzatish): bu so'rovga javoban FAQAT yuqoridagi JSON'ni qaytar -- hech qanday tashqi xabar/bildirishnoma yubormang, hech qanday Bash/skript (jarvis_bildirishnoma, telegram_xabar_yubor, Telegram Bot API va h.k.) ishga tushirmang. Sening yagona vazifang shu javobning matnida JSON qaytarish."""


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_ai_majlis_javobi(raw: str) -> dict | None:
    if not raw:
        return None
    matn = _JSON_FENCE_RE.sub("", raw.strip()).strip()
    # Ba'zan AI JSON atrofida qo'shimcha gap yozishi mumkin — birinchi { dan
    # oxirgi } gacha bo'lgan qismni olamiz.
    start, end = matn.find("{"), matn.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(matn[start:end + 1])
    except Exception:
        return None

    ruxsat = set(MAJLIS_XODIM_TARTIBI)
    try:
        tur1 = [t for t in data.get("tur1", []) if t.get("xodim") in ruxsat and t.get("matn")]
        tur2 = [t for t in data.get("tur2", []) if t.get("xodim") in ruxsat and t.get("matn")]
        gtoyalar = [
            g for g in data.get("gtoyalar", [])
            if g.get("xodim") in ruxsat and g.get("matn") and g.get("muddat")
        ][:3]
        xulosa = str(data.get("xulosa") or "").strip()
        if not (tur1 and gtoyalar and xulosa):
            return None
        return {"tur1": tur1, "tur2": tur2, "gtoyalar": gtoyalar, "xulosa": xulosa}
    except Exception:
        return None


def live_fallback_majlis(mavzu: str) -> dict:
    """AI ishlamasa ham majlis HECH QACHON butunlay muvaffaqiyatsiz
    bo'lmasligi uchun — har xodimning REAL joriy holatidan (say/batafsil)
    qisqa jumla olib, umumiy mavzuga bog'lab beradi. AI'dek "aqlli"
    munozara emas, lekin har doim REAL ma'lumot bilan ishlaydi va hech
    qachon qotib qolmaydi."""
    bugun = jjd._bugun_str()
    tur1 = []
    for xid in MAJLIS_XODIM_TARTIBI:
        karta = jjd.xodim_kartasi(xid, bugun)
        tur1.append({
            "xodim": xid,
            "matn": f"\"{mavzu}\" mavzusida o'z tomonimdan aytadiganim: {karta.get('hozir', '')}",
        })
    tur2 = [{
        "xodim": "nozima",
        "matn": "Umuman olganda, jamoa bo'lib birga harakat qilsak bu masalani tezroq hal qilamiz.",
    }]
    gtoyalar = [
        {"matn": f"\"{mavzu}\" bo'yicha batafsil hisobot tayyorlash", "xodim": "nozima", "muddat": "3 kun ichida"},
        {"matn": "Holatni haftalik kuzatib borish va Azizbekka yangilanish berish", "xodim": "sardor", "muddat": "shu haftadan boshlab"},
        {"matn": "Mijozlar/ota-onalar bilan bog'lanish kerak bo'lsa, boshlash", "xodim": "samandar", "muddat": "1 hafta ichida"},
    ]
    xulosa = (
        f"Xulosa qilsam, Azizbek aka: \"{mavzu}\" mavzusini jamoa bo'lib ko'rib chiqdik. "
        "Uchta qadam belgiladik, tasdig'ingizni kutamiz. "
        "(Eslatma: bu majlis AI band bo'lgani uchun soddalashtirilgan tartibda, "
        "lekin xodimlarning bugungi REAL ko'rsatkichlari asosida tuzildi.)"
    )
    return {"mavzu": mavzu, "sana": bugun, "tur1": tur1, "tur2": tur2, "gtoyalar": gtoyalar, "xulosa": xulosa}


# ---------------------------------------------------------------------------
# 3) "✅ Topshiriq qilish" — g'oyani to'g'ridan-to'g'ri vazifalar.md'ga yozadi
#    (AI ishlatilmaydi, darhol va deterministik).
# ---------------------------------------------------------------------------
VAZIFALAR_FAYL = BASE / "xotira" / "vazifalar.md"
_MAJLIS_BOLIM_SARLAVHA = "## Majlisdan chiqqan topshiriqlar"


def vazifa_yoz(matn: str, xodim_id: str, muddat: str, mavzu: str = "") -> str:
    ism = jjd.XODIMLAR.get(xodim_id, {}).get("name", xodim_id)
    sana = _hozir().strftime("%Y-%m-%d")
    qator = f"- [ ] (Majlis {sana}) {matn} — mas'ul: {ism}, muddat: {muddat}."
    if mavzu:
        qator += f" _(mavzu: {mavzu[:80]})_"

    try:
        matn_fayl = VAZIFALAR_FAYL.read_text(encoding="utf-8")
    except Exception:
        matn_fayl = "# Vazifalar\n"

    if _MAJLIS_BOLIM_SARLAVHA in matn_fayl:
        idx = matn_fayl.index(_MAJLIS_BOLIM_SARLAVHA)
        sarlavha_oxiri = matn_fayl.index("\n", idx) + 1
        yangi = matn_fayl[:sarlavha_oxiri] + qator + "\n" + matn_fayl[sarlavha_oxiri:]
    else:
        yangi = matn_fayl.rstrip("\n") + f"\n\n{_MAJLIS_BOLIM_SARLAVHA}\n{qator}\n"

    VAZIFALAR_FAYL.write_text(yangi, encoding="utf-8")
    return qator


if __name__ == "__main__":
    import pprint
    d = demo_orzu_majlis_matni()
    pprint.pprint(d)
